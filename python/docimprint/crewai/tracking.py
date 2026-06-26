"""Provenance audit trail for CrewAI tool runs."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, Protocol

from docimprint.crewai.toolkit import DocImprintToolkit

# Matches DocImprint bundle ids in canonical tool output (ev_…).
_BUNDLE_ID_RE = re.compile(r"\bev_[a-zA-Z0-9][a-zA-Z0-9_-]*\b")

# Prefer explicit markers from formatted tool output when present.
_BUNDLE_ID_MARKERS = (
    re.compile(r"EVIDENCE BUNDLE\s+(ev_[a-zA-Z0-9][a-zA-Z0-9_-]*)", re.IGNORECASE),
    re.compile(r"Bundle ID:\s*(ev_[a-zA-Z0-9][a-zA-Z0-9_-]*)", re.IGNORECASE),
    re.compile(r"CLAIM CHECK RESULTS for\s+(ev_[a-zA-Z0-9][a-zA-Z0-9_-]*)", re.IGNORECASE),
    re.compile(r"\[Source:\s*bundle\s+(ev_[a-zA-Z0-9][a-zA-Z0-9_-]*)", re.IGNORECASE),
)

_RESULT_SUMMARY_LIMIT = 500


class _RunnableTool(Protocol):
    name: str

    def _run(self, *args: Any, **kwargs: Any) -> str: ...


def extract_bundle_ids(output: str) -> list[str]:
    """Extract unique bundle ids from DocImprint tool output text."""
    if not output or output.startswith("ERROR:"):
        return []

    ordered: list[str] = []
    seen: set[str] = set()

    for pattern in _BUNDLE_ID_MARKERS:
        for match in pattern.finditer(output):
            bundle_id = match.group(1)
            if bundle_id not in seen:
                seen.add(bundle_id)
                ordered.append(bundle_id)

    for match in _BUNDLE_ID_RE.finditer(output):
        bundle_id = match.group(0)
        if bundle_id not in seen:
            seen.add(bundle_id)
            ordered.append(bundle_id)

    return ordered


def _format_query(*args: Any, **kwargs: Any) -> str | None:
    parts: list[str] = []
    if args:
        parts.append(", ".join(repr(arg) for arg in args))
    if kwargs:
        parts.append(", ".join(f"{key}={value!r}" for key, value in kwargs.items()))
    if not parts:
        return None
    return "; ".join(parts)


class ProvenanceTracker:
    """Context manager that auto-logs tool calls touching DocImprint bundles."""

    def __init__(
        self,
        toolkit: DocImprintToolkit,
        crew_name: str,
        *,
        agent_id: str | None = None,
    ) -> None:
        self.toolkit = toolkit
        self.crew_name = crew_name
        self.agent_id = agent_id or crew_name
        self._patched: list[tuple[_RunnableTool, Callable[..., str]]] = []
        self._active = False

    def __enter__(self) -> ProvenanceTracker:
        self._patch_tools()
        self._active = True
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self._restore_tools()
        self._active = False

    def record_handoff(
        self,
        bundle_id: str,
        from_agent: str,
        to_agent: str,
        note: str = "",
    ) -> dict[str, Any]:
        """Record a multi-agent handoff for chain-of-custody."""
        return self.toolkit.client.handoff(bundle_id, from_agent, to_agent, note)

    def _patch_tools(self) -> None:
        for tool in self.toolkit.trackable_tools():
            if not hasattr(tool, "_run"):
                continue
            original = tool._run
            if getattr(original, "__provenance_wrapped__", False):
                continue

            def patched_run(
                *args: Any,
                _original: Callable[..., str] = original,
                _tool: _RunnableTool = tool,
                **kwargs: Any,
            ) -> str:
                output = _original(*args, **kwargs)
                self._log_tool_output(_tool, output, args=args, kwargs=kwargs)
                return output

            patched_run.__provenance_wrapped__ = True  # type: ignore[attr-defined]
            tool._run = patched_run  # type: ignore[method-assign]
            self._patched.append((tool, original))

    def _restore_tools(self) -> None:
        for tool, original in self._patched:
            tool._run = original  # type: ignore[method-assign]
        self._patched.clear()

    def _log_tool_output(
        self,
        tool: _RunnableTool,
        output: str,
        *,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> None:
        bundle_ids = extract_bundle_ids(output)
        if not bundle_ids:
            return

        action = getattr(tool, "name", tool.__class__.__name__)
        query = _format_query(*args, **kwargs)
        summary = output[:_RESULT_SUMMARY_LIMIT]

        for bundle_id in bundle_ids:
            self.toolkit.client.log_provenance(
                bundle_id,
                self.agent_id,
                action,
                query=query,
                result_summary=summary,
            )
