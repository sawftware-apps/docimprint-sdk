"""Evidence + receipt deep dive: URL extract → verify → optional notarize → receipt audit.

Usage:
  python -m docimprint_examples.production_flow --url https://example.com/contract.pdf
  python -m docimprint_examples.production_flow --url https://example.com/contract.pdf --notarize
"""

from __future__ import annotations

import argparse
from typing import Any

from docimprint import DocImprintError
from rich.panel import Panel

from docimprint_examples.shared import (
    api_verify_url,
    bundle_id_of,
    console,
    json_dump,
    load_config,
    manifest_sha256,
    open_session,
    print_error,
    print_share_panel,
    print_warnings,
    receipt_id,
    require_valid_receipt,
    verify_tool_url,
    write_evidence_pack,
)


def run(
    *,
    url: str,
    notarize: bool,
    api_key: str,
    base_url: str,
    allow_missing_receipt: bool = False,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "demo": "production_flow",
        "source_url": url,
        "bundle_id": None,
        "manifest_sha256": None,
        "verify": None,
        "notarize": None,
        "inline_receipt_id": None,
        "receipt_list_count": 0,
        "receipt_verify": None,
        "warnings": [],
    }

    console.print(
        Panel.fit(
            "[bold]Evidence + receipt[/]\n"
            "Extract a URL into a signed bundle, verify integrity, "
            "then independently audit the action receipt.",
            border_style="blue",
        )
    )

    with open_session(api_key, base_url) as session:
        extracted = session.client.extract(url=url)
        bundle_id = bundle_id_of(extracted)
        if not bundle_id:
            raise DocImprintError(
                "extract response missing bundle_id",
                code="MISSING_BUNDLE_ID",
                details=extracted,
            )

        manifest = manifest_sha256(extracted)
        summary["bundle_id"] = bundle_id
        summary["manifest_sha256"] = manifest
        console.print(f"  bundle_id = [cyan]{bundle_id}[/]")
        console.print(f"  manifest  = [cyan]{manifest or '—'}[/]")

        verified = session.client.verify(bundle_id)
        inline_receipt = (
            verified.get("receipt") if isinstance(verified.get("receipt"), dict) else None
        )
        summary["verify"] = {
            "valid": bool(verified.get("valid")),
            "manifest_sha256": manifest_sha256(verified) or manifest,
            "checks": verified.get("checks"),
        }
        summary["inline_receipt_id"] = receipt_id(inline_receipt)

        if not verified.get("valid"):
            raise DocImprintError(
                "bundle verification failed",
                code="VERIFY_INVALID",
                details=verified,
            )
        console.print("  verify   = [green]valid[/]")

        if notarize:
            notarized = session.client.notarize(bundle_id)
            notarize_receipt = (
                notarized.get("receipt") if isinstance(notarized.get("receipt"), dict) else None
            )
            summary["notarize"] = {
                "attestation": notarized.get("attestation"),
                "receipt_id": receipt_id(notarize_receipt),
            }
            console.print("  notarize = done")

        receipt_verify, receipt_rows, receipt_warnings = require_valid_receipt(
            session.client,
            bundle_id=bundle_id,
            preferred_id=summary["inline_receipt_id"],
            allow_missing=allow_missing_receipt,
        )
        summary["warnings"].extend(receipt_warnings)
        summary["receipt_list_count"] = len(receipt_rows)
        summary["receipt_verify"] = receipt_verify
        if receipt_verify:
            console.print("  receipt  = [green]valid[/]")

        summary["links"] = {
            "verify_ui": verify_tool_url(bundle_id),
            "verify_api": api_verify_url(base_url, bundle_id),
        }
        pack_path = write_evidence_pack(bundle_id, summary)
        print_share_panel(
            bundle_id=bundle_id,
            manifest=summary["manifest_sha256"],
            base_url=base_url,
            receipt_verify=summary.get("receipt_verify"),
            pack_path=pack_path,
        )
        print_warnings(summary["warnings"])
        return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Production DocImprint flow: extract a source URL into an evidence bundle, "
            "verify integrity, optionally notarize on-chain, then independently verify "
            "the signed action receipt."
        )
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Source document URL to extract (PDF, HTML, etc.)",
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
        summary = run(
            url=args.url,
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

    json_dump({"ok": True, **summary})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
