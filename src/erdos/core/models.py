"""Core domain models for erdos-banger."""

import re
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def utc_now() -> datetime:
    """Timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class ErdosBaseModel(BaseModel):
    """Base model with shared configuration."""

    model_config = ConfigDict(
        # Validation
        strict=True,  # Strict type coercion
        validate_assignment=True,  # Validate on attribute assignment
        validate_default=True,  # Validate default values
        # Serialization
        ser_json_bytes="base64",  # How to serialize bytes
        ser_json_timedelta="float",  # Timedelta as seconds
        # Immutability (where desired)
        frozen=False,  # Subclasses can override
        # Extra fields
        extra="forbid",  # Reject unknown fields
        # JSON schema
        json_schema_extra={
            "examples": []  # Subclasses add examples
        },
    )


class ProblemStatus(str, Enum):
    """Status of an Erdős problem."""

    OPEN = "open"
    PROVED = "proved"
    DISPROVED = "disproved"
    PARTIALLY_SOLVED = "partially_solved"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> "ProblemStatus":
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
    references: Annotated[list["ReferenceEntry"], Field(default_factory=list)] = Field(
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


class OpenAccessStatus(str, Enum):
    """Open access status from Unpaywall or similar."""

    GOLD = "gold"  # Published OA
    GREEN = "green"  # Repository/preprint
    BRONZE = "bronze"  # Free to read but not formally OA
    HYBRID = "hybrid"  # OA in subscription journal
    CLOSED = "closed"  # Paywalled
    UNKNOWN = "unknown"


class ReferenceRecord(ErdosBaseModel):
    """
    A fully enriched literature reference.

    Created by ingesting metadata from Crossref, arXiv, etc.
    """

    # Identifiers (at least one required)
    doi: Annotated[str | None, Field(default=None, pattern=r"^10\.\d{4,}/.*$")] = None
    arxiv_id: Annotated[
        str | None,
        Field(
            default=None,
            # Accept both post-2007 (YYMM.NNNN/NNNNN) and pre-2007 (archive/YYMMNNN) identifiers.
            # Defense-in-depth: prevents path traversal attacks when used in file paths.
            pattern=r"^(?:\d{4}\.\d{4,5}|[A-Za-z\-]+(?:\.[A-Za-z\-]+)?/\d{7})(?:v\d+)?$",
        ),
    ] = None
    semantic_scholar_id: Annotated[str | None, Field(default=None)] = None

    # Bibliographic metadata
    title: Annotated[str, Field(min_length=1)]
    authors: Annotated[list[str], Field(default_factory=list)] = Field(
        default_factory=list
    )
    year: Annotated[int | None, Field(default=None, ge=1900, le=2100)] = None
    venue: Annotated[
        str | None, Field(default=None, description="Journal or conference")
    ] = None
    abstract: Annotated[str | None, Field(default=None)] = None

    # Access information
    oa_status: Annotated[OpenAccessStatus, Field(default=OpenAccessStatus.UNKNOWN)] = (
        OpenAccessStatus.UNKNOWN
    )
    oa_url: Annotated[
        str | None, Field(default=None, description="Open access URL")
    ] = None
    license: Annotated[
        str | None, Field(default=None, description="Content license (e.g., CC-BY)")
    ] = None

    # Local state (not from upstream)
    fetched_at: Annotated[datetime | None, Field(default=None)] = None
    source: Annotated[
        str | None, Field(default=None, description="API that provided this data")
    ] = None

    @property
    def has_identifier(self) -> bool:
        """Check if reference has at least one identifier."""
        return bool(self.doi or self.arxiv_id or self.semantic_scholar_id)

    @model_validator(mode="after")
    def _require_identifier(self) -> "ReferenceRecord":
        """Enforce that at least one identifier is present."""
        if not (self.doi or self.arxiv_id or self.semantic_scholar_id):
            raise ValueError(
                "ReferenceRecord requires at least one identifier: doi, arxiv_id, or semantic_scholar_id"
            )
        return self

    @property
    def best_url(self) -> str | None:
        """Return the best available URL for accessing this reference."""
        if self.oa_url:
            return self.oa_url
        if self.arxiv_id:
            return f"https://arxiv.org/abs/{self.arxiv_id}"
        if self.doi:
            return f"https://doi.org/{self.doi}"
        return None


class ManifestEntry(ErdosBaseModel):
    """
    A reference with local cache state.

    Stored in literature/manifests/<problem_id>.yaml
    """

    # Schema version for migration support
    schema_version: Annotated[int, Field(default=1, ge=1)] = 1

    # The reference data
    reference: ReferenceRecord

    # Local cache state
    cached: Annotated[bool, Field(default=False)] = False
    cache_path: Annotated[Path | None, Field(default=None)] = None
    cache_hash: Annotated[
        str | None, Field(default=None, description="MD5 of cached content")
    ] = None

    # Extraction state
    extracted: Annotated[bool, Field(default=False)] = False
    extract_path: Annotated[Path | None, Field(default=None)] = None

    # Processing metadata
    ingested_at: Annotated[datetime | None, Field(default=None)] = None
    error: Annotated[
        str | None, Field(default=None, description="Error if ingestion failed")
    ] = None


class ProblemManifest(ErdosBaseModel):
    """
    Manifest file for a problem's references.

    Stored at literature/manifests/<problem_id>.yaml
    """

    schema_version: Annotated[int, Field(default=1)] = 1
    problem_id: Annotated[int, Field(ge=1)]
    entries: Annotated[list[ManifestEntry], Field(default_factory=list)] = Field(
        default_factory=list
    )
    created_at: Annotated[datetime, Field(default_factory=utc_now)] = Field(
        default_factory=utc_now
    )
    updated_at: Annotated[datetime, Field(default_factory=utc_now)] = Field(
        default_factory=utc_now
    )


class ChunkSource(str, Enum):
    """Where a text chunk came from."""

    PROBLEM_STATEMENT = "problem_statement"
    PROBLEM_NOTES = "problem_notes"
    REFERENCE_ABSTRACT = "reference_abstract"
    REFERENCE_FULLTEXT = "reference_fulltext"


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
    def _validate_char_span(self) -> "TextChunk":
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
    def from_problem(cls, problem: ProblemRecord) -> "TextChunk":
        """Create a chunk from a problem statement."""
        return cls(
            id=f"problem_{problem.id}_statement",
            text=problem.statement,
            source=ChunkSource.PROBLEM_STATEMENT,
            problem_id=problem.id,
            preview=problem.statement[:200]
            if len(problem.statement) > 200
            else problem.statement,
        )


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


class CLIOutput(ErdosBaseModel):
    """
    Standard wrapper for CLI JSON output.

    All --json output uses this structure for consistency.
    """

    schema_version: Annotated[int, Field(default=1)] = 1
    command: Annotated[str, Field(description="Command that produced this output")]
    success: Annotated[bool, Field(default=True)] = True
    data: Annotated[Any, Field(description="Command-specific output data")]
    error: Annotated[dict[str, Any] | None, Field(default=None)] = None

    # Metadata
    timestamp: Annotated[datetime, Field(default_factory=utc_now)] = Field(
        default_factory=utc_now
    )
    duration_ms: Annotated[int | None, Field(default=None)] = None

    @model_validator(mode="after")
    def _check_invariants(self) -> "CLIOutput":
        """Ensure success/data/error consistency."""
        if self.success:
            if self.error is not None:
                raise ValueError("CLIOutput: success=True but error is set")
            return self

        # Failure case
        if self.error is None:
            raise ValueError("CLIOutput: success=False but error is None")
        if self.data is not None:
            raise ValueError("CLIOutput: success=False but data is not None")

        required_keys = {"type", "message", "code"}
        missing = required_keys.difference(self.error.keys())
        if missing:
            raise ValueError(f"CLIOutput: error missing keys: {sorted(missing)}")

        if not isinstance(self.error.get("type"), str) or not self.error["type"]:
            raise ValueError("CLIOutput: error.type must be a non-empty string")
        if not isinstance(self.error.get("message"), str) or not self.error["message"]:
            raise ValueError("CLIOutput: error.message must be a non-empty string")
        if not isinstance(self.error.get("code"), int):
            raise ValueError("CLIOutput: error.code must be an int")
        return self

    @classmethod
    def ok(cls, command: str, data: Any, duration_ms: int | None = None) -> "CLIOutput":
        """Create a successful output."""
        return cls(command=command, success=True, data=data, duration_ms=duration_ms)

    @classmethod
    def err(
        cls,
        command: str,
        error_type: str,
        message: str,
        code: int = 1,
    ) -> "CLIOutput":
        """Create an error output."""
        return cls(
            command=command,
            success=False,
            data=None,
            error={"type": error_type, "message": message, "code": code},
        )


ProblemRecord.model_rebuild()
