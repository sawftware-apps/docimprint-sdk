"""Claim checking and translation tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from docimprint.crewai.base import BaseTool
from docimprint.crewai.formatters import format_check_claims_response, format_error, format_translate_response

if TYPE_CHECKING:
    from docimprint.client import DocImprintClient


class CheckClaimsInput(BaseModel):
    url: str = Field(..., description="HTTPS URL to check claims against")
    claims: list[str] = Field(..., description="List of factual claims to verify (max 20)")


class TranslateInput(BaseModel):
    url: str = Field(..., description="HTTPS URL to translate")
    target_language: str = Field(..., description="ISO 639-1 language code (e.g. es, fr, de)")


class CheckClaimsTool(BaseTool):
    name: str = "check_claims"
    description: str = (
        "Verify factual claims against a source URL. Returns TRUE/FALSE/UNCERTAIN per claim "
        "with evidence. Costs 3 credits."
    )
    args_schema: type[BaseModel] = CheckClaimsInput
    client: object = Field(exclude=True)

    def _run(self, url: str, claims: list[str]) -> str:
        try:
            data = self.client.check_claims(url, claims)  # type: ignore[attr-defined]
            return format_check_claims_response(data)
        except Exception as exc:
            return format_error(exc)


class TranslateTool(BaseTool):
    name: str = "translate_document"
    description: str = (
        "Translate document content from a URL with source citations. Costs 5 credits."
    )
    args_schema: type[BaseModel] = TranslateInput
    client: object = Field(exclude=True)

    def _run(self, url: str, target_language: str) -> str:
        try:
            data = self.client.translate(url, target_language)  # type: ignore[attr-defined]
            return format_translate_response(data)
        except Exception as exc:
            return format_error(exc)


def make_claims_tools(client: DocImprintClient) -> list[BaseTool]:
    return [
        CheckClaimsTool(client=client),
        TranslateTool(client=client),
    ]
