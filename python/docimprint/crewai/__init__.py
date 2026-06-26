"""CrewAI integration for DocImprint."""

from docimprint.crewai.base import CREWAI_AVAILABLE
from docimprint.crewai.knowledge import (
    DocImprintKnowledgeSource,
    DocImprintKnowledgeStorage,
    format_search_hit,
    format_search_results,
)
from docimprint.crewai.toolkit import DocImprintToolkit
from docimprint.crewai.tracking import ProvenanceTracker, extract_bundle_ids
from docimprint.crewai.tools import (
    CheckClaimsTool,
    ExtractEvidenceTool,
    NotarizeTool,
    QATool,
    SummarizeTool,
    TranslateTool,
    VerifyBundleTool,
    make_collection_tools,
)

__all__ = [
    "CREWAI_AVAILABLE",
    "DocImprintKnowledgeSource",
    "DocImprintKnowledgeStorage",
    "DocImprintToolkit",
    "ProvenanceTracker",
    "extract_bundle_ids",
    "CheckClaimsTool",
    "ExtractEvidenceTool",
    "NotarizeTool",
    "QATool",
    "SummarizeTool",
    "TranslateTool",
    "VerifyBundleTool",
    "format_search_hit",
    "format_search_results",
    "make_collection_tools",
]
