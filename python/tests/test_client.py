"""Unit tests for DocImprintClient."""

from __future__ import annotations

import httpx
import pytest
import respx

from docimprint.client import DocImprintClient
from docimprint.errors import DocImprintError


@pytest.fixture
def client() -> DocImprintClient:
    return DocImprintClient("dr_test_key", base_url="https://api.docimprint.com")


@respx.mock
def test_extract_sync(client: DocImprintClient) -> None:
    route = respx.post("https://api.docimprint.com/v1/extract").mock(
        return_value=httpx.Response(
            200,
            json={
                "bundle_id": "ev_test123",
                "status": "complete",
                "result": {"summary": "Test summary"},
                "provenance": {"manifest_sha256": "abc" * 21 + "a"},
                "metadata": {"url": "https://example.com"},
            },
        )
    )
    data = client.extract(url="https://example.com")
    assert data["bundle_id"] == "ev_test123"
    assert route.called
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer dr_test_key"


@respx.mock
def test_summarize(client: DocImprintClient) -> None:
    respx.post("https://api.docimprint.com/v1/summarize").mock(
        return_value=httpx.Response(
            200,
            json={"bundle_id": "ev_sum", "result": {"summary": "Short", "key_points": ["a"]}},
        )
    )
    data = client.summarize("https://example.com")
    assert data["result"]["summary"] == "Short"


@respx.mock
def test_qa(client: DocImprintClient) -> None:
    respx.post("https://api.docimprint.com/v1/qa").mock(
        return_value=httpx.Response(
            200,
            json={"result": {"answer": "42", "citations": [{"quote": "answer text"}]}},
        )
    )
    data = client.qa("https://example.com", "What is the answer?")
    assert data["result"]["answer"] == "42"


@respx.mock
def test_check_claims(client: DocImprintClient) -> None:
    respx.post("https://api.docimprint.com/v1/check-claims").mock(
        return_value=httpx.Response(
            200,
            json={
                "bundle_id": "ev_claims",
                "result": {
                    "claims": [
                        {"claim": "It rains", "status": "supported", "evidence": {"quote": "rain"}},
                    ]
                },
            },
        )
    )
    data = client.check_claims("https://example.com", ["It rains"])
    assert data["result"]["claims"][0]["status"] == "supported"


@respx.mock
def test_verify(client: DocImprintClient) -> None:
    respx.get("https://api.docimprint.com/v1/extract/ev_abc/verify").mock(
        return_value=httpx.Response(
            200,
            json={"valid": True, "manifest_sha256": "deadbeef", "checks": {"manifest_hash": True}},
        )
    )
    data = client.verify("ev_abc")
    assert data["valid"] is True


@respx.mock
def test_notarize(client: DocImprintClient) -> None:
    respx.post("https://api.docimprint.com/v1/extract/ev_abc/notarize").mock(
        return_value=httpx.Response(
            200,
            json={"attestation": {"tx_hash": "0xabc", "network": "Base Sepolia"}},
        )
    )
    data = client.notarize("ev_abc")
    assert data["attestation"]["tx_hash"] == "0xabc"


@respx.mock
def test_collections(client: DocImprintClient) -> None:
    respx.post("https://api.docimprint.com/v1/collections").mock(
        return_value=httpx.Response(201, json={"id": "col_1", "name": "Test"})
    )
    respx.get("https://api.docimprint.com/v1/collections").mock(
        return_value=httpx.Response(200, json={"collections": [{"id": "col_1"}]})
    )
    respx.post("https://api.docimprint.com/v1/collections/col_1/documents").mock(
        return_value=httpx.Response(200, json={"indexed": True})
    )
    respx.get("https://api.docimprint.com/v1/collections/col_1/search").mock(
        return_value=httpx.Response(
            200,
            json={"results": [{"text": "chunk", "bundle_id": "ev_1", "score": 0.9}]},
        )
    )
    respx.post("https://api.docimprint.com/v1/collections/col_1/ask").mock(
        return_value=httpx.Response(200, json={"answer": "yes", "citations": []})
    )

    created = client.create_collection("Test")
    assert created["id"] == "col_1"
    assert client.list_collections()[0]["id"] == "col_1"
    client.add_to_collection("col_1", "ev_abc")
    search = client.search_collection("col_1", "query")
    assert search["results"][0]["bundle_id"] == "ev_1"
    ask = client.ask_collection("col_1", "question?")
    assert ask["answer"] == "yes"


@respx.mock
def test_get_quota(client: DocImprintClient) -> None:
    respx.get("https://api.docimprint.com/v1/quota").mock(
        return_value=httpx.Response(200, json={"credits_remaining": 100})
    )
    assert client.get_quota()["credits_remaining"] == 100


@respx.mock
def test_wait_for_job(client: DocImprintClient) -> None:
    respx.get("https://api.docimprint.com/v1/jobs/job_1").mock(
        side_effect=[
            httpx.Response(200, json={"status": "pending"}),
            httpx.Response(200, json={"status": "complete", "result": {"bundle_id": "ev_job"}}),
        ]
    )
    result = client.wait_for_job("job_1", timeout=10, poll_interval=0.01)
    assert result["bundle_id"] == "ev_job"


@respx.mock
def test_api_error_raises_docimprint_error(client: DocImprintClient) -> None:
    respx.post("https://api.docimprint.com/v1/summarize").mock(
        return_value=httpx.Response(
            402,
            json={"message": "Insufficient credits", "code": "PAYMENT_REQUIRED"},
            headers={"x-request-id": "req_123"},
        )
    )
    with pytest.raises(DocImprintError) as exc:
        client.summarize("https://example.com")
    assert exc.value.status == 402
    assert exc.value.code == "PAYMENT_REQUIRED"
    assert exc.value.request_id == "req_123"


@respx.mock
def test_provenance_and_handoff(client: DocImprintClient) -> None:
    respx.post("https://api.docimprint.com/v1/extract/ev_1/provenance").mock(
        return_value=httpx.Response(200, json={"logged": True})
    )
    respx.post("https://api.docimprint.com/v1/extract/ev_1/handoff").mock(
        return_value=httpx.Response(200, json={"handoff": True})
    )
    client.log_provenance("ev_1", "agent-a", "read")
    client.handoff("ev_1", "agent-a", "agent-b", "review complete")
