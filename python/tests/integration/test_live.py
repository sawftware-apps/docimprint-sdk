"""Live integration tests — skipped unless DOCIMPRINT_API_KEY is set."""

from __future__ import annotations

import os

import pytest

from docimprint import DocImprintClient
from docimprint.crewai import DocImprintToolkit
from docimprint.crewai.tools.extract import ExtractEvidenceTool

pytestmark = pytest.mark.skipif(
    not os.environ.get("DOCIMPRINT_API_KEY"),
    reason="DOCIMPRINT_API_KEY not set",
)

SAMPLE_URL = "https://example.com"


@pytest.fixture
def live_client() -> DocImprintClient:
    return DocImprintClient(os.environ["DOCIMPRINT_API_KEY"])


def test_live_quota(live_client: DocImprintClient) -> None:
    quota = live_client.get_quota()
    assert "credits_remaining" in quota or quota


def test_live_summarize(live_client: DocImprintClient) -> None:
    result = live_client.summarize(SAMPLE_URL, timeout=120)
    assert result.get("result") or result.get("bundle_id")


def test_live_extract_and_verify_roundtrip(live_client: DocImprintClient) -> None:
    """Full evidence bundle path: POST /v1/extract → bundle_id → GET verify."""
    result = live_client.extract(url=SAMPLE_URL, timeout=120)
    bundle_id = result.get("bundle_id")
    assert bundle_id and str(bundle_id).startswith("ev_"), result

    verify = live_client.verify(bundle_id, quick=True)
    assert verify.get("valid") is True, verify


def test_live_crewai_extract_tool(live_client: DocImprintClient) -> None:
    """CrewAI ExtractEvidenceTool against production API."""
    tool = ExtractEvidenceTool(client=live_client)
    output = tool._run(SAMPLE_URL)
    assert "ev_" in output
    assert "BUNDLE" in output.upper() or "bundle" in output.lower()


def test_live_toolkit_research_tools() -> None:
    toolkit = DocImprintToolkit(api_key=os.environ["DOCIMPRINT_API_KEY"], collection_id="skip")
    tools = toolkit.research_tools()
    assert len(tools) == 4
