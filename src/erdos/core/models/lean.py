"""Lean 4 compiler-related domain models."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - needed at runtime for Pydantic
from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from erdos.core.models.base import ErdosBaseModel, utc_now


class LeanError(ErdosBaseModel):
    """A single Lean compile error."""

    model_config = ConfigDict(frozen=True)

    file: Annotated[str, Field(description="Lean file path")]
    line: Annotated[int, Field(ge=1)]
    column: Annotated[int, Field(ge=1)]
    message: Annotated[str, Field(min_length=1)]
    severity: Annotated[Literal["error", "warning", "info"], Field(default="error")] = (
        "error"
    )

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.column}: {self.severity}: {self.message}"


class LeanCheckResult(ErdosBaseModel):
    """Result of running `lake build <module>` inside a Lean 4 project."""

    file: Annotated[str, Field(description="File that was checked")]
    success: Annotated[bool, Field(description="True if compilation succeeded")]
    errors: Annotated[list[LeanError], Field(default_factory=list)] = Field(
        default_factory=list
    )
    warnings: Annotated[list[LeanError], Field(default_factory=list)] = Field(
        default_factory=list
    )

    # Metadata
    lean_version: Annotated[str | None, Field(default=None)] = None
    duration_ms: Annotated[int | None, Field(default=None, ge=0)] = None
    checked_at: Annotated[datetime, Field(default_factory=utc_now)] = Field(
        default_factory=utc_now
    )

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def has_sorry(self) -> bool:
        """Check if any error mentions 'sorry' (incomplete proof)."""
        return any("sorry" in e.message.lower() for e in self.errors)
