"""Unit tests for demo helpers (no live API calls)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from docimprint import DocImprintClient, DocImprintError

from docimprint_examples.shared import (
    assert_claim_gotcha,
    claim_rows,
    extract_uploaded_file,
    manifest_sha256,
    pick_receipt_for_verify,
    receipt_id,
    require_valid_receipt,
)


def test_manifest_sha256_from_provenance() -> None:
    assert (
        manifest_sha256({"provenance": {"manifest_sha256": "abc"}}) == "abc"
    )
    assert manifest_sha256({"manifest_sha256": "top"}) == "top"


def test_claim_rows_normalizes_shapes() -> None:
    rows = claim_rows(
        {"result": {"claim_results": [{"claim": "a", "status": "supported"}]}}
    )
    assert rows[0]["status"] == "supported"


def test_assert_claim_gotcha() -> None:
    assert_claim_gotcha(
        [
            {"status": "supported"},
            {"status": "contradicted"},
        ]
    )
    with pytest.raises(DocImprintError) as exc:
        assert_claim_gotcha([{"status": "supported"}, {"status": "supported"}])
    assert exc.value.code == "CLAIM_GOTCHA_MISSING"


def test_pick_receipt_prefers_verify_action() -> None:
    rows = [
        {"id": "rcpt_1", "action": "get_bundle"},
        {"id": "rcpt_2", "action": "verify_bundle"},
    ]
    chosen = pick_receipt_for_verify(rows, preferred_id=None)
    assert receipt_id(chosen) == "rcpt_2"


@respx.mock
def test_extract_uploaded_file_retries_processing_error() -> None:
    route = respx.post("https://api.docimprint.com/v1/extract").mock(
        side_effect=[
            httpx.Response(
                500,
                json={"message": "Unexpected AI response format", "code": "PROCESSING_ERROR"},
            ),
            httpx.Response(
                200,
                json={
                    "bundle_id": "ev_abc123",
                    "result": {
                        "claims": [
                            {"claim": "yes", "status": "supported"},
                            {"claim": "no", "status": "contradicted"},
                        ]
                    },
                    "provenance": {"manifest_sha256": "deadbeef"},
                },
            ),
        ]
    )
    http = httpx.Client(base_url="https://api.docimprint.com")
    data = extract_uploaded_file(
        http,
        file_bytes=b"hello",
        filename="sample_msa.txt",
        mode="claim-check",
        claims=["yes", "no"],
        retries=2,
    )
    assert data["bundle_id"] == "ev_abc123"
    assert route.call_count == 2
    http.close()


@respx.mock
def test_require_valid_receipt_success() -> None:
    respx.get("https://api.docimprint.com/v1/extract/ev_abc123/receipts").mock(
        return_value=httpx.Response(
            200,
            json={
                "bundle_id": "ev_abc123",
                "receipts": [
                    {
                        "id": "rcpt_1",
                        "action": "verify_bundle",
                        "manifest_sha256": "abc",
                    }
                ],
            },
        )
    )
    respx.get("https://api.docimprint.com/v1/extract/receipts/rcpt_1/verify").mock(
        return_value=httpx.Response(
            200,
            json={
                "receipt_id": "rcpt_1",
                "valid": True,
                "signature_valid": True,
                "manifest_matches_current": True,
                "action": "verify_bundle",
            },
        )
    )
    with DocImprintClient("test-key", base_url="https://api.docimprint.com") as client:
        verified, rows, warnings = require_valid_receipt(
            client,
            bundle_id="ev_abc123",
            preferred_id="rcpt_1",
            allow_missing=False,
        )
    assert verified is not None
    assert verified["valid"] is True
    assert len(rows) == 1
    assert warnings == []


@respx.mock
def test_require_valid_receipt_missing_fails() -> None:
    respx.get("https://api.docimprint.com/v1/extract/ev_abc123/receipts").mock(
        return_value=httpx.Response(
            200,
            json={"bundle_id": "ev_abc123", "receipts": []},
        )
    )
    with DocImprintClient("test-key", base_url="https://api.docimprint.com") as client:
        with pytest.raises(DocImprintError) as exc:
            require_valid_receipt(
                client,
                bundle_id="ev_abc123",
                preferred_id=None,
                allow_missing=False,
            )
    assert exc.value.code == "RECEIPT_MISSING"
