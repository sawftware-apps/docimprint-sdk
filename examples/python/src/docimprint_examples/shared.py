"""Shared helpers for DocImprint example demos."""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from docimprint import DocImprintClient, DocImprintError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

REPO_ROOT = Path(__file__).resolve().parents[2]  # examples/python
EXAMPLES_ROOT = Path(__file__).resolve().parents[3]  # examples/
FIXTURES_DIR = EXAMPLES_ROOT / "fixtures"
OUT_DIR = REPO_ROOT / "out"

DEFAULT_BASE_URL = "https://api.docimprint.com"
VERIFY_TOOL_URL = "https://docimprint.com/tools/verify-bundle"

console = Console(stderr=False)
err_console = Console(stderr=True)


@dataclass
class DemoSession:
    """Shared HTTP session for SDK client + multipart uploads."""

    api_key: str
    base_url: str
    http: httpx.Client
    client: DocImprintClient

    def close(self) -> None:
        self.client.close()
        self.http.close()

    def __enter__(self) -> DemoSession:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def load_config() -> tuple[str, str]:
    """Load API key + base URL from env (.env supported). Raises SystemExit on missing key."""
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv()
    api_key = os.environ.get("DOCIMPRINT_API_KEY", "").strip()
    if not api_key:
        err_console.print(
            "[bold red]error:[/] DOCIMPRINT_API_KEY is required "
            "(copy .env.example → .env and set your key)"
        )
        raise SystemExit(1)
    base_url = os.environ.get("DOCIMPRINT_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
    return api_key, base_url


def open_session(api_key: str, base_url: str, *, timeout: float = 120.0) -> DemoSession:
    http = httpx.Client(
        base_url=base_url.rstrip("/"),
        timeout=timeout,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    client = DocImprintClient(api_key, base_url=base_url, timeout=timeout, client=http)
    return DemoSession(
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        http=http,
        client=client,
    )


def cited_text(value: Any) -> tuple[str, list[dict[str, Any]]]:
    """Some endpoints return a plain string, others a cited field ({value, confidence, citations})."""
    if isinstance(value, dict) and "value" in value:
        citations = value.get("citations")
        return str(value.get("value") or ""), citations if isinstance(citations, list) else []
    return str(value or ""), []


def manifest_sha256(payload: dict[str, Any]) -> str | None:
    if payload.get("manifest_sha256"):
        return str(payload["manifest_sha256"])
    provenance = payload.get("provenance") or {}
    if isinstance(provenance, dict) and provenance.get("manifest_sha256"):
        return str(provenance["manifest_sha256"])
    return None


def receipt_id(receipt: dict[str, Any] | None) -> str | None:
    if not receipt:
        return None
    value = receipt.get("receipt_id") or receipt.get("id")
    return str(value) if value else None


def pick_receipt_for_verify(
    listed: list[dict[str, Any]],
    *,
    preferred_id: str | None,
) -> dict[str, Any] | None:
    if preferred_id:
        for row in listed:
            if row.get("id") == preferred_id or row.get("receipt_id") == preferred_id:
                return row
    for row in listed:
        if row.get("action") == "verify_bundle":
            return row
    return listed[-1] if listed else None


def bundle_id_of(payload: dict[str, Any]) -> str | None:
    value = payload.get("bundle_id") or payload.get("id")
    return str(value) if value else None


def verify_tool_url(bundle_id: str) -> str:
    return f"{VERIFY_TOOL_URL}?bundle_id={bundle_id}"


def api_verify_url(base_url: str, bundle_id: str) -> str:
    return f"{base_url.rstrip('/')}/v1/extract/{bundle_id}/verify"


def claim_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize claim-check response shapes into a list of claim dicts."""
    result = payload.get("result") or {}
    if not isinstance(result, dict):
        result = {}
    rows = (
        result.get("claim_results")
        or result.get("claims")
        or payload.get("claim_results")
        or payload.get("claims")
        or []
    )
    return [r for r in rows if isinstance(r, dict)]


def assert_claim_gotcha(rows: list[dict[str, Any]]) -> None:
    """Require at least one supported and one contradicted/not_found verdict."""
    statuses = {str(r.get("status") or r.get("verdict") or "").lower() for r in rows}
    has_supported = "supported" in statuses
    has_negative = bool(statuses & {"contradicted", "not_found", "unsupported"})
    if not has_supported or not has_negative:
        raise DocImprintError(
            "expected a supported claim and a contradicted/not_found claim "
            f"(got statuses={sorted(statuses)})",
            code="CLAIM_GOTCHA_MISSING",
            details={"statuses": sorted(statuses), "rows": rows},
        )


def write_evidence_pack(bundle_id: str, payload: dict[str, Any]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"evidence_pack_{bundle_id}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def print_error(exc: DocImprintError) -> None:
    err_console.print(
        Panel.fit(
            Text.from_markup(
                f"[bold red]{exc.message}[/]\n"
                f"status={exc.status}  code={exc.code}  request_id={exc.request_id}"
            ),
            title="DocImprintError",
            border_style="red",
        )
    )


def print_warnings(warnings: list[str]) -> None:
    for warning in warnings:
        err_console.print(f"[yellow]warning:[/] {warning}")


def print_claim_table(rows: list[dict[str, Any]]) -> None:
    table = Table(title="Claim check", show_lines=True)
    table.add_column("Verdict", style="bold", width=14)
    table.add_column("Claim")
    table.add_column("Evidence quote")

    for item in rows:
        status = str(item.get("status") or item.get("verdict") or "unknown").lower()
        claim = str(item.get("claim") or "")
        evidence = item.get("evidence") or {}
        quote = ""
        if isinstance(evidence, dict):
            quote = str(evidence.get("quote") or evidence.get("text") or "")
        elif isinstance(evidence, str):
            quote = evidence

        style = {
            "supported": "green",
            "contradicted": "red",
            "not_found": "yellow",
            "unsupported": "yellow",
        }.get(status, "white")

        table.add_row(
            Text(status, style=style),
            claim,
            quote[:180] + ("…" if len(quote) > 180 else ""),
        )

    console.print(table)


def print_share_panel(
    *,
    bundle_id: str,
    manifest: str | None,
    base_url: str,
    receipt_verify: dict[str, Any] | None,
    pack_path: Path | None,
) -> None:
    lines = [
        f"[bold]bundle_id[/]          {bundle_id}",
        f"[bold]manifest_sha256[/]    {manifest or '—'}",
        f"[bold]verify (UI)[/]        {verify_tool_url(bundle_id)}",
        f"[bold]verify (API)[/]       {api_verify_url(base_url, bundle_id)}",
    ]
    if receipt_verify:
        lines.append(
            f"[bold]receipt_id[/]         {receipt_verify.get('receipt_id') or '—'}"
        )
        lines.append(
            f"[bold]receipt valid[/]      {receipt_verify.get('valid')}"
        )
    if pack_path:
        lines.append(f"[bold]evidence pack[/]     {pack_path}")

    console.print(
        Panel(
            "\n".join(lines),
            title="Shareable artifacts",
            border_style="cyan",
        )
    )


def extract_uploaded_file(
    http: httpx.Client,
    *,
    file_bytes: bytes,
    filename: str,
    mode: str = "extract",
    claims: list[str] | None = None,
    lean: bool = False,
    wait: bool = True,
    retries: int = 2,
    wait_for_job: Any | None = None,
) -> dict[str, Any]:
    """Upload a local fixture via multipart with an explicit filename.

    Claims must be a JSON string in multipart form fields.
    Retries transient ``PROCESSING_ERROR`` responses (model format flakiness).
    """
    params: dict[str, Any] = {"sync": "true", "store": "false" if lean else "true"}
    form: dict[str, Any] = {"mode": mode}
    if claims is not None:
        form["claims"] = json.dumps(claims)

    content_type = "text/plain"
    if filename.lower().endswith(".pdf"):
        content_type = "application/pdf"
    elif filename.lower().endswith((".html", ".htm")):
        content_type = "text/html"

    attempts = max(1, retries + 1)
    last_error: DocImprintError | None = None

    for attempt in range(attempts):
        try:
            response = http.post(
                "/v1/extract",
                params=params,
                data=form,
                files={"file": (filename, file_bytes, content_type)},
            )
        except httpx.HTTPError as exc:
            raise DocImprintError(str(exc)) from exc

        request_id = response.headers.get("x-request-id")
        if response.status_code not in (200, 201, 202):
            payload: dict[str, Any] = {}
            try:
                payload = response.json()
            except ValueError:
                payload = {"message": response.text or response.reason_phrase}
            message = payload.get("message") or payload.get("error") or "Request failed"
            last_error = DocImprintError(
                str(message),
                status=response.status_code,
                code=payload.get("code"),
                request_id=request_id or payload.get("request_id"),
                details=payload,
            )
            if (
                attempt + 1 < attempts
                and response.status_code >= 500
                and (payload.get("code") == "PROCESSING_ERROR" or "AI response" in str(message))
            ):
                time.sleep(1.5 * (attempt + 1))
                continue
            raise last_error

        data = response.json() if response.content else {}
        if (
            wait
            and wait_for_job is not None
            and data.get("job_id")
            and data.get("status") not in (None, "complete", "failed", "completed")
        ):
            return wait_for_job(data["job_id"])
        return data

    assert last_error is not None
    raise last_error


def require_valid_receipt(
    client: DocImprintClient,
    *,
    bundle_id: str,
    preferred_id: str | None,
    allow_missing: bool,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[str]]:
    """List receipts, verify one, or fail unless allow_missing."""
    warnings: list[str] = []
    listed = client.list_receipts(bundle_id)
    receipt_rows = listed.get("receipts") or []
    if not isinstance(receipt_rows, list):
        receipt_rows = []

    chosen = pick_receipt_for_verify(receipt_rows, preferred_id=preferred_id)
    chosen_id = receipt_id(chosen) if chosen else preferred_id

    if not chosen_id:
        if allow_missing:
            warnings.append(
                "no action receipts available — document verify succeeded without a signed receipt"
            )
            return None, receipt_rows, warnings
        raise DocImprintError(
            "expected a signed action receipt after verify; none were returned. "
            "Pass --allow-missing-receipt only for environments without signing.",
            code="RECEIPT_MISSING",
            details={"bundle_id": bundle_id, "inline_receipt_id": preferred_id},
        )

    check = client.verify_receipt(chosen_id)
    receipt_verify = {
        "receipt_id": check.get("receipt_id") or chosen_id,
        "valid": bool(check.get("valid")),
        "signature_valid": check.get("signature_valid"),
        "manifest_matches_current": check.get("manifest_matches_current"),
        "action": check.get("action"),
        "agent_id": check.get("agent_id"),
        "manifest_sha256": check.get("manifest_sha256"),
        "tampered": check.get("tampered") or [],
    }
    if not check.get("valid"):
        raise DocImprintError(
            "action receipt verification failed",
            code="RECEIPT_INVALID",
            details=check,
        )
    return receipt_verify, receipt_rows, warnings


def json_dump(data: dict[str, Any], *, stream: Any = None) -> None:
    print(json.dumps(data, indent=2), file=stream or sys.stdout)
