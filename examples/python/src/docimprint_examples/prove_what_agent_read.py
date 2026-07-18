"""Hero demo: prove what an AI agent read — claim-check + evidence + receipt.

Clone-and-run against a local MSA fixture (no fragile third-party PDF URL).

One stored claim-check upload produces both claim verdicts and an evidence bundle,
then we verify integrity and audit the action receipt.

Usage:
  python -m docimprint_examples.prove_what_agent_read
  python -m docimprint_examples.prove_what_agent_read --notarize
  python -m docimprint_examples.prove_what_agent_read --allow-missing-receipt
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from docimprint import DocImprintError
from rich.panel import Panel

from docimprint_examples.shared import (
    FIXTURES_DIR,
    api_verify_url,
    assert_claim_gotcha,
    bundle_id_of,
    claim_rows,
    console,
    extract_uploaded_file,
    load_config,
    manifest_sha256,
    open_session,
    print_claim_table,
    print_error,
    print_share_panel,
    print_warnings,
    receipt_id,
    require_valid_receipt,
    verify_tool_url,
    write_evidence_pack,
)


def _load_fixture() -> tuple[bytes, list[str], Path]:
    msa_path = FIXTURES_DIR / "sample_msa.txt"
    claims_path = FIXTURES_DIR / "claims.json"
    if not msa_path.is_file():
        raise DocImprintError(f"missing fixture: {msa_path}", code="MISSING_FIXTURE")
    if not claims_path.is_file():
        raise DocImprintError(f"missing fixture: {claims_path}", code="MISSING_FIXTURE")

    claims_doc = json.loads(claims_path.read_text(encoding="utf-8"))
    claims = claims_doc.get("claims") or []
    if not isinstance(claims, list) or len(claims) < 2:
        raise DocImprintError(
            "fixtures/claims.json must contain at least two claim strings",
            code="INVALID_FIXTURE",
        )
    return msa_path.read_bytes(), [str(c) for c in claims], msa_path


def run(
    *,
    notarize: bool,
    api_key: str,
    base_url: str,
    allow_missing_receipt: bool = False,
) -> dict[str, Any]:
    file_bytes, claims, fixture_path = _load_fixture()
    warnings: list[str] = []

    console.print(
        Panel.fit(
            "[bold]Problem[/]\n"
            "An agent asserted two clauses about this MSA.\n"
            "A chat log cannot prove either claim — DocImprint can.",
            title="Prove what the agent read",
            border_style="magenta",
        )
    )
    console.print(f"[dim]Fixture:[/] {fixture_path}")
    console.print()

    with open_session(api_key, base_url) as session:
        # 1) Stored claim-check — verdicts + evidence bundle in one capture
        console.print("[bold]1/3[/] Claim-check + store evidence bundle…")
        claims_resp = extract_uploaded_file(
            session.http,
            file_bytes=file_bytes,
            filename="sample_msa.txt",
            mode="claim-check",
            claims=claims,
            lean=False,
            retries=3,
            wait_for_job=session.client.wait_for_job,
        )
        rows = claim_rows(claims_resp)
        print_claim_table(rows)
        assert_claim_gotcha(rows)

        bundle_id = bundle_id_of(claims_resp)
        if not bundle_id:
            raise DocImprintError(
                "claim-check response missing bundle_id",
                code="MISSING_BUNDLE_ID",
                details=claims_resp,
            )
        manifest = manifest_sha256(claims_resp)
        console.print(f"  bundle_id = [cyan]{bundle_id}[/]")
        console.print(f"  manifest  = [cyan]{manifest or '—'}[/]")
        console.print()

        # 2) Verify + inline receipt
        console.print("[bold]2/3[/] Verifying bundle integrity…")
        verified = session.client.verify(bundle_id)
        if not verified.get("valid"):
            raise DocImprintError(
                "bundle verification failed",
                code="VERIFY_INVALID",
                details=verified,
            )
        inline = verified.get("receipt") if isinstance(verified.get("receipt"), dict) else None
        inline_rid = receipt_id(inline)
        console.print("  valid = [green]true[/]")
        if inline_rid:
            console.print(f"  inline receipt_id = [cyan]{inline_rid}[/]")
        else:
            warnings.append(
                "verify returned no inline receipt — will try list_receipts next"
            )
        console.print()

        notarize_summary: dict[str, Any] | None = None
        if notarize:
            console.print("[bold cyan]Optional[/] Notarizing on-chain…")
            notarized = session.client.notarize(bundle_id)
            notarize_summary = {
                "attestation": notarized.get("attestation"),
                "receipt_id": receipt_id(
                    notarized.get("receipt") if isinstance(notarized.get("receipt"), dict) else None
                ),
            }
            console.print(f"  attestation = {notarize_summary.get('attestation')}")
            console.print()

        # 3) Independent receipt audit (required unless explicitly waived)
        console.print("[bold]3/3[/] Independently verifying the action receipt…")
        receipt_verify, receipt_rows, receipt_warnings = require_valid_receipt(
            session.client,
            bundle_id=bundle_id,
            preferred_id=inline_rid,
            allow_missing=allow_missing_receipt,
        )
        warnings.extend(receipt_warnings)
        if receipt_verify:
            console.print(
                f"  receipt valid = [green]true[/]  "
                f"(signature_valid={receipt_verify.get('signature_valid')}, "
                f"manifest_matches_current={receipt_verify.get('manifest_matches_current')})"
            )
        else:
            console.print("  [yellow]skipped[/] (no receipt)")
        console.print()

        pack = {
            "demo": "prove_what_agent_read",
            "fixture": str(fixture_path.name),
            "claims_input": claims,
            "claim_results": rows,
            "bundle_id": bundle_id,
            "manifest_sha256": manifest or manifest_sha256(verified),
            "verify": {
                "valid": True,
                "manifest_sha256": manifest_sha256(verified) or manifest,
                "checks": verified.get("checks"),
            },
            "notarize": notarize_summary,
            "inline_receipt_id": inline_rid,
            "receipt_list_count": len(receipt_rows),
            "receipt_verify": receipt_verify,
            "links": {
                "verify_ui": verify_tool_url(bundle_id),
                "verify_api": api_verify_url(base_url, bundle_id),
            },
            "warnings": warnings,
        }
        pack_path = write_evidence_pack(bundle_id, pack)
        print_share_panel(
            bundle_id=bundle_id,
            manifest=pack["manifest_sha256"],
            base_url=base_url,
            receipt_verify=receipt_verify,
            pack_path=pack_path,
        )
        print_warnings(warnings)
        return pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prove what an AI agent read: claim-check a local MSA fixture, "
            "store a signed evidence bundle, verify it, and audit the action receipt."
        )
    )
    parser.add_argument(
        "--notarize",
        action="store_true",
        help="Also notarize the bundle on-chain (uses plan quota / credits)",
    )
    parser.add_argument(
        "--allow-missing-receipt",
        action="store_true",
        help="Do not fail if the API returns no signed action receipt (dev only)",
    )
    args = parser.parse_args(argv)

    try:
        api_key, base_url = load_config()
        run(
            notarize=args.notarize,
            api_key=api_key,
            base_url=base_url,
            allow_missing_receipt=args.allow_missing_receipt,
        )
    except DocImprintError as exc:
        print_error(exc)
        return 1
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
