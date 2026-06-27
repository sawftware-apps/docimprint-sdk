"""Bundle verification and notarization tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from docimprint.crewai.base import BaseTool
from docimprint.crewai.formatters import format_error, format_notarize_response, format_verify_response

if TYPE_CHECKING:
    from docimprint.client import DocImprintClient


class BundleIdInput(BaseModel):
    bundle_id: str = Field(..., description="Evidence bundle ID (ev_...) to operate on")


class VerifyBundleTool(BaseTool):
    name: str = "verify_bundle"
    description: str = (
        "Verify cryptographic integrity of an evidence bundle (manifest hash, signature). "
        "Free (0 credits)."
    )
    args_schema: type[BaseModel] = BundleIdInput
    client: object = Field(exclude=True)

    def _run(self, bundle_id: str) -> str:
        try:
            data = self.client.verify(bundle_id)  # type: ignore[attr-defined]
            return format_verify_response(data, bundle_id)
        except Exception as exc:
            return format_error(exc)


class NotarizeTool(BaseTool):
    name: str = "notarize_bundle"
    description: str = (
        "Notarize an evidence bundle on-chain (Base/EAS attestation). Costs 7 credits."
    )
    args_schema: type[BaseModel] = BundleIdInput
    client: object = Field(exclude=True)

    def _run(self, bundle_id: str) -> str:
        try:
            data = self.client.notarize(bundle_id)  # type: ignore[attr-defined]
            return format_notarize_response(data, bundle_id)
        except Exception as exc:
            return format_error(exc)


def make_verify_tools(client: DocImprintClient) -> list[BaseTool]:
    return [
        VerifyBundleTool(client=client),
        NotarizeTool(client=client),
    ]
