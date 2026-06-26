"""Tests for provenance client methods."""

from __future__ import annotations

import httpx
import pytest

from docimprint.client import DocImprintClient
from docimprint.errors import DocImprintError


def test_log_provenance_posts_expected_payload(httpx_mock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.example.com/v1/extract/ev_abc123/provenance",
        json={"provenance_id": "prov_1", "bundle_id": "ev_abc123"},
        status_code=201,
    )

    client = DocImprintClient("test-key", base_url="https://api.example.com")
    result = client.log_provenance(
        "ev_abc123",
        "due-diligence-crew",
        "ExtractEvidenceTool",
        query="url='https://example.com'",
        result_summary="extracted bundle",
    )

    assert result["provenance_id"] == "prov_1"
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["authorization"] == "Bearer test-key"
    import json

    body = json.loads(request.content)
    assert body == {
        "agent_id": "due-diligence-crew",
        "action": "ExtractEvidenceTool",
        "query": "url='https://example.com'",
        "result_summary": "extracted bundle",
    }


def test_handoff_posts_expected_payload(httpx_mock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.example.com/v1/extract/ev_abc123/handoff",
        json={"handoff_id": "hand_1", "bundle_id": "ev_abc123"},
        status_code=201,
    )

    client = DocImprintClient("test-key", base_url="https://api.example.com")
    result = client.handoff("ev_abc123", "researcher", "lawyer", note="review claims")

    assert result["handoff_id"] == "hand_1"
    import json

    request = httpx_mock.get_request()
    body = json.loads(request.content)
    assert body == {
        "from_agent": "researcher",
        "to_agent": "lawyer",
        "note": "review claims",
    }


def test_request_raises_docimprint_error(httpx_mock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.example.com/v1/extract/ev_missing/provenance",
        json={"error": "Bundle not found", "code": "not_found"},
        status_code=404,
        headers={"x-request-id": "req_123"},
    )

    client = DocImprintClient("test-key", base_url="https://api.example.com")
    with pytest.raises(DocImprintError) as exc:
        client.log_provenance("ev_missing", "agent", "action")

    assert exc.value.status == 404
    assert exc.value.code == "not_found"
    assert exc.value.request_id == "req_123"
