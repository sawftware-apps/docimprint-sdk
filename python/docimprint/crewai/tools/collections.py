"""Collection search, ask, and indexing tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from docimprint.crewai.base import BaseTool
from docimprint.crewai.formatters import (
    format_add_to_collection_response,
    format_ask_collection_response,
    format_error,
    format_search_response,
)

if TYPE_CHECKING:
    from docimprint.client import DocImprintClient


class SearchInput(BaseModel):
    query: str = Field(..., description="Search query against indexed documents")
    limit: int = Field(10, description="Maximum number of results to return")


class AskCollectionInput(BaseModel):
    question: str = Field(..., description="Question to answer across all documents in the collection")


class AddToCollectionInput(BaseModel):
    bundle_id: str = Field(..., description="Evidence bundle ID to add to the collection")


class SearchCollectionTool(BaseTool):
    name: str = "search_collection"
    description: str = "Search indexed documents in a DocImprint collection. Costs 2 credits."
    args_schema: type[BaseModel] = SearchInput
    client: Any = Field(exclude=True)
    collection_id: str = Field(exclude=True)

    def model_post_init(self, __context: Any) -> None:
        self.description = (
            f"Search indexed documents in collection {self.collection_id}. "
            "Returns ranked chunks with bundle provenance. Costs 2 credits."
        )

    def _run(self, query: str, limit: int = 10) -> str:
        try:
            data = self.client.search_collection(self.collection_id, query, limit=limit)
            return format_search_response(data, self.collection_id)
        except Exception as exc:
            return format_error(exc)


class AskCollectionTool(BaseTool):
    name: str = "ask_collection"
    description: str = "Ask a question across documents in a DocImprint collection. Costs 3 credits."
    args_schema: type[BaseModel] = AskCollectionInput
    client: Any = Field(exclude=True)
    collection_id: str = Field(exclude=True)

    def model_post_init(self, __context: Any) -> None:
        self.description = (
            f"Ask a question across all documents in collection {self.collection_id}. "
            "Returns a cited answer. Costs 3 credits."
        )

    def _run(self, question: str) -> str:
        try:
            data = self.client.ask_collection(self.collection_id, question)
            return format_ask_collection_response(data, self.collection_id)
        except Exception as exc:
            return format_error(exc)


class AddToCollectionTool(BaseTool):
    name: str = "add_to_collection"
    description: str = "Add an evidence bundle to a DocImprint collection. Costs 2 credits."
    args_schema: type[BaseModel] = AddToCollectionInput
    client: Any = Field(exclude=True)
    collection_id: str = Field(exclude=True)

    def model_post_init(self, __context: Any) -> None:
        self.description = (
            f"Add an evidence bundle to collection {self.collection_id}. Costs 2 credits."
        )

    def _run(self, bundle_id: str) -> str:
        try:
            self.client.add_to_collection(self.collection_id, bundle_id)
            return format_add_to_collection_response(self.collection_id, bundle_id)
        except Exception as exc:
            return format_error(exc)


def make_collection_tools(client: DocImprintClient, collection_id: str) -> list[BaseTool]:
    return [
        SearchCollectionTool(client=client, collection_id=collection_id),
        AskCollectionTool(client=client, collection_id=collection_id),
        AddToCollectionTool(client=client, collection_id=collection_id),
    ]
