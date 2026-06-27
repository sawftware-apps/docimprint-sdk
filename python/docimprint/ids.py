"""Strict allowlist validators for DocImprint resource IDs."""

from __future__ import annotations

import re

from docimprint.errors import DocImprintError

_BUNDLE_ID_RE = re.compile(r"^ev_[a-zA-Z0-9][a-zA-Z0-9_-]*$")
_COLLECTION_ID_RE = re.compile(r"^col_[a-zA-Z0-9][a-zA-Z0-9_-]*$")
_JOB_ID_RE = re.compile(r"^job_[a-zA-Z0-9][a-zA-Z0-9_-]*$")


def validate_bundle_id(value: str) -> str:
    """Return bundle_id if it matches the ev_… allowlist."""
    if not _BUNDLE_ID_RE.fullmatch(value):
        raise DocImprintError(f"Invalid bundle_id: {value!r}", code="INVALID_ID")
    return value


def validate_collection_id(value: str) -> str:
    """Return collection_id if it matches the col_… allowlist."""
    if not _COLLECTION_ID_RE.fullmatch(value):
        raise DocImprintError(f"Invalid collection_id: {value!r}", code="INVALID_ID")
    return value


def validate_job_id(value: str) -> str:
    """Return job_id if it matches the job_… allowlist."""
    if not _JOB_ID_RE.fullmatch(value):
        raise DocImprintError(f"Invalid job_id: {value!r}", code="INVALID_ID")
    return value
