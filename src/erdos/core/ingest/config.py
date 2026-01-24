"""Ingest configuration objects (parameter object pattern).

These dataclasses group related parameters used across the ingest orchestration
layers (fetch/service/app). They are intentionally small and immutable to reduce
call-site noise and signature sprawl.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path


class MetadataSource(str, Enum):
    """Metadata source for reference ingestion."""

    OPENALEX = "openalex"
    ARXIV = "arxiv"
    CROSSREF = "crossref"


@dataclass(frozen=True)
class FetchConfig:
    """Configuration for reference fetching and rate limiting."""

    repo_root: Path
    allow_download: bool
    allow_network: bool
    timeout: float
    mailto: str
    delay: float


@dataclass(frozen=True)
class PDFConfig:
    """Configuration for PDF download + extraction (SPEC-019)."""

    enabled: bool = False
    converter: str = "marker"
    use_llm: bool = False


@dataclass(frozen=True)
class IngestConfig:
    """Configuration for reference ingestion coordination."""

    fetch: FetchConfig
    pdf: PDFConfig
    force: bool = False
    source: MetadataSource = MetadataSource.OPENALEX
