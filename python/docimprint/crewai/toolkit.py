"""DocImprintToolkit — entry point for CrewAI integration."""

from __future__ import annotations

from typing import Any

from docimprint.client import DocImprintClient
from docimprint.crewai.base import BaseTool
from docimprint.crewai.tools.claims import CheckClaimsTool, TranslateTool, make_claims_tools
from docimprint.crewai.tools.collections import make_collection_tools
from docimprint.crewai.tools.extract import ExtractEvidenceTool, QATool, SummarizeTool, make_extract_tools
from docimprint.crewai.tools.verify import NotarizeTool, VerifyBundleTool, make_verify_tools


class DocImprintToolkit:
    """Bundles DocImprint client + CrewAI tools for agent crews."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = "https://api.docimprint.com",
        collection_id: str | None = None,
        client: DocImprintClient | None = None,
    ) -> None:
        if client is None and not api_key:
            raise ValueError("api_key is required when client is not provided")
        self.client = client or DocImprintClient(api_key=api_key, base_url=base_url)
        self._collection_id = collection_id
        self._extract_tools = make_extract_tools(self.client)
        self._verify_tools = make_verify_tools(self.client)
        self._claims_tools = make_claims_tools(self.client)
        self._collection_tools: list[BaseTool] = (
            make_collection_tools(self.client, collection_id) if collection_id else []
        )
        self._extra_tools: list[Any] = []

    def register_tools(self, *tools: Any) -> None:
        """Register extra tools included in tracking and tool groups."""
        self._extra_tools.extend(tools)

    def trackable_tools(self) -> list[BaseTool]:
        """All tools that ProvenanceTracker should wrap (no collection_id required)."""
        seen: set[str] = set()
        tools: list[BaseTool] = []
        for tool in (
            self._extract_tools
            + self._claims_tools
            + self._verify_tools
            + self._collection_tools
            + self._extra_tools
        ):
            if tool.name not in seen:
                seen.add(tool.name)
                tools.append(tool)
        return tools

    def research_tools(self) -> list[BaseTool]:
        """ExtractEvidenceTool, SummarizeTool, QATool, CheckClaimsTool."""
        return [
            self._extract_tools[0],
            self._extract_tools[1],
            self._extract_tools[2],
            self._claims_tools[0],
        ]

    def legal_tools(self) -> list[BaseTool]:
        """CheckClaimsTool, VerifyBundleTool, NotarizeTool."""
        return [
            self._claims_tools[0],
            self._verify_tools[0],
            self._verify_tools[1],
        ]

    def collection_tools(self) -> list[BaseTool]:
        """SearchCollectionTool, AskCollectionTool, AddToCollectionTool."""
        if not self._collection_tools:
            raise ValueError(
                "collection_id required at DocImprintToolkit construction for collection tools"
            )
        return list(self._collection_tools)

    def all_tools(self) -> list[BaseTool]:
        """All 10 tools (requires collection_id at construction)."""
        if not self._collection_tools:
            raise ValueError(
                "collection_id required at DocImprintToolkit construction for all_tools()"
            )
        seen: set[str] = set()
        tools: list[BaseTool] = []
        for tool in (
            self._extract_tools
            + self._claims_tools
            + self._verify_tools
            + self._collection_tools
        ):
            if tool.name not in seen:
                seen.add(tool.name)
                tools.append(tool)
        return tools

    def with_collection(self, collection_id: str) -> DocImprintToolkit:
        """Return a toolkit scoped to a specific collection."""
        return DocImprintToolkit(
            client=self.client,
            collection_id=collection_id,
        )

    def knowledge_source(
        self,
        collection_id: str,
        *,
        ingest_urls: list[str] | None = None,
        wait_for_indexing: bool = True,
    ):
        """Return a CrewAI knowledge source backed by a DocImprint collection."""
        from docimprint.crewai.knowledge import DocImprintKnowledgeSource

        return DocImprintKnowledgeSource(
            collection_id=collection_id,
            toolkit=self,
            ingest_urls=ingest_urls or [],
            wait_for_indexing=wait_for_indexing,
        )

    def track_crew(self, crew_name: str, *, agent_id: str | None = None):
        """Return a context manager that auto-logs bundle access during a crew run."""
        from docimprint.crewai.tracking import ProvenanceTracker

        return ProvenanceTracker(self, crew_name, agent_id=agent_id)


__all__ = [
    "DocImprintToolkit",
    "ExtractEvidenceTool",
    "SummarizeTool",
    "QATool",
    "CheckClaimsTool",
    "TranslateTool",
    "VerifyBundleTool",
    "NotarizeTool",
]
