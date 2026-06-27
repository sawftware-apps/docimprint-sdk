"""CrewAI BaseTool shim — uses real crewai when installed, else a compatible fallback."""

from __future__ import annotations

from typing import Any

try:
    from crewai.tools import BaseTool as _CrewAIBaseTool

    BaseTool = _CrewAIBaseTool
    CREWAI_AVAILABLE = True
except ImportError:
    from pydantic import BaseModel

    class BaseTool(BaseModel):  # type: ignore[no-redef]
        """Minimal BaseTool-compatible class for testing without crewai installed."""

        name: str
        description: str
        args_schema: type[BaseModel] | None = None

        model_config = {"arbitrary_types_allowed": True}

        def _run(self, *args: Any, **kwargs: Any) -> str:
            raise NotImplementedError

        def run(self, *args: Any, **kwargs: Any) -> str:
            return self._run(*args, **kwargs)

    CREWAI_AVAILABLE = False

__all__ = ["BaseTool", "CREWAI_AVAILABLE"]
