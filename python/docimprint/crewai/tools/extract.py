"""Evidence extraction and Q&A tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from docimprint.crewai.base import BaseTool
from docimprint.crewai.formatters import (
    format_error,
    format_extract_response,
    format_qa_response,
    format_summarize_response,
)

if TYPE_CHECKING:
    from docimprint.client import DocImprintClient


class UrlInput(BaseModel):
    url: str = Field(..., description="HTTPS URL of the page or document to process")


class QAInput(BaseModel):
    url: str = Field(..., description="HTTPS URL to read")
    question: str = Field(..., description="Question to answer against the source document")


class ExtractEvidenceTool(BaseTool):
    name: str = "extract_evidence"
    description: str = (
        "Extract a verifiable evidence bundle from a URL with cryptographic provenance. "
        "Costs 10 credits. Returns bundle_id, summary, and citations."
    )
    args_schema: type[BaseModel] = UrlInput
    client: object = Field(exclude=True)

    def _run(self, url: str) -> str:
        try:
            data = self.client.extract(url=url)  # type: ignore[attr-defined]
            return format_extract_response(data)
        except Exception as exc:
            return format_error(exc)


class SummarizeTool(BaseTool):
    name: str = "summarize_document"
    description: str = (
        "Summarize a URL with cited key points. Cheaper than full extraction. Costs 3 credits."
    )
    args_schema: type[BaseModel] = UrlInput
    client: object = Field(exclude=True)

    def _run(self, url: str) -> str:
        try:
            data = self.client.summarize(url)  # type: ignore[attr-defined]
            return format_summarize_response(data)
        except Exception as exc:
            return format_error(exc)


class QATool(BaseTool):
    name: str = "ask_document"
    description: str = (
        "Answer a question about a URL with cited evidence. Costs 3 credits."
    )
    args_schema: type[BaseModel] = QAInput
    client: object = Field(exclude=True)

    def _run(self, url: str, question: str) -> str:
        try:
            data = self.client.qa(url, question)  # type: ignore[attr-defined]
            return format_qa_response(data)
        except Exception as exc:
            return format_error(exc)


def make_extract_tools(client: DocImprintClient) -> list[BaseTool]:
    return [
        ExtractEvidenceTool(client=client),
        SummarizeTool(client=client),
        QATool(client=client),
    ]
