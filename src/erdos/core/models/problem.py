"""Problem domain models."""

from __future__ import annotations

import re
from enum import Enum
from typing import Annotated

from pydantic import ConfigDict, Field

from erdos.core.models.base import ErdosBaseModel


class ProblemStatus(str, Enum):
    """Status of an Erdős problem."""

    OPEN = "open"
    PROVED = "proved"
    DISPROVED = "disproved"
    PARTIALLY_SOLVED = "partially_solved"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> ProblemStatus:
        """Parse status from various string formats."""
        normalized = value.lower().strip()
        normalized = re.sub(
            r"\s*\([^)]*\)\s*$", "", normalized
        )  # e.g., "proved (Lean)" -> "proved"
        normalized = normalized.replace("-", "_").replace(" ", "_")
        try:
            return cls(normalized)
        except ValueError:
            # Handle legacy/variant formats
            mapping = {
                "solved": cls.PROVED,
                "partial": cls.PARTIALLY_SOLVED,
                "open_problem": cls.OPEN,
            }
            return mapping.get(normalized, cls.UNKNOWN)


class ReferenceEntry(ErdosBaseModel):
    """
    A reference as embedded in a ProblemRecord.

    This is the minimal reference info from the upstream YAML.
    For enriched metadata, see ReferenceRecord.
    """

    model_config = ConfigDict(frozen=True)

    key: Annotated[
        str, Field(min_length=1, description="Reference key (e.g., 'Erdos1975')")
    ]
    citation: Annotated[
        str | None, Field(default=None, description="Full citation text")
    ] = None
    doi: Annotated[str | None, Field(default=None, pattern=r"^10\.\d{4,}/.*$")] = None
    arxiv_id: Annotated[
        str | None,
        Field(
            default=None,
            # Accept both post-2007 (YYMM.NNNN/NNNNN) and pre-2007 (archive/YYMMNNN) identifiers.
            pattern=r"^(?:\d{4}\.\d{4,5}|[A-Za-z\-]+(?:\.[A-Za-z\-]+)?/\d{7})(?:v\d+)?$",
        ),
    ] = None
    url: Annotated[str | None, Field(default=None)] = None


class ProblemRecord(ErdosBaseModel):
    """
    An Erdős problem from the dataset.

    This is the **enriched** internal representation used by the CLI.

    The upstream `teorth/erdosproblems` `data/problems.yaml` is metadata-only
    (no titles/statements). `ProblemRecord` is produced by combining upstream
    metadata with locally maintained enrichments and/or other sources.

    See Spec 005 for the upstream schema and enrichment strategy.
    """

    model_config = ConfigDict(
        frozen=True,  # Problems are immutable (come from upstream data)
        json_schema_extra={
            "examples": [
                {
                    "id": 6,
                    "title": "Small primes in arithmetic progressions",
                    "statement": "Let p_1 < p_2 < ... be the sequence of primes...",
                    "status": "proved",
                    "prize": 100,
                    "tags": ["number theory", "primes"],
                    "references": [
                        {"key": "Erdos1975", "citation": "P. Erdős (1975)..."}
                    ],
                }
            ]
        },
    )

    # Required fields
    id: Annotated[int, Field(ge=1, description="Problem ID (1-indexed)")]
    title: Annotated[str, Field(min_length=1, max_length=500)]
    statement: Annotated[str, Field(min_length=1, description="Problem statement text")]
    status: ProblemStatus

    # Optional fields with defaults
    prize: Annotated[int, Field(ge=0, default=0, description="Prize amount in USD")] = 0
    tags: Annotated[list[str], Field(default_factory=list)] = Field(
        default_factory=list
    )
    references: Annotated[list[ReferenceEntry], Field(default_factory=list)] = Field(
        default_factory=list
    )

    # Metadata
    oeis_ids: Annotated[
        list[str], Field(default_factory=list, description="Related OEIS sequence IDs")
    ] = Field(default_factory=list)
    notes: Annotated[
        str | None, Field(default=None, description="Additional notes")
    ] = None
    formalized: Annotated[
        bool, Field(default=False, description="Has Lean formalization")
    ] = False

    def __str__(self) -> str:
        """Human-readable representation."""
        prize_str = f" (${self.prize})" if self.prize > 0 else ""
        return f"Problem {self.id}: {self.title}{prize_str} [{self.status.value}]"


# Rebuild model to resolve forward references
ProblemRecord.model_rebuild()
