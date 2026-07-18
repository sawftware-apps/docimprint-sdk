"""Pydantic models for DocImprint API request/response shapes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocImprintModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class Citation(DocImprintModel):
    quote: str | None = None
    page: int | None = None
    section: str | None = None
    paragraphs: list[int] | None = None


class ClaimResult(DocImprintModel):
    claim: str
    status: str
    evidence: dict[str, Any] | None = None
    confidence: str | None = None


class Provenance(DocImprintModel):
    manifest_sha256: str | None = None
    signature: dict[str, Any] | None = None


class ExtractResponse(DocImprintModel):
    bundle_id: str | None = None
    status: str | None = None
    store: bool | None = None
    mode: str | None = None
    result: dict[str, Any] | None = None
    provenance: Provenance | None = None
    artifacts: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    job_id: str | None = None


class SummarizeResponse(DocImprintModel):
    bundle_id: str | None = None
    result: dict[str, Any] | None = None
    job_id: str | None = None


class QAResponse(DocImprintModel):
    bundle_id: str | None = None
    result: dict[str, Any] | None = None
    job_id: str | None = None


class CheckClaimsResponse(DocImprintModel):
    bundle_id: str | None = None
    result: dict[str, Any] | None = None
    claims: list[ClaimResult] | None = None
    job_id: str | None = None


class TranslateResponse(DocImprintModel):
    bundle_id: str | None = None
    result: dict[str, Any] | None = None
    job_id: str | None = None


class VerifyResponse(DocImprintModel):
    valid: bool
    manifest_sha256: str | None = None
    checks: dict[str, Any] | None = None


class NotarizeResponse(DocImprintModel):
    attestation: dict[str, Any] | None = None


class Collection(DocImprintModel):
    id: str
    name: str | None = None


class SearchResult(DocImprintModel):
    text: str | None = None
    bundle_id: str | None = None
    score: float | None = None
    artifact: str | None = None


class SearchCollectionResponse(DocImprintModel):
    results: list[SearchResult] = Field(default_factory=list)


class AskCollectionResponse(DocImprintModel):
    answer: str | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    bundle_id: str | None = None


class JobResponse(DocImprintModel):
    id: str | None = None
    job_id: str | None = None
    status: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


class QuotaResponse(DocImprintModel):
    credits_remaining: int | None = None
    credits_used: int | None = None
    plan: str | None = None


class ActionReceipt(DocImprintModel):
    receipt_id: str | None = None
    bundle_id: str | None = None
    agent_id: str | None = None
    action: str | None = None
    manifest_sha256: str | None = None
    signed_at: str | None = None
    signature: str | None = None
    signer_address: str | None = None
    key_id: str | None = None
    algorithm: str | None = None


class ListReceiptsResponse(DocImprintModel):
    bundle_id: str | None = None
    receipts: list[ActionReceipt] = Field(default_factory=list)
    limit: int | None = None
    offset: int | None = None


class VerifyReceiptResponse(DocImprintModel):
    receipt_id: str | None = None
    valid: bool
    signature_valid: bool | None = None
    manifest_matches_current: bool | None = None
    bundle_id: str | None = None
    agent_id: str | None = None
    action: str | None = None
    manifest_sha256: str | None = None
    signer_address: str | None = None
    signed_at: str | None = None
    tampered: list[str] = Field(default_factory=list)
