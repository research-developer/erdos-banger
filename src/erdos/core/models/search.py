"""Search-related domain models."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Annotated

from pydantic import Field, model_validator

from erdos.core.constants import PREVIEW_LENGTH
from erdos.core.models.base import ErdosBaseModel


if TYPE_CHECKING:
    from erdos.core.models.problem import ProblemRecord


class ChunkSource(str, Enum):
    """Where a text chunk came from."""

    PROBLEM_STATEMENT = "problem_statement"
    PROBLEM_NOTES = "problem_notes"
    REFERENCE_ABSTRACT = "reference_abstract"
    REFERENCE_FULLTEXT = "reference_fulltext"
    RESEARCH_SYNTHESIS = "research_synthesis"
    RESEARCH_LEAD = "research_lead"
    RESEARCH_ATTEMPT = "research_attempt"
    RESEARCH_HYPOTHESIS = "research_hypothesis"
    RESEARCH_TASK = "research_task"


class TextChunk(ErdosBaseModel):
    """
    A chunk of text for the search index.

    Chunks are created by splitting problem statements and
    reference texts into searchable segments.
    """

    id: Annotated[str, Field(description="Unique chunk ID")]
    text: Annotated[str, Field(min_length=1)]
    source: ChunkSource

    # Source linkage
    problem_id: Annotated[int | None, Field(default=None)] = None
    reference_doi: Annotated[str | None, Field(default=None)] = None

    # Position in source document
    start_char: Annotated[int | None, Field(default=None, ge=0)] = None
    end_char: Annotated[int | None, Field(default=None, ge=0)] = None

    # For display
    preview: Annotated[str | None, Field(default=None, max_length=200)] = None

    @model_validator(mode="after")
    def _validate_char_span(self) -> TextChunk:
        """Ensure start_char and end_char are paired and ordered."""
        if (self.start_char is None) != (self.end_char is None):
            raise ValueError(
                "TextChunk: start_char and end_char must both be set or both be None"
            )
        if (
            self.start_char is not None
            and self.end_char is not None
            and self.start_char > self.end_char
        ):
            raise ValueError(
                f"TextChunk: start_char ({self.start_char}) must be <= end_char ({self.end_char})"
            )
        return self

    @classmethod
    def from_problem(cls, problem: ProblemRecord) -> TextChunk:
        """Create a chunk from a problem statement."""
        return cls(
            id=f"problem_{problem.id}_statement",
            text=problem.statement,
            source=ChunkSource.PROBLEM_STATEMENT,
            problem_id=problem.id,
            preview=problem.statement[:PREVIEW_LENGTH]
            if len(problem.statement) > PREVIEW_LENGTH
            else problem.statement,
        )
