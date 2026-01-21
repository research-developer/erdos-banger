"""Ingest package: reference ingestion for Erdős problems.

This package provides:
- stable_key: Stable key generation for deduplication
- models: Result dataclasses
- fetch: Reference fetching and download
- service: Orchestration (ingest_problem_references)

All public APIs are re-exported for backward compatibility.
"""

# Re-export public APIs for backward compatibility
from erdos.core.ingest.fetch import (
    MetadataSource,
    download_and_extract_arxiv,
    fetch_reference_entry,
    process_all_references,
    process_single_reference,
)
from erdos.core.ingest.models import (
    ArxivDownloadResult,
    ProcessAllReferencesResult,
    ReferenceProcessResult,
)
from erdos.core.ingest.service import ingest_problem_references
from erdos.core.ingest.stable_key import HasIdentifiers, get_stable_key


# Private name aliases for backward compatibility with internal/test imports
_download_and_extract_arxiv = download_and_extract_arxiv
_fetch_reference_entry = fetch_reference_entry
_process_all_references = process_all_references
_process_single_reference = process_single_reference
_ReferenceProcessResult = ReferenceProcessResult
_ProcessAllReferencesResult = ProcessAllReferencesResult

__all__ = [
    # Models
    "ArxivDownloadResult",
    "HasIdentifiers",
    "MetadataSource",
    "ProcessAllReferencesResult",
    "ReferenceProcessResult",
    "_ProcessAllReferencesResult",
    "_ReferenceProcessResult",
    # Backward compat aliases
    "_download_and_extract_arxiv",
    "_fetch_reference_entry",
    "_process_all_references",
    "_process_single_reference",
    # Fetch
    "download_and_extract_arxiv",
    "fetch_reference_entry",
    # Stable key
    "get_stable_key",
    # Service
    "ingest_problem_references",
    "process_all_references",
    "process_single_reference",
]
