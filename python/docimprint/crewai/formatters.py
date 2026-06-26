"""Shared helpers for CrewAI tool output formatting."""

from __future__ import annotations

from typing import Any

from docimprint.errors import DocImprintError


def format_error(exc: Exception) -> str:
    if isinstance(exc, DocImprintError):
        parts = [f"ERROR: {exc.message}"]
        if exc.code:
            parts.append(f"({exc.code})")
        if exc.status == 402:
            parts.append("Check quota with get_quota or top up at https://docimprint.com/billing.")
        return " ".join(parts)
    return f"ERROR: {exc}"


def _claim_symbol(status: str) -> str:
    normalized = status.lower()
    if normalized in ("true", "supported", "verified"):
        return "✓ TRUE"
    if normalized in ("false", "refuted", "unsupported", "contradicted"):
        return "✗ FALSE"
    return "? UNCERTAIN"


def format_extract_response(data: dict[str, Any]) -> str:
    bundle_id = data.get("bundle_id", "unknown")
    provenance = data.get("provenance") or {}
    manifest_hash = provenance.get("manifest_sha256", "unknown")
    sig = provenance.get("signature") or {}
    if sig.get("signature"):
        sig_note = (
            " (EIP-191 signed, verified)"
            if data.get("valid") is True
            else " (signature present — run verify_bundle to confirm)"
        )
    else:
        sig_note = ""

    metadata = data.get("metadata") or {}
    source = metadata.get("url") or metadata.get("source") or data.get("source") or "unknown"
    captured = metadata.get("captured_at") or metadata.get("created_at") or "unknown"

    result = data.get("result") or {}
    summary = result.get("summary") or result.get("text") or ""

    lines = [
        f"EVIDENCE BUNDLE {bundle_id} | sha256:{manifest_hash}{sig_note}",
        f"Source: {source} | Captured: {captured}",
        "",
    ]
    if summary:
        lines.extend(["SUMMARY:", summary, ""])

    citations = result.get("citations") or data.get("citations") or []
    if citations:
        lines.append("CITATIONS:")
        for i, cite in enumerate(citations, 1):
            if isinstance(cite, dict):
                quote = cite.get("quote") or cite.get("text") or str(cite)
                loc = cite.get("section") or cite.get("page") or ""
                prefix = f"[{i}] {loc}: " if loc else f"[{i}] "
                lines.append(f'{prefix}"{quote}"')
            else:
                lines.append(f"[{i}] {cite}")

    lines.append(f"\n→ Bundle ID: {bundle_id} (pass to VerifyBundleTool, NotarizeTool, or CheckClaimsTool)")
    return "\n".join(lines)


def format_summarize_response(data: dict[str, Any]) -> str:
    result = data.get("result") or data
    summary = result.get("summary") or result.get("text") or ""
    key_points = result.get("key_points") or []
    bundle_id = data.get("bundle_id")

    lines = ["SUMMARY:"]
    if bundle_id:
        lines[0] = f"EVIDENCE BUNDLE {bundle_id}\n\nSUMMARY:"
    lines.append(summary)
    if key_points:
        lines.extend(["", "KEY POINTS:"])
        for point in key_points:
            lines.append(f"- {point}")
    if bundle_id:
        lines.append(f"\n→ Bundle ID: {bundle_id}")
    return "\n".join(lines)


def format_qa_response(data: dict[str, Any]) -> str:
    result = data.get("result") or data
    answer = result.get("answer") or result.get("text") or ""
    citations = result.get("citations") or data.get("citations") or []
    bundle_id = data.get("bundle_id")

    lines = ["ANSWER:"]
    if bundle_id:
        lines[0] = f"EVIDENCE BUNDLE {bundle_id}\n\nANSWER:"
    lines.append(answer)
    if citations:
        lines.extend(["", "CITATIONS:"])
        for i, cite in enumerate(citations, 1):
            if isinstance(cite, dict):
                quote = cite.get("quote") or cite.get("text") or str(cite)
                lines.append(f'[{i}] "{quote}"')
            else:
                lines.append(f"[{i}] {cite}")
    if bundle_id:
        lines.append(f"\n→ Bundle ID: {bundle_id}")
    return "\n".join(lines)


def format_check_claims_response(data: dict[str, Any]) -> str:
    bundle_id = data.get("bundle_id", "unknown")
    result = data.get("result") or data
    claims = result.get("claims") or data.get("claims") or []

    lines = [f"CLAIM CHECK RESULTS for {bundle_id}", ""]
    for item in claims:
        if not isinstance(item, dict):
            continue
        claim = item.get("claim", "")
        status = item.get("status", "uncertain")
        lines.append(f'{_claim_symbol(status)}     "{claim}"')
        evidence = item.get("evidence") or {}
        if isinstance(evidence, dict):
            quote = evidence.get("quote") or evidence.get("text") or ""
            if quote:
                lines.append(f'  Evidence: "{quote}"')
        lines.append("")

    if bundle_id and bundle_id != "unknown":
        lines.append(f"→ Bundle ID: {bundle_id}")
    return "\n".join(lines).strip()


def format_translate_response(data: dict[str, Any]) -> str:
    result = data.get("result") or data
    translated = result.get("translated_text") or result.get("text") or ""
    bundle_id = data.get("bundle_id")
    citations = result.get("citations") or []

    lines = ["TRANSLATION:"]
    if bundle_id:
        lines[0] = f"EVIDENCE BUNDLE {bundle_id}\n\nTRANSLATION:"
    lines.append(translated)
    if citations:
        lines.extend(["", "SOURCE CITATIONS:"])
        for i, cite in enumerate(citations, 1):
            quote = cite.get("quote", str(cite)) if isinstance(cite, dict) else str(cite)
            lines.append(f'[{i}] "{quote}"')
    if bundle_id:
        lines.append(f"\n→ Bundle ID: {bundle_id}")
    return "\n".join(lines)


def format_verify_response(data: dict[str, Any], bundle_id: str) -> str:
    valid = data.get("valid", False)
    manifest = data.get("manifest_sha256", "unknown")
    checks = data.get("checks") or {}
    status = "VALID" if valid else "INVALID"
    lines = [
        f"VERIFY {bundle_id}: {status}",
        f"manifest_sha256: {manifest}",
    ]
    if checks:
        for key, value in checks.items():
            lines.append(f"  {key}: {value}")
    return "\n".join(lines)


def format_notarize_response(data: dict[str, Any], bundle_id: str) -> str:
    attestation = data.get("attestation") or data
    tx_hash = attestation.get("tx_hash", "unknown")
    network = attestation.get("network", "unknown")
    eas_uid = attestation.get("eas_uid") or attestation.get("uid") or "n/a"
    return (
        f"NOTARIZED {bundle_id}\n"
        f"tx_hash: {tx_hash}\n"
        f"network: {network}\n"
        f"EAS UID: {eas_uid}"
    )


def format_search_response(data: dict[str, Any], collection_id: str) -> str:
    results = data.get("results") or []
    lines = [f"SEARCH RESULTS (collection {collection_id})", ""]
    for i, item in enumerate(results, 1):
        if not isinstance(item, dict):
            continue
        text = item.get("text") or item.get("content") or ""
        bundle_id = item.get("bundle_id", "unknown")
        score = item.get("score")
        score_str = f" (score: {score:.3f})" if isinstance(score, (int, float)) else ""
        lines.append(f"[{i}]{score_str} bundle {bundle_id}")
        lines.append(text)
        lines.append("")
    if not results:
        lines.append("No results found.")
    return "\n".join(lines).strip()


def format_ask_collection_response(data: dict[str, Any], collection_id: str) -> str:
    answer = data.get("answer") or (data.get("result") or {}).get("answer") or ""
    citations = data.get("citations") or (data.get("result") or {}).get("citations") or []
    lines = [f"COLLECTION ANSWER (collection {collection_id})", "", answer]
    if citations:
        lines.extend(["", "CITATIONS:"])
        for i, cite in enumerate(citations, 1):
            if isinstance(cite, dict):
                bundle_id = cite.get("bundle_id", "")
                quote = cite.get("quote") or cite.get("text") or ""
                prefix = f"[{i}] bundle {bundle_id}: " if bundle_id else f"[{i}] "
                lines.append(f'{prefix}"{quote}"')
            else:
                lines.append(f"[{i}] {cite}")
    return "\n".join(lines)


def format_add_to_collection_response(collection_id: str, bundle_id: str) -> str:
    return f"Added bundle {bundle_id} to collection {collection_id}."
