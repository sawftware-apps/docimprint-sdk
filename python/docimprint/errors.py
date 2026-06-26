"""DocImprint API error types."""

from __future__ import annotations

from typing import Any


class DocImprintError(Exception):
    """Raised when the DocImprint API returns an error response."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str | None = None,
        request_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.request_id = request_id
        self.details = details

    def __str__(self) -> str:
        parts = [self.message]
        if self.status is not None:
            parts.append(f"status={self.status}")
        if self.code:
            parts.append(f"code={self.code}")
        if self.request_id:
            parts.append(f"request_id={self.request_id}")
        return " | ".join(parts)
