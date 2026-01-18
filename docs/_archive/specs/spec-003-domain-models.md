# Spec 003: Core Domain Models

> Defines the Pydantic models that represent the core domain entities. These are the foundation all other code builds upon.

---

## Overview

Domain models define the data structures that flow through the system. They are:
- **Validated** - Invalid data is rejected at the boundary
- **Typed** - Full type hints for IDE support and mypy
- **Serializable** - Clean JSON output for CLI `--json` mode
- **Immutable where possible** - Reduce bugs from accidental mutation

### Guiding Principles

1. **Parse, don't validate** - Use Pydantic to transform and validate in one step
2. **Fail fast** - Reject invalid data at system boundaries, not deep in business logic
3. **Single source of truth** - One model definition, used everywhere
4. **Schema versioning** - Support evolution of data formats

---

## 1) Model Hierarchy

```
erdos.core.models
├── ProblemRecord       # Core entity: an Erdős problem
├── ReferenceRecord     # A literature reference
├── ManifestEntry       # Extended reference with local state
├── TextChunk           # A searchable piece of text
├── LeanCheckResult     # Result of compiling Lean code
├── LeanError           # A single Lean compile error
└── CLIOutput           # Wrapper for JSON CLI responses
```

---

## 2) Base Configuration

All models share common Pydantic configuration:

```python
# src/erdos/core/models.py
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
        strict=True,              # Strict type coercion
        validate_assignment=True, # Validate on attribute assignment
        validate_default=True,    # Validate default values

        # Serialization
        ser_json_bytes="base64",  # How to serialize bytes
        ser_json_timedelta="float", # Timedelta as seconds

        # Immutability (where desired)
        frozen=False,             # Subclasses can override

        # Extra fields
        extra="forbid",           # Reject unknown fields

        # JSON schema
        json_schema_extra={
            "examples": []        # Subclasses add examples
        },
    )
```

---

## 3) Problem Status Enum

```python
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
        import re

        normalized = value.lower().strip()
        normalized = re.sub(r"\\s*\\([^)]*\\)\\s*$", "", normalized)  # e.g., "proved (Lean)" -> "proved"
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
```

---

## 4) ProblemRecord

The core entity representing an Erdős problem.

```python
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
                    "references": [{"key": "Erdos1975", "citation": "P. Erdős (1975)..."}],
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
    prize: Annotated[int, Field(ge=0, default=0, description="Prize amount in USD")]
    tags: Annotated[list[str], Field(default_factory=list)]
    references: Annotated[list["ReferenceEntry"], Field(default_factory=list)]

    # Metadata
    oeis_ids: Annotated[list[str], Field(default_factory=list, description="Related OEIS sequence IDs")]
    notes: Annotated[str | None, Field(default=None, description="Additional notes")]
    formalized: Annotated[bool, Field(default=False, description="Has Lean formalization")]

    def __str__(self) -> str:
        """Human-readable representation."""
        prize_str = f" (${self.prize})" if self.prize > 0 else ""
        return f"Problem {self.id}: {self.title}{prize_str} [{self.status.value}]"


class ReferenceEntry(ErdosBaseModel):
    """
    A reference as embedded in a ProblemRecord.

    This is the minimal reference info from the upstream YAML.
    For enriched metadata, see ReferenceRecord.
    """

    model_config = ConfigDict(frozen=True)

    key: Annotated[str, Field(min_length=1, description="Reference key (e.g., 'Erdos1975')")]
    citation: Annotated[str | None, Field(default=None, description="Full citation text")]
    doi: Annotated[str | None, Field(default=None, pattern=r"^10\.\d{4,}/.*$")]
    arxiv_id: Annotated[
        str | None,
        Field(
            default=None,
            # Accept both post-2007 (YYMM.NNNN/NNNNN) and pre-2007 (archive/YYMMNNN) identifiers.
            pattern=r"^(?:\d{4}\.\d{4,5}|[A-Za-z\\-]+(?:\\.[A-Za-z\\-]+)?/\\d{7})(?:v\\d+)?$",
        ),
    ]
    url: Annotated[str | None, Field(default=None)]
```

---

## 5) ReferenceRecord

Enriched reference with metadata from external APIs.

```python
class OpenAccessStatus(str, Enum):
    """Open access status from Unpaywall or similar."""

    GOLD = "gold"           # Published OA
    GREEN = "green"         # Repository/preprint
    BRONZE = "bronze"       # Free to read but not formally OA
    HYBRID = "hybrid"       # OA in subscription journal
    CLOSED = "closed"       # Paywalled
    UNKNOWN = "unknown"


class ReferenceRecord(ErdosBaseModel):
    """
    A fully enriched literature reference.

    Created by ingesting metadata from Crossref, arXiv, etc.
    """

    # Identifiers (at least one required)
    doi: Annotated[str | None, Field(default=None, pattern=r"^10\.\d{4,}/.*$")]
    arxiv_id: Annotated[str | None, Field(default=None)]
    semantic_scholar_id: Annotated[str | None, Field(default=None)]

    # Bibliographic metadata
    title: Annotated[str, Field(min_length=1)]
    authors: Annotated[list[str], Field(default_factory=list)]
    year: Annotated[int | None, Field(default=None, ge=1900, le=2100)]
    venue: Annotated[str | None, Field(default=None, description="Journal or conference")]
    abstract: Annotated[str | None, Field(default=None)]

    # Access information
    oa_status: Annotated[OpenAccessStatus, Field(default=OpenAccessStatus.UNKNOWN)]
    oa_url: Annotated[str | None, Field(default=None, description="Open access URL")]
    license: Annotated[str | None, Field(default=None, description="Content license (e.g., CC-BY)")]

    # Local state (not from upstream)
    fetched_at: Annotated[datetime | None, Field(default=None)]
    source: Annotated[str | None, Field(default=None, description="API that provided this data")]

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
```

---

## 6) ManifestEntry

Reference with local cache state, stored in `literature/manifests/`.

```python
class ManifestEntry(ErdosBaseModel):
    """
    A reference with local cache state.

    Stored in literature/manifests/<problem_id>.yaml
    """

    # Schema version for migration support
    schema_version: Annotated[int, Field(default=1, ge=1)]

    # The reference data
    reference: ReferenceRecord

    # Local cache state
    cached: Annotated[bool, Field(default=False)]
    cache_path: Annotated[Path | None, Field(default=None)]
    cache_hash: Annotated[str | None, Field(default=None, description="MD5 of cached content")]

    # Extraction state
    extracted: Annotated[bool, Field(default=False)]
    extract_path: Annotated[Path | None, Field(default=None)]

    # Processing metadata
    ingested_at: Annotated[datetime | None, Field(default=None)]
    error: Annotated[str | None, Field(default=None, description="Error if ingestion failed")]


class ProblemManifest(ErdosBaseModel):
    """
    Manifest file for a problem's references.

    Stored at literature/manifests/<problem_id>.yaml
    """

    schema_version: Annotated[int, Field(default=1)]
    problem_id: Annotated[int, Field(ge=1)]
    entries: Annotated[list[ManifestEntry], Field(default_factory=list)]
    created_at: Annotated[datetime, Field(default_factory=utc_now)]
    updated_at: Annotated[datetime, Field(default_factory=utc_now)]
```

---

## 7) TextChunk

Searchable text segment for the retrieval index.

```python
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
            preview=problem.statement[:200] if len(problem.statement) > 200 else problem.statement,
        )
```

---

## 8) Lean-Related Models

```python
class LeanError(ErdosBaseModel):
    """A single Lean compile error."""

    model_config = ConfigDict(frozen=True)

    file: Annotated[str, Field(description="Lean file path")]
    line: Annotated[int, Field(ge=1)]
    column: Annotated[int, Field(ge=1)]
    message: Annotated[str, Field(min_length=1)]
    severity: Annotated[Literal["error", "warning", "info"], Field(default="error")] = "error"

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.column}: {self.severity}: {self.message}"


class LeanCheckResult(ErdosBaseModel):
    """Result of running `lake build <module>` inside a Lean 4 project."""

    file: Annotated[str, Field(description="File that was checked")]
    success: Annotated[bool, Field(description="True if compilation succeeded")]
    errors: Annotated[list[LeanError], Field(default_factory=list)]
    warnings: Annotated[list[LeanError], Field(default_factory=list)]

    # Metadata
    lean_version: Annotated[str | None, Field(default=None)]
    duration_ms: Annotated[int | None, Field(default=None, ge=0)]
    checked_at: Annotated[datetime, Field(default_factory=utc_now)]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def has_sorry(self) -> bool:
        """Check if any error mentions 'sorry' (incomplete proof)."""
        return any("sorry" in e.message.lower() for e in self.errors)
```

---

## 9) CLI Output Wrapper

Standard wrapper for JSON CLI output.

```python
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
    timestamp: Annotated[datetime, Field(default_factory=utc_now)]
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


# Example usage:
# CLIOutput.ok("erdos show", problem.model_dump())
# CLIOutput.err("erdos show", "NotFound", "Problem 9999 not found", code=3)
```

---

## 10) Model Relationships Diagram

```
                                    ┌─────────────────┐
                                    │   CLIOutput     │
                                    │  (wrapper for   │
                                    │   all --json)   │
                                    └────────┬────────┘
                                             │ wraps
                ┌────────────────────────────┼────────────────────────────┐
                │                            │                            │
                ▼                            ▼                            ▼
        ┌───────────────┐          ┌─────────────────┐          ┌─────────────────┐
        │ ProblemRecord │          │ LeanCheckResult │          │  SearchResult   │
        │               │          │                 │          │   (future)      │
        └───────┬───────┘          └────────┬────────┘          └─────────────────┘
                │                           │
                │ contains                  │ contains
                ▼                           ▼
        ┌───────────────┐          ┌─────────────────┐
        │ReferenceEntry │          │    LeanError    │
        │  (minimal)    │          │                 │
        └───────────────┘          └─────────────────┘
                │
                │ enriched to
                ▼
        ┌───────────────┐
        │ReferenceRecord│
        │  (full meta)  │
        └───────┬───────┘
                │
                │ wrapped in
                ▼
        ┌───────────────┐
        │ ManifestEntry │
        │ (with cache   │
        │  state)       │
        └───────┬───────┘
                │
                │ many in
                ▼
        ┌───────────────┐
        │ProblemManifest│
        │ (YAML file)   │
        └───────────────┘
```

---

## 11) Validation Examples

```python
# Valid problem
problem = ProblemRecord(
    id=6,
    title="Small primes",
    statement="Prove that...",
    status=ProblemStatus.PROVED,
    prize=100,
    tags=["primes"],
)

# Invalid: negative ID
try:
    ProblemRecord(id=-1, ...)  # Raises ValidationError
except ValidationError as e:
    print(e)  # "id: Input should be greater than or equal to 1"

# Invalid: empty title
try:
    ProblemRecord(id=1, title="", ...)  # Raises ValidationError
except ValidationError as e:
    print(e)  # "title: String should have at least 1 character"

# Invalid: unknown status
try:
    ProblemRecord(id=1, status="maybe", ...)  # Raises ValidationError
except ValidationError as e:
    print(e)  # "status: Input should be 'open', 'proved', ..."

# DOI format validation
ref = ReferenceRecord(
    doi="10.1007/BF01940595",  # Valid
    title="Test",
)

try:
    ReferenceRecord(doi="invalid-doi", title="Test")  # Raises ValidationError
except ValidationError as e:
    print(e)  # "doi: String should match pattern '^10\.\d{4,}/.*$'"
```

---

## 12) Serialization Examples

```python
# To JSON dict (enums become strings)
problem_dict = problem.model_dump(mode="json")
# {
#     "id": 6,
#     "title": "Small primes",
#     "statement": "Prove that...",
#     "status": "proved",
#     "prize": 100,
#     "tags": ["primes"],
#     ...
# }

# To JSON string
problem_json = problem.model_dump_json(indent=2)

# From dict
# Note: with strict models (Spec 003), json-mode dumps must be re-validated with strict=False.
restored = ProblemRecord.model_validate(problem_dict, strict=False)

# From JSON string
restored = ProblemRecord.model_validate_json(problem_json)

# Partial update (if not frozen)
updated = problem.model_copy(update={"prize": 200})
```

---

## 13) Verification: This Spec is Testable

### Unit Tests

```python
# tests/unit/test_models.py
"""Tests for domain models."""

import pytest
from pydantic import ValidationError

from erdos.core.models import (
    ProblemRecord,
    ProblemStatus,
    ReferenceRecord,
    LeanError,
    LeanCheckResult,
    CLIOutput,
)


class TestProblemStatus:
    def test_from_string_standard(self) -> None:
        assert ProblemStatus.from_string("open") == ProblemStatus.OPEN
        assert ProblemStatus.from_string("proved") == ProblemStatus.PROVED

    def test_from_string_variants(self) -> None:
        assert ProblemStatus.from_string("solved") == ProblemStatus.PROVED
        assert ProblemStatus.from_string("proved (Lean)") == ProblemStatus.PROVED
        assert ProblemStatus.from_string("OPEN") == ProblemStatus.OPEN

    def test_from_string_unknown(self) -> None:
        assert ProblemStatus.from_string("gibberish") == ProblemStatus.UNKNOWN


class TestProblemRecord:
    def test_valid_problem(self) -> None:
        problem = ProblemRecord(
            id=1,
            title="Test",
            statement="Prove X",
            status=ProblemStatus.OPEN,
        )
        assert problem.id == 1
        assert problem.prize == 0  # default

    def test_invalid_id_rejected(self) -> None:
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            ProblemRecord(id=0, title="Test", statement="X", status=ProblemStatus.OPEN)

    def test_roundtrip_json(self) -> None:
        problem = ProblemRecord(
            id=42,
            title="Test Problem",
            statement="Prove that 1+1=2",
            status=ProblemStatus.PROVED,
            tags=["math"],
        )
        json_str = problem.model_dump_json()
        restored = ProblemRecord.model_validate_json(json_str)
        assert restored == problem

    def test_str_representation(self) -> None:
        problem = ProblemRecord(
            id=6,
            title="Small primes",
            statement="...",
            status=ProblemStatus.PROVED,
            prize=100,
        )
        assert str(problem) == "Problem 6: Small primes ($100) [proved]"


class TestReferenceRecord:
    def test_valid_doi(self) -> None:
        ref = ReferenceRecord(doi="10.1007/BF01940595", title="Test")
        assert ref.doi == "10.1007/BF01940595"

    def test_invalid_doi_rejected(self) -> None:
        with pytest.raises(ValidationError, match="String should match pattern"):
            ReferenceRecord(doi="not-a-doi", title="Test")

    def test_best_url_priority(self) -> None:
        ref = ReferenceRecord(
            doi="10.1234/test",
            arxiv_id="2203.00001",
            oa_url="https://example.com/paper.pdf",
            title="Test",
        )
        assert ref.best_url == "https://example.com/paper.pdf"

        ref2 = ReferenceRecord(arxiv_id="2203.00001", title="Test")
        assert ref2.best_url == "https://arxiv.org/abs/2203.00001"


class TestLeanCheckResult:
    def test_success_result(self) -> None:
        result = LeanCheckResult(file="Test.lean", success=True)
        assert result.success
        assert result.error_count == 0

    def test_error_result(self) -> None:
        result = LeanCheckResult(
            file="Test.lean",
            success=False,
            errors=[
                LeanError(file="Test.lean", line=10, column=5, message="type mismatch")
            ],
        )
        assert not result.success
        assert result.error_count == 1

    def test_has_sorry_detection(self) -> None:
        result = LeanCheckResult(
            file="Test.lean",
            success=False,
            errors=[
                LeanError(file="Test.lean", line=10, column=5, message="declaration uses 'sorry'")
            ],
        )
        assert result.has_sorry


class TestCLIOutput:
    def test_ok_output(self) -> None:
        output = CLIOutput.ok("erdos show", {"id": 1})
        assert output.success
        assert output.data == {"id": 1}
        assert output.error is None

    def test_error_output(self) -> None:
        output = CLIOutput.err("erdos show", "NotFound", "Problem not found", code=3)
        assert not output.success
        assert output.error is not None
        assert output.error["type"] == "NotFound"
        assert output.error["code"] == 3
```

### Property-Based Tests

```python
# tests/unit/test_models_hypothesis.py
from hypothesis import given, strategies as st

from erdos.core.models import ProblemRecord, ProblemStatus


@given(
    id=st.integers(min_value=1, max_value=10000),
    title=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
    prize=st.integers(min_value=0, max_value=1_000_000),
)
def test_problem_record_roundtrips(id: int, title: str, prize: int) -> None:
    """Any valid ProblemRecord should roundtrip through JSON."""
    problem = ProblemRecord(
        id=id,
        title=title,
        statement="Test statement",
        status=ProblemStatus.OPEN,
        prize=prize,
    )
    json_str = problem.model_dump_json()
    restored = ProblemRecord.model_validate_json(json_str)
    assert restored == problem
```

---

## 14) References

- [Pydantic Documentation](https://docs.pydantic.dev/latest/)
- [Pydantic Field Types](https://docs.pydantic.dev/latest/concepts/fields/)
- [Pydantic JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-16 | Initial spec |
