"""Research domain errors."""

from __future__ import annotations


class ResearchError(Exception):
    """Base error for research operations."""


class ResearchNotInitializedError(ResearchError):
    """Raised when a workspace is required but missing."""


class ResearchRecordNotFoundError(ResearchError):
    """Raised when a specific record file is missing."""


class ResearchRecordInvalidError(ResearchError):
    """Raised when a record fails schema validation or invariants."""
