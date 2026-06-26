"""Live integration tests — skipped unless DOCIMPRINT_API_KEY is set."""

from __future__ import annotations

import os

import pytest

from docimprint import DocImprintClient
from docimprint.crewai import DocImprintToolkit

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


def test_live_toolkit_research_tools() -> None:
    toolkit = DocImprintToolkit(api_key=os.environ["DOCIMPRINT_API_KEY"], collection_id="skip")
    tools = toolkit.research_tools()
    assert len(tools) == 4
