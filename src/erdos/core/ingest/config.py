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

    def __post_init__(self) -> None:
        if self.timeout <= 0:
            raise ValueError("timeout must be > 0")
        if self.delay < 0:
            raise ValueError("delay must be >= 0")
        if self.allow_network and not self.mailto.strip():
            raise ValueError("mailto must be non-empty when allow_network is True")


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
    openalex_api_key: str | None = None
