"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict, Field


def _install_crewai_stubs() -> None:
    if "crewai.knowledge.source.base_knowledge_source" in sys.modules:
        return

    class BaseKnowledgeStorage(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)

        def search(self, *args: Any, **kwargs: Any) -> list[Any]:
            raise NotImplementedError

        async def asearch(self, *args: Any, **kwargs: Any) -> list[Any]:
            raise NotImplementedError

        def save(self, documents: list[str]) -> None:
            raise NotImplementedError

        async def asave(self, documents: list[str]) -> None:
            raise NotImplementedError

        def reset(self) -> None:
            raise NotImplementedError

        async def areset(self) -> None:
            raise NotImplementedError

    class BaseKnowledgeSource(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)

        chunk_size: int = 4000
        chunk_overlap: int = 200
        chunks: list[str] = Field(default_factory=list)
        storage: BaseKnowledgeStorage | None = None
        metadata: dict[str, Any] = Field(default_factory=dict)
        collection_name: str | None = None

        def validate_content(self) -> Any:
            raise NotImplementedError

        def add(self) -> None:
            raise NotImplementedError

        async def aadd(self) -> None:
            raise NotImplementedError

    base_storage_mod = ModuleType("crewai.knowledge.storage.base_knowledge_storage")
    base_storage_mod.BaseKnowledgeStorage = BaseKnowledgeStorage

    base_source_mod = ModuleType("crewai.knowledge.source.base_knowledge_source")
    base_source_mod.BaseKnowledgeSource = BaseKnowledgeSource
    base_source_mod.BaseKnowledgeStorage = BaseKnowledgeStorage

    crewai_mod = ModuleType("crewai")
    knowledge_mod = ModuleType("crewai.knowledge")
    storage_mod = ModuleType("crewai.knowledge.storage")
    source_mod = ModuleType("crewai.knowledge.source")

    sys.modules["crewai"] = crewai_mod
    sys.modules["crewai.knowledge"] = knowledge_mod
    sys.modules["crewai.knowledge.storage"] = storage_mod
    sys.modules["crewai.knowledge.source"] = source_mod
    sys.modules["crewai.knowledge.storage.base_knowledge_storage"] = base_storage_mod
    sys.modules["crewai.knowledge.source.base_knowledge_source"] = base_source_mod


def pytest_configure() -> None:
    _install_crewai_stubs()


@pytest.fixture(autouse=True)
def reload_knowledge_module() -> None:
    for mod in list(sys.modules):
        if mod.startswith("docimprint.crewai.knowledge"):
            del sys.modules[mod]
