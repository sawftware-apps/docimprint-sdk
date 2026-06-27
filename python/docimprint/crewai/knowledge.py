"""CrewAI knowledge integration backed by DocImprint collections."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field, PrivateAttr, model_validator

from docimprint.client import DocImprintClient

if TYPE_CHECKING:
    from docimprint.crewai.toolkit import DocImprintToolkit

try:
    from crewai.knowledge.source.base_knowledge_source import BaseKnowledgeSource
    from crewai.knowledge.storage.base_knowledge_storage import BaseKnowledgeStorage

    _CREWAI_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when crewai not installed
    _CREWAI_AVAILABLE = False

    class BaseKnowledgeSource:  # type: ignore[no-redef]
        """Fallback stub when crewai is not installed."""

    class BaseKnowledgeStorage:  # type: ignore[no-redef]
        """Fallback stub when crewai is not installed."""


def format_search_hit(hit: dict[str, Any]) -> dict[str, Any]:
    """Format a collection search hit with bundle provenance metadata."""
    bundle_id = hit.get("bundle_id", "unknown")
    artifact = hit.get("artifact") or hit.get("title") or "text"
    text = hit.get("text") or hit.get("text_preview") or ""
    content = f"{text}\n[Source: bundle {bundle_id}, {artifact}]"
    return {
        "content": content,
        "score": float(hit.get("score", 0.0)),
        "metadata": {
            "bundle_id": bundle_id,
            "chunk_id": hit.get("chunk_id"),
            "artifact": artifact,
        },
    }


def format_search_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Format collection search API payload into knowledge chunks."""
    return [format_search_hit(hit) for hit in payload.get("results", [])]


class DocImprintKnowledgeStorage(BaseKnowledgeStorage):
    """Remote vector store backed by a DocImprint collection."""

    collection_id: str
    client: DocImprintClient
    score_threshold: float = 0.0

    def search(
        self,
        query: list[str],
        limit: int = 5,
        metadata_filter: dict[str, Any] | None = None,
        score_threshold: float = 0.6,
    ) -> list[dict[str, Any]]:
        del metadata_filter  # DocImprint search does not support arbitrary metadata filters yet.
        q = " ".join(query).strip()
        if not q:
            return []
        payload = self.client.search_collection(self.collection_id, q, limit=limit)
        hits = format_search_results(payload)
        threshold = score_threshold if score_threshold is not None else self.score_threshold
        return [hit for hit in hits if hit["score"] >= threshold]

    async def asearch(
        self,
        query: list[str],
        limit: int = 5,
        metadata_filter: dict[str, Any] | None = None,
        score_threshold: float = 0.6,
    ) -> list[dict[str, Any]]:
        return self.search(query, limit=limit, metadata_filter=metadata_filter, score_threshold=score_threshold)

    def save(self, documents: list[str]) -> None:
        del documents  # Indexing happens via DocImprint extract/add APIs.

    async def asave(self, documents: list[str]) -> None:
        self.save(documents)

    def reset(self) -> None:
        raise NotImplementedError("DocImprint collections cannot be reset from the SDK")

    async def areset(self) -> None:
        self.reset()


class DocImprintKnowledgeSource(BaseKnowledgeSource):
    """CrewAI knowledge source backed by a DocImprint collection."""

    collection_id: str
    toolkit: Any = Field(repr=False)
    ingest_urls: list[str] = Field(default_factory=list)
    wait_for_indexing: bool = True

    _client: DocImprintClient = PrivateAttr()

    @model_validator(mode="after")
    def _wire_storage(self) -> DocImprintKnowledgeSource:
        if not _CREWAI_AVAILABLE:
            raise ImportError(
                "docimprint[crewai] requires crewai>=0.80 on Python >=3.10,<3.14. "
                "Install a supported Python version and pip install 'docimprint[crewai]'."
            )
        client = getattr(self.toolkit, "client", None)
        if not isinstance(client, DocImprintClient):
            raise TypeError("toolkit must provide a DocImprintClient at toolkit.client")
        self._client = client
        if self.storage is None:
            self.storage = DocImprintKnowledgeStorage(
                collection_id=self.collection_id,
                client=client,
            )
        return self

    def validate_content(self) -> dict[str, str]:
        return {url: url for url in self.ingest_urls}

    def add(self) -> None:
        """Ingest configured URLs into the DocImprint collection."""
        for url in self.ingest_urls:
            self.add_url(url)

    async def aadd(self) -> None:
        self.add()

    def add_url(self, url: str) -> str:
        """Extract a URL into a bundle and index it into this collection."""
        bundle = self._client.extract(url=url, wait=self.wait_for_indexing)
        bundle_id = str(bundle["bundle_id"])
        index_result = self._client.add_to_collection(self.collection_id, bundle_id)
        if self.wait_for_indexing and index_result and index_result.get("job_id"):
            self._client.wait_for_job(str(index_result["job_id"]))
        return bundle_id

    def query(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        """Search the backing collection and return provenance-rich chunks."""
        payload = self._client.search_collection(self.collection_id, query, limit=limit)
        return format_search_results(payload)


def require_crewai() -> None:
    if not _CREWAI_AVAILABLE:
        raise ImportError(
            "docimprint[crewai] requires crewai>=0.80 on Python >=3.10,<3.14."
        )
