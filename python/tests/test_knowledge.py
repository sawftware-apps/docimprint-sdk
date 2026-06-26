"""Tests for DocImprint knowledge source integration."""

from __future__ import annotations

import httpx
import pytest

from docimprint.client import DocImprintClient
from docimprint.crewai.knowledge import (
    DocImprintKnowledgeSource,
    format_search_hit,
    format_search_results,
)
from docimprint.crewai.toolkit import DocImprintToolkit


def test_format_search_hit_includes_bundle_provenance() -> None:
    hit = format_search_hit(
        {
            "bundle_id": "ev_abc123",
            "chunk_id": "chunk_1",
            "text": "Payment within 90 days.",
            "score": 0.91,
            "artifact": "page-3",
        }
    )
    assert "ev_abc123" in hit["content"]
    assert hit["metadata"]["bundle_id"] == "ev_abc123"
    assert hit["score"] == pytest.approx(0.91)


def test_format_search_results_maps_payload() -> None:
    payload = {
        "collection_id": "col_1",
        "query": "payment terms",
        "results": [
            {"bundle_id": "ev_1", "text": "90 days", "score": 0.8},
        ],
    }
    results = format_search_results(payload)
    assert len(results) == 1
    assert results[0]["metadata"]["bundle_id"] == "ev_1"


def test_knowledge_storage_search_filters_by_score(httpx_mock) -> None:
    from docimprint.crewai.knowledge import DocImprintKnowledgeStorage

    httpx_mock.add_response(
        method="GET",
        url="https://api.docimprint.com/v1/collections/col_1/search?q=payment+terms&limit=5",
        json={
            "results": [
                {"bundle_id": "ev_high", "text": "high", "score": 0.9},
                {"bundle_id": "ev_low", "text": "low", "score": 0.1},
            ]
        },
    )
    client = DocImprintClient(api_key="test-key")
    storage = DocImprintKnowledgeStorage(collection_id="col_1", client=client)
    hits = storage.search(["payment terms"], limit=5, score_threshold=0.5)
    assert len(hits) == 1
    assert hits[0]["metadata"]["bundle_id"] == "ev_high"


def test_knowledge_source_add_url_extracts_and_indexes(httpx_mock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.docimprint.com/v1/extract?sync=true&store=true",
        json={"bundle_id": "ev_new", "status": "complete"},
    )
    httpx_mock.add_response(
        method="POST",
        url="https://api.docimprint.com/v1/collections/col_lib/documents",
        json={"collection_id": "col_lib", "bundle_id": "ev_new", "status": "indexed"},
    )

    toolkit = DocImprintToolkit(api_key="test-key")
    source = toolkit.knowledge_source("col_lib", wait_for_indexing=False)
    bundle_id = source.add_url("https://example.com/contract.pdf")

    assert bundle_id == "ev_new"
    requests = httpx_mock.get_requests()
    assert requests[0].url.path == "/v1/extract"
    assert requests[1].url.path == "/v1/collections/col_lib/documents"


def test_knowledge_source_query_returns_bundle_citations(httpx_mock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://api.docimprint.com/v1/collections/col_lib/search?q=late+fees&limit=5",
        json={
            "collection_id": "col_lib",
            "query": "late fees",
            "results": [
                {
                    "bundle_id": "ev_fee",
                    "chunk_id": "c1",
                    "text": "Late fees accrue at 1.5% per month.",
                    "score": 0.88,
                }
            ],
        },
    )

    toolkit = DocImprintToolkit(api_key="test-key")
    source = toolkit.knowledge_source("col_lib")
    results = source.query("late fees", limit=5)

    assert len(results) == 1
    assert "ev_fee" in results[0]["content"]
    assert results[0]["metadata"]["bundle_id"] == "ev_fee"


def test_toolkit_knowledge_source_factory() -> None:
    toolkit = DocImprintToolkit(api_key="test-key")
    source = toolkit.knowledge_source("col_x", ingest_urls=["https://example.com/a.pdf"])
    assert source.collection_id == "col_x"
    assert source.ingest_urls == ["https://example.com/a.pdf"]
    assert source.storage is not None
    assert source.storage.collection_id == "col_x"


def test_client_search_collection_raises_docimprint_error(httpx_mock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://api.docimprint.com/v1/collections/col_1/search?q=test&limit=10",
        status_code=503,
        json={"error": "Search unavailable", "code": "SEARCH_UNAVAILABLE"},
    )
    client = DocImprintClient(api_key="test-key")
    from docimprint.errors import DocImprintError

    with pytest.raises(DocImprintError) as exc:
        client.search_collection("col_1", "test")
    assert "Search unavailable" in str(exc.value)
