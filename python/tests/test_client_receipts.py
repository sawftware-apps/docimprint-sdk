"""Tests for signed action receipt client methods."""

from __future__ import annotations

import pytest

from docimprint.client import DocImprintClient
from docimprint.errors import DocImprintError


def test_list_receipts_sends_pagination_params(httpx_mock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://api.example.com/v1/extract/ev_abc123/receipts?limit=50&offset=0",
        json={
            "bundle_id": "ev_abc123",
            "receipts": [
                {
                    "id": "rcpt_1",
                    "bundle_id": "ev_abc123",
                    "agent_id": "cust:cus_1",
                    "action": "verify_bundle",
                    "manifest_sha256": "a" * 64,
                    "signature": "0xsig",
                    "signer_address": "0xabc",
                    "key_id": "v1",
                    "algorithm": "secp256k1-eip191",
                    "created_at": "2026-07-17T13:49:11.068Z",
                }
            ],
            "limit": 50,
            "offset": 0,
        },
        status_code=200,
    )

    client = DocImprintClient("test-key", base_url="https://api.example.com")
    result = client.list_receipts("ev_abc123")

    assert result["bundle_id"] == "ev_abc123"
    assert len(result["receipts"]) == 1
    assert result["receipts"][0]["id"] == "rcpt_1"
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["authorization"] == "Bearer test-key"


def test_verify_receipt_returns_verdict(httpx_mock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://api.example.com/v1/extract/receipts/rcpt_1/verify",
        json={
            "receipt_id": "rcpt_1",
            "valid": True,
            "signature_valid": True,
            "manifest_matches_current": True,
            "bundle_id": "ev_abc123",
            "agent_id": "cust:cus_1",
            "action": "verify_bundle",
            "manifest_sha256": "a" * 64,
            "signer_address": "0xabc",
            "signed_at": "2026-07-17T13:49:11.068Z",
            "tampered": [],
        },
        status_code=200,
    )

    client = DocImprintClient("test-key", base_url="https://api.example.com")
    result = client.verify_receipt("rcpt_1")

    assert result["valid"] is True
    assert result["signature_valid"] is True
    assert result["tampered"] == []


def test_verify_receipt_requires_receipt_id() -> None:
    client = DocImprintClient("test-key", base_url="https://api.example.com")
    with pytest.raises(DocImprintError) as exc:
        client.verify_receipt("")

    assert exc.value.code == "INVALID_RECEIPT_ID"


def test_verify_receipt_raises_on_not_found(httpx_mock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://api.example.com/v1/extract/receipts/rcpt_missing/verify",
        json={"error": "Receipt not found"},
        status_code=404,
        headers={"x-request-id": "req_456"},
    )

    client = DocImprintClient("test-key", base_url="https://api.example.com")
    with pytest.raises(DocImprintError) as exc:
        client.verify_receipt("rcpt_missing")

    assert exc.value.status == 404
    assert exc.value.request_id == "req_456"
