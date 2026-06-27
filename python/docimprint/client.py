"""Synchronous HTTP client for the DocImprint API."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlparse

import httpx

from docimprint.errors import DocImprintError
from docimprint.ids import validate_bundle_id, validate_collection_id, validate_job_id


def _normalize_base_url(base_url: str, *, allow_insecure_http: bool) -> str:
    normalized = base_url.rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme == "https":
        return normalized
    if allow_insecure_http:
        return normalized
    if parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1"):
        return normalized
    raise DocImprintError(
        f"base_url must use HTTPS (got {parsed.scheme!r}); "
        "pass allow_insecure_http=True for local development only",
        code="INSECURE_BASE_URL",
    )


class DocImprintClient:
    """Python REST client for DocImprint."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.docimprint.com",
        timeout: float = 120.0,
        allow_insecure_http: bool = False,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self.base_url = _normalize_base_url(base_url, allow_insecure_http=allow_insecure_http)
        self._owns_client = client is None
        self._http = client or httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def __repr__(self) -> str:
        return f"DocImprintClient(base_url={self.base_url!r}, api_key='***')"

    def close(self) -> None:
        if self._owns_client:
            self._http.close()

    def __enter__(self) -> DocImprintClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        expected: tuple[int, ...] = (200, 201, 202, 204),
    ) -> dict[str, Any] | None:
        try:
            response = self._http.request(
                method,
                path,
                params=params,
                json=json,
                data=data,
                files=files,
            )
        except httpx.HTTPError as exc:
            raise DocImprintError(str(exc)) from exc

        request_id = response.headers.get("x-request-id")

        if response.status_code not in expected:
            payload: dict[str, Any] = {}
            try:
                payload = response.json()
            except ValueError:
                payload = {"message": response.text or response.reason_phrase}
            message = payload.get("message") or payload.get("error") or "Request failed"
            raise DocImprintError(
                str(message),
                status=response.status_code,
                code=payload.get("code"),
                request_id=request_id or payload.get("request_id"),
                details=payload,
            )

        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def _maybe_wait(self, data: dict[str, Any] | None, *, wait: bool, timeout: float) -> dict[str, Any]:
        if not data:
            return {}
        if wait and data.get("job_id") and data.get("status") not in (None, "complete", "failed"):
            return self.wait_for_job(data["job_id"], timeout=timeout)
        if wait and data.get("job_id") and data.get("status") is None:
            return self.wait_for_job(data["job_id"], timeout=timeout)
        return data

    def wait_for_job(
        self,
        job_id: str,
        *,
        timeout: float = 60.0,
        poll_interval: float = 2.0,
        max_interval: float = 10.0,
    ) -> dict[str, Any]:
        """Poll a job until complete, failed, or timeout."""
        job_id = validate_job_id(job_id)
        deadline = time.monotonic() + timeout
        interval = poll_interval
        while time.monotonic() < deadline:
            job = self.get_job(job_id)
            status = job.get("status")
            if status in ("complete", "completed", "failed", "error"):
                if status in ("failed", "error"):
                    raise DocImprintError(
                        job.get("error") or "Job failed",
                        code=job.get("code"),
                    )
                return job.get("result") or job
            time.sleep(interval)
            interval = min(interval * 1.5, max_interval)
        raise DocImprintError(f"Job {job_id} timed out after {timeout}s", code="JOB_TIMEOUT")

    # --- Core evidence ---

    def extract(
        self,
        *,
        url: str | None = None,
        file: bytes | None = None,
        mode: str = "extract",
        wait: bool = True,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"sync": "true", "store": "true"}
        if kwargs.pop("async_", False):
            params["async"] = "true"
            params.pop("sync", None)
        if kwargs.pop("lean", False):
            params["store"] = "false"

        body: dict[str, Any] = {"mode": mode, **kwargs}
        if url:
            body["source"] = url
        files = None
        form_data = None
        if file is not None:
            files = {"file": ("upload", file)}
            form_data = body
            body = None
        data = self._request(
            "POST",
            "/v1/extract",
            params=params,
            json=body,
            data=form_data,
            files=files,
        )
        return self._maybe_wait(data, wait=wait, timeout=timeout)

    def verify(self, bundle_id: str, *, quick: bool = False) -> dict[str, Any]:
        bundle_id = validate_bundle_id(bundle_id)
        params = {"quick": "true"} if quick else None
        result = self._request("GET", f"/v1/extract/{bundle_id}/verify", params=params)
        return result or {}

    def notarize(self, bundle_id: str) -> dict[str, Any]:
        bundle_id = validate_bundle_id(bundle_id)
        result = self._request("POST", f"/v1/extract/{bundle_id}/notarize")
        return result or {}

    def delete_bundle(self, bundle_id: str, *, acknowledge_notarized: bool = False) -> None:
        bundle_id = validate_bundle_id(bundle_id)
        params = {"acknowledge_notarized": "true"} if acknowledge_notarized else None
        self._request("DELETE", f"/v1/extract/{bundle_id}", params=params, expected=(200, 204))

    def get_bundle(self, bundle_id: str) -> dict[str, Any]:
        bundle_id = validate_bundle_id(bundle_id)
        result = self._request("GET", f"/v1/extract/{bundle_id}")
        return result or {}

    # --- Focused endpoints ---

    def summarize(self, url: str, *, wait: bool = True, timeout: float = 60.0, **kwargs: Any) -> dict[str, Any]:
        data = self._request("POST", "/v1/summarize", json={"source": url, **kwargs})
        return self._maybe_wait(data, wait=wait, timeout=timeout)

    def qa(self, url: str, question: str, *, wait: bool = True, timeout: float = 60.0, **kwargs: Any) -> dict[str, Any]:
        data = self._request("POST", "/v1/qa", json={"source": url, "question": question, **kwargs})
        return self._maybe_wait(data, wait=wait, timeout=timeout)

    def translate(
        self,
        url: str,
        target_language: str,
        *,
        wait: bool = True,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        data = self._request(
            "POST",
            "/v1/translate",
            json={"source": url, "target_lang": target_language, **kwargs},
        )
        return self._maybe_wait(data, wait=wait, timeout=timeout)

    def check_claims(
        self,
        url: str,
        claims: list[str],
        *,
        wait: bool = True,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        data = self._request(
            "POST",
            "/v1/check-claims",
            json={"source": url, "claims": claims, **kwargs},
        )
        return self._maybe_wait(data, wait=wait, timeout=timeout)

    def describe(self, url: str, *, wait: bool = True, timeout: float = 60.0, **kwargs: Any) -> dict[str, Any]:
        data = self._request("POST", "/v1/describe", json={"source": url, **kwargs})
        return self._maybe_wait(data, wait=wait, timeout=timeout)

    # --- Collections ---

    def create_collection(self, name: str) -> dict[str, Any]:
        result = self._request("POST", "/v1/collections", json={"name": name}, expected=(200, 201))
        return result or {}

    def list_collections(self) -> list[dict[str, Any]]:
        result = self._request("GET", "/v1/collections")
        if not result:
            return []
        if isinstance(result, list):
            return result
        return result.get("collections", result.get("items", []))

    def add_to_collection(self, collection_id: str, bundle_id: str) -> dict[str, Any]:
        collection_id = validate_collection_id(collection_id)
        bundle_id = validate_bundle_id(bundle_id)
        result = self._request(
            "POST",
            f"/v1/collections/{collection_id}/documents",
            json={"bundle_id": bundle_id},
        )
        return result or {}

    def search_collection(self, collection_id: str, query: str, *, limit: int = 10) -> dict[str, Any]:
        collection_id = validate_collection_id(collection_id)
        result = self._request(
            "GET",
            f"/v1/collections/{collection_id}/search",
            params={"q": query, "limit": limit},
        )
        return result or {}

    def ask_collection(self, collection_id: str, question: str) -> dict[str, Any]:
        collection_id = validate_collection_id(collection_id)
        result = self._request(
            "POST",
            f"/v1/collections/{collection_id}/ask",
            json={"question": question},
        )
        return result or {}

    # --- Jobs & quota ---

    def get_job(self, job_id: str) -> dict[str, Any]:
        job_id = validate_job_id(job_id)
        result = self._request("GET", f"/v1/jobs/{job_id}")
        return result or {}

    def get_quota(self) -> dict[str, Any]:
        result = self._request("GET", "/v1/quota")
        return result or {}

    # --- Provenance ---

    def log_provenance(
        self,
        bundle_id: str,
        agent_id: str,
        action: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        bundle_id = validate_bundle_id(bundle_id)
        body = {"agent_id": agent_id, "action": action, **kwargs}
        result = self._request("POST", f"/v1/extract/{bundle_id}/provenance", json=body)
        return result or {}

    def handoff(
        self,
        bundle_id: str,
        from_agent: str,
        to_agent: str,
        note: str = "",
    ) -> dict[str, Any]:
        bundle_id = validate_bundle_id(bundle_id)
        result = self._request(
            "POST",
            f"/v1/extract/{bundle_id}/handoff",
            json={"from_agent": from_agent, "to_agent": to_agent, "note": note},
        )
        return result or {}
