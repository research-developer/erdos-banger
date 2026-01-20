"""Ingest result models and dataclasses."""

from dataclasses import dataclass
from pathlib import Path

from erdos.core.models import ManifestEntry


@dataclass
class ArxivDownloadResult:
    """Result of downloading and extracting an arXiv paper.

    Attributes:
        cache_path: Relative path to cached tarball (None if failed).
        cache_hash: SHA256 hash of cached tarball (None if failed).
        extract_path: Relative path to extracted text (None if not extracted).
        extracted: True if text extraction succeeded.
        error: Error message if download or extraction failed.
    """

    cache_path: Path | None
    cache_hash: str | None
    extract_path: Path | None
    extracted: bool
    error: str | None


@dataclass
class ReferenceProcessResult:
    """Result of processing a single reference.

    Attributes:
        entry: The manifest entry created for this reference.
        failed: True if processing failed.
        network_failed: True if failure was network-related.
        internal_error: Exception if unexpected internal error occurred.
    """

    entry: ManifestEntry
    failed: bool
    network_failed: bool
    internal_error: Exception | None


@dataclass
class ProcessAllReferencesResult:
    """Result of processing all references for a problem.

    Attributes:
        entries: Manifest entries created.
        skipped: Number of references skipped (no identifiers).
        failed: Number of failed references.
        internal_error: First internal error encountered, if any.
        network_failed: True if any network errors occurred.
        non_network_failed: True if any non-network errors occurred.
    """

    entries: list[ManifestEntry]
    skipped: int
    failed: int
    internal_error: Exception | None
    network_failed: bool
    non_network_failed: bool
