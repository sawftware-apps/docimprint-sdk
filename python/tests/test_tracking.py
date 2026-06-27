"""Tests for ProvenanceTracker audit trail."""

from __future__ import annotations

import pytest

from docimprint.crewai import DocImprintToolkit, ProvenanceTracker, extract_bundle_ids
from docimprint.crewai.tracking import ProvenanceTracker as TrackerClass
from docimprint.errors import DocImprintError


SAMPLE_EXTRACT_OUTPUT = """\
EVIDENCE BUNDLE ev_abc123 | sha256:deadbeef (signature present — run verify_bundle to confirm)
Source: https://example.com/contract.pdf | Captured: 2024-01-15T10:30Z

SUMMARY:
The agreement sets a 90-day payment window.

→ Bundle ID: ev_abc123 (pass to VerifyBundleTool)
"""

SAMPLE_CLAIMS_OUTPUT = """\
CLAIM CHECK RESULTS for ev_claims99

✓ TRUE     "The penalty is 1.5% monthly"
"""


class MockExtractTool:
    name = "ExtractEvidenceTool"

    def __init__(self) -> None:
        self.calls = 0

    def _run(self, url: str) -> str:
        self.calls += 1
        return SAMPLE_EXTRACT_OUTPUT


class MockVerifyTool:
    name = "VerifyBundleTool"

    def _run(self, bundle_id: str) -> str:
        return f"INTEGRITY OK for {bundle_id}"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (SAMPLE_EXTRACT_OUTPUT, ["ev_abc123"]),
        (SAMPLE_CLAIMS_OUTPUT, ["ev_claims99"]),
        ("ERROR: insufficient credits", []),
        ("no bundles here", []),
        (
            "[Source: bundle ev_src1, page 2] and ev_other",
            ["ev_src1", "ev_other"],
        ),
    ],
)
def test_extract_bundle_ids(text: str, expected: list[str]) -> None:
    assert extract_bundle_ids(text) == expected


def test_track_crew_logs_provenance_on_tool_run(httpx_mock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.example.com/v1/extract/ev_abc123/provenance",
        json={"provenance_id": "prov_1"},
        status_code=201,
    )

    toolkit = DocImprintToolkit("test-key", base_url="https://api.example.com")
    tool = MockExtractTool()
    toolkit.register_tools(tool)

    with toolkit.track_crew("due-diligence-matter-1") as tracker:
        assert isinstance(tracker, TrackerClass)
        output = tool._run("https://example.com/contract.pdf")

    assert "ev_abc123" in output
    assert tool.calls == 1
    request = httpx_mock.get_request()
    import json

    body = json.loads(request.content)
    assert body["agent_id"] == "due-diligence-matter-1"
    assert body["action"] == "ExtractEvidenceTool"
    assert "contract.pdf" in body["query"]
    assert "EVIDENCE BUNDLE ev_abc123" in body["result_summary"]


def test_tracker_restores_original_run_after_exit() -> None:
    toolkit = DocImprintToolkit("test-key", base_url="https://api.example.com")
    tool = MockExtractTool()
    toolkit.register_tools(tool)
    original_func = tool._run.__func__

    with toolkit.track_crew("crew-a"):
        assert getattr(tool._run, "__provenance_wrapped__", False)

    assert not getattr(tool._run, "__provenance_wrapped__", False)
    assert tool._run.__func__ is original_func
    assert tool._run("https://example.com") == SAMPLE_EXTRACT_OUTPUT
    assert tool.calls == 1


def test_record_handoff_calls_client(httpx_mock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.example.com/v1/extract/ev_abc123/handoff",
        json={"handoff_id": "hand_1"},
        status_code=201,
    )

    toolkit = DocImprintToolkit("test-key", base_url="https://api.example.com")
    tracker = ProvenanceTracker(toolkit, "crew-a")

    result = tracker.record_handoff("ev_abc123", "researcher", "lawyer", note="legal review")
    assert result["handoff_id"] == "hand_1"


def test_multiple_tools_and_bundles_log_separately(httpx_mock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.example.com/v1/extract/ev_one/provenance",
        json={"provenance_id": "prov_1"},
        status_code=201,
    )
    httpx_mock.add_response(
        method="POST",
        url="https://api.example.com/v1/extract/ev_two/provenance",
        json={"provenance_id": "prov_2"},
        status_code=201,
    )

    class MultiBundleTool:
        name = "CheckClaimsTool"

        def _run(self, bundle_id: str) -> str:
            return (
                "CLAIM CHECK RESULTS for ev_one\n\n"
                "Also referenced ev_two in a citation."
            )

    toolkit = DocImprintToolkit("test-key", base_url="https://api.example.com")
    tool = MultiBundleTool()
    toolkit.register_tools(tool)

    with toolkit.track_crew("claims-crew", agent_id="legal-analyst"):
        tool._run("ev_one")

    import json

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    agents = {json.loads(req.content)["agent_id"] for req in requests}
    assert agents == {"legal-analyst"}


def test_error_output_skips_provenance_logging(httpx_mock) -> None:
    class ErrorTool:
        name = "ExtractEvidenceTool"

        def _run(self, url: str) -> str:
            return "ERROR: Payment required — insufficient credits."

    toolkit = DocImprintToolkit("test-key", base_url="https://api.example.com")
    tool = ErrorTool()
    toolkit.register_tools(tool)

    with toolkit.track_crew("crew-a"):
        tool._run("https://example.com")

    assert len(httpx_mock.get_requests()) == 0


def test_verify_output_without_bundle_marker_still_logs_when_id_present(httpx_mock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.example.com/v1/extract/ev_verify1/provenance",
        json={"provenance_id": "prov_1"},
        status_code=201,
    )

    toolkit = DocImprintToolkit("test-key", base_url="https://api.example.com")
    tool = MockVerifyTool()
    toolkit.register_tools(tool)

    with toolkit.track_crew("crew-a"):
        tool._run("ev_verify1")

    request = httpx_mock.get_request()
    import json

    body = json.loads(request.content)
    assert body["action"] == "VerifyBundleTool"
