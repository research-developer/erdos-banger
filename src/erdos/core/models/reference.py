"""Reference and manifest domain models."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - needed at runtime for Pydantic
from enum import Enum
from pathlib import Path  # noqa: TC003 - needed at runtime for Pydantic
from typing import Annotated

from pydantic import Field, model_validator

from erdos.core.models.base import ErdosBaseModel, utc_now


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

    @model_validator(mode="after")
    def _require_identifier(self) -> ReferenceRecord:
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
        str | None, Field(default=None, description="SHA256 of cached content")
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

    schema_version: Annotated[int, Field(default=1, ge=1)] = 1
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
