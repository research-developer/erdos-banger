"""Literature ingestion core logic (SPEC-010-D).

This module orchestrates:
- Loading problem references from YAML
- Fetching metadata from arXiv/Crossref
- Downloading and extracting arXiv source tarballs
- Managing manifest creation/updates with idempotence
"""

import hashlib
import tarfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import requests
import yaml
from pydantic import TypeAdapter, ValidationError

from erdos.core.arxiv_client import (
    extract_arxiv_text,
    fetch_arxiv_atom,
    parse_arxiv_atom,
)
from erdos.core.crossref_client import fetch_crossref_work, parse_crossref_work
from erdos.core.exit_codes import ExitCode
from erdos.core.literature_paths import (
    get_arxiv_cache_path,
    get_arxiv_extract_path,
    get_manifest_path,
)
from erdos.core.models import (
    CLIOutput,
    ManifestEntry,
    ProblemManifest,
    ProblemRecord,
    ReferenceEntry,
    ReferenceRecord,
)
from erdos.core.ports import ProblemRepository
from erdos.core.problem_loader import ProblemLoaderError


def _load_problem(
    problem_id: int, command: str, *, repo: ProblemRepository
) -> tuple[ProblemRecord | None, CLIOutput | None]:
    """Load problem by ID, returning (problem, error).

    Returns:
        Tuple of (problem, error_output). If successful, problem is set and error_output is None.
        If failed, problem is None and error_output contains the error to return.
    """
    try:
        problem = repo.get_by_id(problem_id)
    except ProblemLoaderError as e:
        return (
            None,
            CLIOutput.err(
                command=command,
                error_type="LoaderError",
                message=str(e),
                code=ExitCode.ERROR,
            ),
        )
    except Exception as e:
        return (
            None,
            CLIOutput.err(
                command=command,
                error_type="LoaderError",
                message=str(e),
                code=ExitCode.ERROR,
            ),
        )

    if problem is None:
        return (
            None,
            CLIOutput.err(
                command=command,
                error_type="NotFoundError",
                message=f"Problem {problem_id} not found",
                code=ExitCode.NOT_FOUND,
            ),
        )

    return (problem, None)


def _load_existing_manifest(manifest_path: Path, force: bool) -> ProblemManifest | None:
    """Load existing manifest if present and not forcing refresh.

    Args:
        manifest_path: Path to manifest file.
        force: If True, ignore existing manifest.

    Returns:
        Loaded ProblemManifest or None if not present/corrupted/forcing.
    """
    if not manifest_path.exists() or force:
        return None

    try:
        with manifest_path.open() as f:
            manifest_data = yaml.safe_load(f)
        # Use TypeAdapter with strict=False to allow string->enum/datetime conversion
        adapter = TypeAdapter(ProblemManifest)
        return adapter.validate_python(manifest_data, strict=False)
    except (OSError, yaml.YAMLError, ValidationError, TypeError, ValueError):
        # If manifest is corrupted, return None to proceed with fresh ingestion
        return None


@dataclass
class _ReferenceProcessResult:
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


def _process_single_reference(
    ref: ReferenceEntry,
    *,
    existing_manifest: ProblemManifest | None,
    force: bool,
    repo_root: Path,
    allow_download: bool,
    allow_network: bool,
    timeout: float,
    mailto: str,
) -> _ReferenceProcessResult:
    """Process a single reference, checking for existing entry or fetching new.

    Args:
        ref: Reference to process.
        existing_manifest: Existing manifest to check for cached entries.
        force: If True, ignore existing entries and re-fetch.
        repo_root: Repository root directory.
        allow_download: Whether to download arXiv tarballs.
        allow_network: Whether network access is allowed.
        timeout: HTTP timeout in seconds.
        mailto: Contact email for Crossref polite pool.

    Returns:
        _ReferenceProcessResult with entry and failure status.
    """
    # Check for existing entry if not forcing
    stable_key = get_stable_key(ref)
    existing_entry = None
    if existing_manifest and not force:
        for entry in existing_manifest.entries:
            if get_stable_key(entry.reference) == stable_key:
                existing_entry = entry
                break

    if existing_entry:
        # Reuse existing entry (idempotence)
        return _ReferenceProcessResult(
            entry=existing_entry,
            failed=False,
            network_failed=False,
            internal_error=None,
        )

    # Fetch new entry
    try:
        entry = _fetch_reference_entry(
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
        return _ReferenceProcessResult(
            entry=entry,
            failed=failed,
            network_failed=network_failed,
            internal_error=None,
        )
    except requests.RequestException as e:
        error_entry = ManifestEntry(
            reference=ReferenceRecord(
                doi=ref.doi,
                arxiv_id=ref.arxiv_id,
                title=f"Failed to fetch: {ref.key}",
                authors=[],
                source="error",
            ),
            error=str(e),
            ingested_at=datetime.now(UTC),
        )
        return _ReferenceProcessResult(
            entry=error_entry,
            failed=True,
            network_failed=True,
            internal_error=None,
        )
    except RuntimeError as e:
        # Network policy errors (e.g., --no-network)
        error_entry = ManifestEntry(
            reference=ReferenceRecord(
                doi=ref.doi,
                arxiv_id=ref.arxiv_id,
                title=f"Failed to fetch: {ref.key}",
                authors=[],
                source="error",
            ),
            error=str(e),
            ingested_at=datetime.now(UTC),
        )
        return _ReferenceProcessResult(
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
        # Record failure but continue
        error_entry = ManifestEntry(
            reference=ReferenceRecord(
                doi=ref.doi,
                arxiv_id=ref.arxiv_id,
                title=f"Failed to fetch: {ref.key}",
                authors=[],
                source="error",
            ),
            error=str(e),
            ingested_at=datetime.now(UTC),
        )
        return _ReferenceProcessResult(
            entry=error_entry,
            failed=True,
            network_failed=False,
            internal_error=None,
        )
    except Exception as e:
        # Unexpected internal error
        error_entry = ManifestEntry(
            reference=ReferenceRecord(
                doi=ref.doi,
                arxiv_id=ref.arxiv_id,
                title=f"Unexpected error: {ref.key}",
                authors=[],
                source="error",
            ),
            error=f"{type(e).__name__}: {e}",
            ingested_at=datetime.now(UTC),
        )
        return _ReferenceProcessResult(
            entry=error_entry,
            failed=True,
            network_failed=False,
            internal_error=e,
        )


def _write_manifest_atomic(
    manifest: ProblemManifest, manifest_path: Path
) -> tuple[bool, str | None]:
    """Write manifest to disk using atomic rename.

    Args:
        manifest: Manifest to write.
        manifest_path: Target path for manifest file.

    Returns:
        Tuple of (success, error_message). error_message is None on success.
    """
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = manifest_path.with_suffix(".tmp")
    try:
        with temp_path.open("w") as f:
            yaml.dump(manifest.model_dump(mode="json"), f, default_flow_style=False)
        temp_path.replace(manifest_path)
        return (True, None)
    except (OSError, yaml.YAMLError) as e:
        if temp_path.exists():
            temp_path.unlink()
        return (False, f"Failed to write manifest: {e}")


def _check_duplicate_keys(
    entries: list[ManifestEntry], command: str
) -> CLIOutput | None:
    """Check for duplicate stable keys in entries.

    Returns:
        Error CLIOutput if duplicates found, None otherwise.
    """
    seen_keys = set()
    for entry in entries:
        key = get_stable_key(entry.reference)
        if key in seen_keys:
            return CLIOutput.err(
                command=command,
                error_type="ConfigError",
                message=f"Duplicate reference key detected: {key}",
                code=ExitCode.CONFIG_ERROR,
            )
        seen_keys.add(key)
    return None


@dataclass
class _ProcessAllReferencesResult:
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


def _process_all_references(
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
) -> _ProcessAllReferencesResult:
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
        _ProcessAllReferencesResult with all entries and status.
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
        result = _process_single_reference(
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

    return _ProcessAllReferencesResult(
        entries=entries,
        skipped=skipped,
        failed=failed,
        internal_error=internal_error,
        network_failed=network_failed,
        non_network_failed=non_network_failed,
    )


def _create_manifest(
    problem_id: int,
    entries: list[ManifestEntry],
    existing_manifest: ProblemManifest | None,
) -> ProblemManifest:
    """Create manifest with entries.

    Args:
        problem_id: Problem ID.
        entries: Manifest entries.
        existing_manifest: Existing manifest to preserve created_at timestamp.

    Returns:
        New ProblemManifest.
    """
    return ProblemManifest(
        problem_id=problem_id,
        entries=entries,
        created_at=existing_manifest.created_at
        if existing_manifest
        else datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _build_ingest_result(
    *,
    command: str,
    problem_id: int,
    manifest: ProblemManifest,
    references_total: int,
    entries_written: int,
    skipped: int,
    failed: int,
    internal_error: Exception | None,
    network_failed: bool,
    non_network_failed: bool,
) -> CLIOutput:
    """Build the final CLIOutput result for ingestion.

    Args:
        command: Command name.
        problem_id: Problem ID.
        manifest: Created manifest.
        references_total: Total number of references.
        entries_written: Number of entries written.
        skipped: Number of references skipped.
        failed: Number of failed references.
        internal_error: Internal error if any.
        network_failed: Whether any network errors occurred.
        non_network_failed: Whether any non-network errors occurred.

    Returns:
        CLIOutput with success or error status.
    """
    data = {
        "problem_id": problem_id,
        "manifest_path": str(get_manifest_path(problem_id)),
        "references_total": references_total,
        "entries_written": entries_written,
        "skipped": skipped,
        "manifest": manifest.model_dump(mode="json"),
    }

    if failed > 0:
        if internal_error is not None:
            result = CLIOutput.err(
                command=command,
                error_type="Error",
                message=f"Unexpected error during ingestion: {type(internal_error).__name__}: {internal_error}",
                code=ExitCode.ERROR,
            )
            if isinstance(result.error, dict):
                result.error.update(
                    {
                        "manifest_path": str(get_manifest_path(problem_id)),
                        "references_processed": entries_written,
                        "references_failed": failed,
                    }
                )
            return result

        result = CLIOutput.err(
            command=command,
            error_type="NetworkError"
            if network_failed and not non_network_failed
            else "IngestError",
            message=f"{failed} reference(s) failed (see manifest)",
            code=ExitCode.NETWORK_ERROR
            if network_failed and not non_network_failed
            else ExitCode.ERROR,
        )
        if isinstance(result.error, dict):
            result.error.update(
                {
                    "manifest_path": str(get_manifest_path(problem_id)),
                    "references_processed": entries_written,
                    "references_failed": failed,
                }
            )
        return result

    return CLIOutput.ok(command=command, data=data)


def ingest_problem_references(
    problem_id: int,
    *,
    repo: ProblemRepository,
    repo_root: Path,
    force: bool = False,
    no_download: bool = False,
    no_network: bool = False,
    timeout: float = 30.0,
    delay: float = 3.0,
    mailto: str,
) -> CLIOutput:
    """Ingest references for a problem.

    Args:
        problem_id: Erdős problem ID.
        repo: Problem repository (injected).
        repo_root: Repository root directory.
        force: Re-fetch even if already cached.
        no_download: Fetch metadata only, no arXiv tarballs.
        no_network: Fail if network access required.
        timeout: HTTP timeout in seconds.
        delay: Delay between API requests in seconds.
        mailto: Contact email for Crossref polite pool.

    Returns:
        CLIOutput with ingestion results.
    """
    command = "erdos ingest"

    # Convert negative flags to positive internal variables for readability
    allow_download = not no_download
    allow_network = not no_network

    # Load problem
    problem, error = _load_problem(problem_id, command, repo=repo)
    if error or problem is None:
        return error or CLIOutput.err(
            command=command,
            error_type="LoaderError",
            message="Failed to load problem",
            code=ExitCode.ERROR,
        )

    # Get manifest path
    manifest_path = repo_root / get_manifest_path(problem_id)

    # Load existing manifest if present
    existing_manifest = _load_existing_manifest(manifest_path, force)

    # Process all references
    process_result = _process_all_references(
        problem,
        existing_manifest=existing_manifest,
        force=force,
        repo_root=repo_root,
        allow_download=allow_download,
        allow_network=allow_network,
        timeout=timeout,
        mailto=mailto,
        delay=delay,
    )

    # Check for duplicate stable keys
    duplicate_error = _check_duplicate_keys(process_result.entries, command)
    if duplicate_error:
        return duplicate_error

    # Create and write manifest
    manifest = _create_manifest(problem_id, process_result.entries, existing_manifest)
    success, error_msg = _write_manifest_atomic(manifest, manifest_path)
    if not success:
        return CLIOutput.err(
            command=command,
            error_type="IOError",
            message=error_msg or "Unknown write error",
            code=ExitCode.ERROR,
        )

    # Return result
    return _build_ingest_result(
        command=command,
        problem_id=problem_id,
        manifest=manifest,
        references_total=len(problem.references),
        entries_written=len(process_result.entries),
        skipped=process_result.skipped,
        failed=process_result.failed,
        internal_error=process_result.internal_error,
        network_failed=process_result.network_failed,
        non_network_failed=process_result.non_network_failed,
    )


class HasIdentifiers(Protocol):
    """Protocol for objects with DOI and arXiv identifiers.

    Used by get_stable_key to work with both ReferenceEntry and ReferenceRecord.
    """

    @property
    def doi(self) -> str | None:
        """DOI identifier."""
        ...

    @property
    def arxiv_id(self) -> str | None:
        """arXiv identifier."""
        ...


def get_stable_key(obj: HasIdentifiers) -> str:
    """Get stable deduplication key for any object with identifiers.

    This function works with both ReferenceEntry and ReferenceRecord,
    eliminating the need for separate type-specific functions.

    Args:
        obj: Any object with doi and arxiv_id attributes

    Returns:
        Stable key in format "doi:<lowercased-doi>" or "arxiv:<id>",
        or empty string if no identifiers present.

    Examples:
        >>> from erdos.core.models import ReferenceEntry, ReferenceRecord
        >>> ref = ReferenceEntry(key="Test2023", doi="10.1007/BF01940595")
        >>> get_stable_key(ref)
        'doi:10.1007/bf01940595'
        >>> rec = ReferenceRecord(arxiv_id="2203.00001", title="Test", source="arxiv")
        >>> get_stable_key(rec)
        'arxiv:2203.00001'
    """
    if obj.doi:
        return f"doi:{obj.doi.lower()}"
    if obj.arxiv_id:
        return f"arxiv:{obj.arxiv_id}"
    return ""


@dataclass
class ArxivDownloadResult:
    """Result of downloading and extracting an arXiv paper.

    Attributes:
        cache_path: Relative path to cached tarball (None if failed).
        cache_hash: MD5 hash of cached tarball (None if failed).
        extract_path: Relative path to extracted text (None if not extracted).
        extracted: True if text extraction succeeded.
        error: Error message if download or extraction failed.
    """

    cache_path: Path | None
    cache_hash: str | None
    extract_path: Path | None
    extracted: bool
    error: str | None


def _download_and_extract_arxiv(
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

        # Compute hash
        cache_hash = hashlib.md5(tarball_bytes).hexdigest()  # noqa: S324
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


def _fetch_reference_entry(
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
            download_result = _download_and_extract_arxiv(
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
            download_result = _download_and_extract_arxiv(
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
