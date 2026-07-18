"""Thin REST helpers for DocImprint action receipts.

The published ``docimprint`` Python client does not yet expose these endpoints;
the TypeScript SDK and REST API do.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx
from docimprint import DocImprintError
from docimprint.ids import validate_bundle_id


def _normalize_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in ("https", "http"):
        raise DocImprintError(
            f"base_url must use http or https (got {parsed.scheme!r})",
            code="INVALID_BASE_URL",
        )
    return normalized


def _raise_for_status(response: httpx.Response) -> dict[str, Any]:
    request_id = response.headers.get("x-request-id")
    if response.status_code in (200, 201):
        return response.json() if response.content else {}

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


class ReceiptClient:
    """List and independently verify signed action receipts."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.docimprint.com",
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = _normalize_base_url(base_url)
        self._owns_client = client is None
        self._http = client or httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def close(self) -> None:
        if self._owns_client:
            self._http.close()

    def __enter__(self) -> ReceiptClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def list_receipts(
        self,
        bundle_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """GET /v1/extract/{bundle_id}/receipts"""
        bundle_id = validate_bundle_id(bundle_id)
        response = self._http.get(
            f"/v1/extract/{bundle_id}/receipts",
            params={"limit": limit, "offset": offset},
        )
        return _raise_for_status(response)

    def verify_receipt(self, receipt_id: str) -> dict[str, Any]:
        """GET /v1/extract/receipts/{receipt_id}/verify

        Receipt IDs are unguessable capability tokens — this endpoint is not
        owner-gated so a third-party auditor can verify independently.
        """
        if not receipt_id or not isinstance(receipt_id, str):
            raise DocImprintError("receipt_id is required", code="INVALID_RECEIPT_ID")
        response = self._http.get(f"/v1/extract/receipts/{receipt_id}/verify")
        return _raise_for_status(response)
