"""Unit tests for CrewAI tools and formatters."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from docimprint.crewai import DocImprintToolkit
from docimprint.crewai.formatters import format_check_claims_response, format_extract_response
from docimprint.crewai.toolkit import DocImprintToolkit as ToolkitClass
from docimprint.crewai.tools.extract import ExtractEvidenceTool, QATool, SummarizeTool
from docimprint.errors import DocImprintError


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def toolkit(mock_client: MagicMock) -> DocImprintToolkit:
    return DocImprintToolkit(api_key="key", collection_id="col_test", client=mock_client)


def test_format_extract_response() -> None:
    text = format_extract_response(
        {
            "bundle_id": "ev_abc",
            "provenance": {"manifest_sha256": "deadbeef", "signature": {"signature": "0x1"}},
            "metadata": {"url": "https://example.com", "captured_at": "2024-01-01"},
            "result": {
                "summary": "A contract",
                "citations": [{"quote": "payment in 90 days", "section": "§2.1"}],
            },
        }
    )
    assert "EVIDENCE BUNDLE ev_abc" in text
    assert "signature present — run verify_bundle to confirm" in text
    assert "EIP-191 signed" not in text
    assert "payment in 90 days" in text
    assert "→ Bundle ID: ev_abc" in text


def test_format_check_claims_response() -> None:
    text = format_check_claims_response(
        {
            "bundle_id": "ev_x",
            "result": {
                "claims": [
                    {"claim": "True claim", "status": "supported", "evidence": {"quote": "yes"}},
                    {"claim": "False claim", "status": "refuted", "evidence": {"quote": "no"}},
                ]
            },
        }
    )
    assert "✓ TRUE" in text
    assert "✗ FALSE" in text


def test_extract_tool_success(mock_client: MagicMock) -> None:
    mock_client.extract.return_value = {
        "bundle_id": "ev_tool",
        "provenance": {"manifest_sha256": "abc"},
        "metadata": {"url": "https://example.com"},
        "result": {"summary": "done"},
    }
    tool = ExtractEvidenceTool(client=mock_client)
    out = tool.run("https://example.com")
    assert "ev_tool" in out
    mock_client.extract.assert_called_once_with(url="https://example.com")


def test_extract_tool_error_string(mock_client: MagicMock) -> None:
    mock_client.extract.side_effect = DocImprintError("Insufficient credits", status=402, code="PAYMENT_REQUIRED")
    tool = ExtractEvidenceTool(client=mock_client)
    out = tool.run("https://example.com")
    assert out.startswith("ERROR:")
    assert "Insufficient credits" in out


def test_summarize_tool(mock_client: MagicMock) -> None:
    mock_client.summarize.return_value = {"result": {"summary": "Hi", "key_points": ["a"]}}
    out = SummarizeTool(client=mock_client).run("https://example.com")
    assert "Hi" in out
    assert "KEY POINTS" in out


def test_qa_tool(mock_client: MagicMock) -> None:
    mock_client.qa.return_value = {"result": {"answer": "Yes", "citations": [{"quote": "proof"}]}}
    out = QATool(client=mock_client).run("https://example.com", "Is it true?")
    assert "Yes" in out
    assert "proof" in out


def test_toolkit_research_tools(toolkit: DocImprintToolkit) -> None:
    tools = toolkit.research_tools()
    assert len(tools) == 4
    names = {t.name for t in tools}
    assert names == {"extract_evidence", "summarize_document", "ask_document", "check_claims"}


def test_toolkit_legal_tools(toolkit: DocImprintToolkit) -> None:
    tools = toolkit.legal_tools()
    assert len(tools) == 3
    names = {t.name for t in tools}
    assert names == {"check_claims", "verify_bundle", "notarize_bundle"}


def test_toolkit_collection_tools(toolkit: DocImprintToolkit) -> None:
    tools = toolkit.collection_tools()
    assert len(tools) == 3
    names = {t.name for t in tools}
    assert names == {"search_collection", "ask_collection", "add_to_collection"}


def test_toolkit_all_tools(toolkit: DocImprintToolkit) -> None:
    tools = toolkit.all_tools()
    assert len(tools) == 10
    assert len({t.name for t in tools}) == 10


def test_collection_tools_baked_in_collection_id(mock_client: MagicMock) -> None:
    mock_client.search_collection.return_value = {"results": []}
    toolkit = DocImprintToolkit(api_key="k", collection_id="col_secret", client=mock_client)
    search_tool = next(t for t in toolkit.collection_tools() if t.name == "search_collection")
    search_tool.run("query")
    mock_client.search_collection.assert_called_with("col_secret", "query", limit=10)


def test_collection_tools_require_collection_id(mock_client: MagicMock) -> None:
    toolkit = ToolkitClass(api_key="k", client=mock_client)
    with pytest.raises(ValueError, match="collection_id"):
        toolkit.collection_tools()


def test_crewai_imports() -> None:
    from docimprint.crewai import (
        CheckClaimsTool,
        DocImprintToolkit,
        ExtractEvidenceTool,
        NotarizeTool,
        QATool,
        SummarizeTool,
        TranslateTool,
        VerifyBundleTool,
        make_collection_tools,
    )

    assert all(
        cls is not None
        for cls in (
            DocImprintToolkit,
            ExtractEvidenceTool,
            SummarizeTool,
            QATool,
            CheckClaimsTool,
            TranslateTool,
            VerifyBundleTool,
            NotarizeTool,
            make_collection_tools,
        )
    )
