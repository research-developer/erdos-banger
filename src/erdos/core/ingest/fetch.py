"""Reference fetching and download logic."""

import hashlib
import tarfile
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

import requests

from erdos.core.arxiv_client import (
    extract_arxiv_text,
    fetch_arxiv_atom,
    parse_arxiv_atom,
)
from erdos.core.crossref_client import fetch_crossref_work, parse_crossref_work
from erdos.core.ingest.models import (
    ArxivDownloadResult,
    ProcessAllReferencesResult,
    ReferenceProcessResult,
)
from erdos.core.ingest.stable_key import get_stable_key
from erdos.core.literature_paths import (
    get_arxiv_cache_path,
    get_arxiv_extract_path,
)
from erdos.core.models import (
    ManifestEntry,
    ProblemManifest,
    ProblemRecord,
    ReferenceEntry,
    ReferenceRecord,
)


def download_and_extract_arxiv(
    arxiv_id: str,
    repo_root: Path,
    timeout: float,
) -> ArxivDownloadResult:
    """Download arXiv source tarball and extract text.

    This is the single implementation used by both DOI+arXiv and arXiv-only paths.

    Args:
        arxiv_id: arXiv identifier (e.g., "2203.00001").
        repo_root: Repository root directory.
        timeout: HTTP timeout in seconds.

    Returns:
        ArxivDownloadResult with cache/extract paths or error.
    """
    cache_path = None
    cache_hash = None
    extract_path = None
    extracted = False
    error = None

    try:
        arxiv_cache_path = repo_root / get_arxiv_cache_path(arxiv_id)
        arxiv_extract_path = repo_root / get_arxiv_extract_path(arxiv_id)

        # Download source
        source_url = f"https://arxiv.org/e-print/{arxiv_id}"
        response = requests.get(source_url, timeout=timeout)
        response.raise_for_status()
        tarball_bytes = response.content

        # Write cache
        arxiv_cache_path.parent.mkdir(parents=True, exist_ok=True)
        arxiv_cache_path.write_bytes(tarball_bytes)

        # Compute hash (SHA256 for cache integrity, not crypto)
        cache_hash = hashlib.sha256(tarball_bytes).hexdigest()
        cache_path = get_arxiv_cache_path(arxiv_id)

        # Extract text
        try:
            text_bytes = extract_arxiv_text(tarball_bytes)
            text = text_bytes.decode("utf-8", errors="replace")
            arxiv_extract_path.parent.mkdir(parents=True, exist_ok=True)
            arxiv_extract_path.write_text(text, encoding="utf-8")
            extract_path = get_arxiv_extract_path(arxiv_id)
            extracted = True
        except (OSError, ValueError, tarfile.TarError) as e:
            error = f"Extraction failed: {e}"
            extracted = False
    except (OSError, requests.RequestException) as e:
        error = f"Download failed: {e}"

    return ArxivDownloadResult(
        cache_path=cache_path,
        cache_hash=cache_hash,
        extract_path=extract_path,
        extracted=extracted,
        error=error,
    )


def _find_existing_manifest_entry(
    ref: ReferenceEntry,
    existing_manifest: ProblemManifest | None,
    *,
    force: bool,
) -> ManifestEntry | None:
    """Return an existing manifest entry for this reference, if available."""
    if existing_manifest is None or force:
        return None
    stable_key = get_stable_key(ref)
    for entry in existing_manifest.entries:
        if get_stable_key(entry.reference) == stable_key:
            return entry
    return None


def _error_manifest_entry(
    ref: ReferenceEntry, *, title: str, error: str
) -> ManifestEntry:
    """Create a manifest entry representing a failed ingestion attempt."""
    return ManifestEntry(
        reference=ReferenceRecord(
            doi=ref.doi,
            arxiv_id=ref.arxiv_id,
            title=title,
            authors=[],
            source="error",
        ),
        error=error,
        ingested_at=datetime.now(UTC),
    )


def fetch_reference_entry(
    ref: ReferenceEntry,
    *,
    repo_root: Path,
    allow_download: bool,
    allow_network: bool,
    timeout: float,
    mailto: str,
) -> ManifestEntry:
    """Fetch metadata and optionally download content for a reference."""
    if not allow_network:
        raise RuntimeError("Network access disabled but required for fetching")

    # Case 1: Both DOI and arXiv ID (merged entry)
    if ref.doi and ref.arxiv_id:
        # Fetch metadata via Crossref (DOI is authoritative)
        crossref_data = fetch_crossref_work(ref.doi, mailto=mailto, timeout=timeout)
        reference = parse_crossref_work(crossref_data, doi=ref.doi)
        reference.arxiv_id = ref.arxiv_id

        # Download arXiv source if enabled
        if allow_download:
            download_result = download_and_extract_arxiv(
                arxiv_id=ref.arxiv_id,
                repo_root=repo_root,
                timeout=timeout,
            )
            cache_path = download_result.cache_path
            cache_hash = download_result.cache_hash
            extract_path = download_result.extract_path
            extracted = download_result.extracted
            error = download_result.error
        else:
            cache_path = None
            cache_hash = None
            extract_path = None
            extracted = False
            error = None

        return ManifestEntry(
            reference=reference,
            cached=cache_path is not None,
            cache_path=cache_path,
            cache_hash=cache_hash,
            extracted=extracted,
            extract_path=extract_path,
            ingested_at=datetime.now(UTC),
            error=error,
        )

    # Case 2: DOI only
    if ref.doi:
        crossref_data = fetch_crossref_work(ref.doi, mailto=mailto, timeout=timeout)
        reference = parse_crossref_work(crossref_data, doi=ref.doi)

        return ManifestEntry(
            reference=reference,
            ingested_at=datetime.now(UTC),
        )

    # Case 3: arXiv only
    if ref.arxiv_id:
        arxiv_atom = fetch_arxiv_atom(ref.arxiv_id, timeout=timeout)
        reference = parse_arxiv_atom(arxiv_atom)

        # Download arXiv source if enabled
        if allow_download:
            download_result = download_and_extract_arxiv(
                arxiv_id=ref.arxiv_id,
                repo_root=repo_root,
                timeout=timeout,
            )
            cache_path = download_result.cache_path
            cache_hash = download_result.cache_hash
            extract_path = download_result.extract_path
            extracted = download_result.extracted
            error = download_result.error
        else:
            cache_path = None
            cache_hash = None
            extract_path = None
            extracted = False
            error = None

        return ManifestEntry(
            reference=reference,
            cached=cache_path is not None,
            cache_path=cache_path,
            cache_hash=cache_hash,
            extracted=extracted,
            extract_path=extract_path,
            ingested_at=datetime.now(UTC),
            error=error,
        )

    raise ValueError("Reference has no DOI or arXiv ID")


def process_single_reference(
    ref: ReferenceEntry,
    *,
    existing_manifest: ProblemManifest | None,
    force: bool,
    repo_root: Path,
    allow_download: bool,
    allow_network: bool,
    timeout: float,
    mailto: str,
) -> ReferenceProcessResult:
    """Process a single reference, reusing a cached manifest entry unless forced."""
    if existing_entry := _find_existing_manifest_entry(
        ref,
        existing_manifest,
        force=force,
    ):
        return ReferenceProcessResult(
            entry=existing_entry,
            failed=False,
            network_failed=False,
            internal_error=None,
        )

    # Fetch new entry
    try:
        entry = fetch_reference_entry(
            ref=ref,
            repo_root=repo_root,
            allow_download=allow_download,
            allow_network=allow_network,
            timeout=timeout,
            mailto=mailto,
        )
        # Check if entry has error from download/extraction
        failed = entry.error is not None
        network_failed = (
            entry.error.startswith("Download failed:") if entry.error else False
        )
        return ReferenceProcessResult(
            entry=entry,
            failed=failed,
            network_failed=network_failed,
            internal_error=None,
        )
    except (requests.RequestException, RuntimeError) as e:
        error_entry = _error_manifest_entry(
            ref,
            title=f"Failed to fetch: {ref.key}",
            error=str(e),
        )
        return ReferenceProcessResult(
            entry=error_entry,
            failed=True,
            network_failed=True,
            internal_error=None,
        )
    except (
        ET.ParseError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        tarfile.TarError,
    ) as e:
        error_entry = _error_manifest_entry(
            ref,
            title=f"Failed to fetch: {ref.key}",
            error=str(e),
        )
        return ReferenceProcessResult(
            entry=error_entry,
            failed=True,
            network_failed=False,
            internal_error=None,
        )
    except Exception as e:
        error_entry = _error_manifest_entry(
            ref,
            title=f"Unexpected error: {ref.key}",
            error=f"{type(e).__name__}: {e}",
        )
        return ReferenceProcessResult(
            entry=error_entry,
            failed=True,
            network_failed=False,
            internal_error=e,
        )


def process_all_references(
    problem: ProblemRecord,
    *,
    existing_manifest: ProblemManifest | None,
    force: bool,
    repo_root: Path,
    allow_download: bool,
    allow_network: bool,
    timeout: float,
    mailto: str,
    delay: float,
) -> ProcessAllReferencesResult:
    """Process all references for a problem.

    Args:
        problem: Problem record with references.
        existing_manifest: Existing manifest for idempotence.
        force: If True, ignore existing entries.
        repo_root: Repository root directory.
        allow_download: Whether to download arXiv tarballs.
        allow_network: Whether network access is allowed.
        timeout: HTTP timeout in seconds.
        mailto: Contact email for Crossref polite pool.
        delay: Rate limiting delay between requests.

    Returns:
        ProcessAllReferencesResult with all entries and status.
    """
    entries: list[ManifestEntry] = []
    skipped = 0
    failed = 0
    internal_error: Exception | None = None
    network_failed = False
    non_network_failed = False

    for ref in problem.references:
        # Skip references without identifiers
        if not ref.doi and not ref.arxiv_id:
            skipped += 1
            continue

        # Process reference
        result = process_single_reference(
            ref,
            existing_manifest=existing_manifest,
            force=force,
            repo_root=repo_root,
            allow_download=allow_download,
            allow_network=allow_network,
            timeout=timeout,
            mailto=mailto,
        )

        entries.append(result.entry)

        if result.failed:
            failed += 1
            if result.network_failed:
                network_failed = True
            else:
                non_network_failed = True
            if result.internal_error and internal_error is None:
                internal_error = result.internal_error

        # Rate limiting
        if delay > 0:
            time.sleep(delay)

    return ProcessAllReferencesResult(
        entries=entries,
        skipped=skipped,
        failed=failed,
        internal_error=internal_error,
        network_failed=network_failed,
        non_network_failed=non_network_failed,
    )
