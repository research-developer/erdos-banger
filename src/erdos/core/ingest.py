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
    ReferenceEntry,
    ReferenceRecord,
)
from erdos.core.problem_loader import ProblemLoader, ProblemLoaderError


def ingest_problem_references(  # noqa: PLR0911, PLR0912, PLR0915
    problem_id: int,
    *,
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
    try:
        loader = ProblemLoader.from_default()
    except ProblemLoaderError as e:
        return CLIOutput.err(
            command=command,
            error_type="LoaderError",
            message=str(e),
            code=ExitCode.ERROR,
        )

    try:
        problem = loader.get_by_id(problem_id)
    except ProblemLoaderError as e:
        return CLIOutput.err(
            command=command,
            error_type="LoaderError",
            message=str(e),
            code=ExitCode.ERROR,
        )

    if problem is None:
        return CLIOutput.err(
            command=command,
            error_type="NotFoundError",
            message=f"Problem {problem_id} not found",
            code=ExitCode.NOT_FOUND,
        )

    # Get manifest path
    manifest_path = repo_root / get_manifest_path(problem_id)

    # Load existing manifest if present
    existing_manifest = None
    if manifest_path.exists() and not force:
        try:
            with manifest_path.open() as f:
                manifest_data = yaml.safe_load(f)
            # Use TypeAdapter with strict=False to allow string->enum/datetime conversion
            adapter = TypeAdapter(ProblemManifest)
            existing_manifest = adapter.validate_python(manifest_data, strict=False)
        except (OSError, yaml.YAMLError, ValidationError, TypeError, ValueError):
            # If manifest is corrupted, proceed with fresh ingestion
            pass

    # Process references
    references_total = len(problem.references)
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

        # Check for existing entry if not forcing
        stable_key = _get_stable_key(ref)
        existing_entry = None
        if existing_manifest and not force:
            for entry in existing_manifest.entries:
                if _get_stable_key_from_record(entry.reference) == stable_key:
                    existing_entry = entry
                    break

        if existing_entry:
            # Reuse existing entry (idempotence)
            entries.append(existing_entry)
            continue

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
        except requests.RequestException as e:
            failed += 1
            network_failed = True
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
            entries.append(error_entry)
            continue
        except RuntimeError as e:
            # Network policy errors (e.g., --no-network) should return NETWORK_ERROR.
            failed += 1
            network_failed = True
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
            entries.append(error_entry)
            continue
        except (
            ET.ParseError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
            tarfile.TarError,
        ) as e:
            # Record failure but continue
            failed += 1
            non_network_failed = True
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
            entries.append(error_entry)
            continue
        except Exception as e:
            # Unexpected internal error: record and continue (we'll return ExitCode.ERROR).
            failed += 1
            if internal_error is None:
                internal_error = e
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
            entries.append(error_entry)
            continue

        entries.append(entry)
        if entry.error is not None:
            failed += 1
            if entry.error.startswith("Download failed:"):
                network_failed = True
            else:
                non_network_failed = True

        # Rate limiting
        if delay > 0:
            time.sleep(delay)

    # Check for duplicate stable keys
    seen_keys = set()
    for entry in entries:
        key = _get_stable_key_from_record(entry.reference)
        if key in seen_keys:
            return CLIOutput.err(
                command=command,
                error_type="ConfigError",
                message=f"Duplicate reference key detected: {key}",
                code=ExitCode.CONFIG_ERROR,
            )
        seen_keys.add(key)

    # Create manifest
    manifest = ProblemManifest(
        problem_id=problem_id,
        entries=entries,
        created_at=existing_manifest.created_at
        if existing_manifest
        else datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # Write manifest atomically
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = manifest_path.with_suffix(".tmp")
    try:
        with temp_path.open("w") as f:
            yaml.dump(manifest.model_dump(mode="json"), f, default_flow_style=False)
        temp_path.replace(manifest_path)
    except (OSError, yaml.YAMLError) as e:
        if temp_path.exists():
            temp_path.unlink()
        return CLIOutput.err(
            command=command,
            error_type="IOError",
            message=f"Failed to write manifest: {e}",
            code=ExitCode.ERROR,
        )

    # Return result
    entries_written = len(entries)
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


def _get_stable_key(ref: ReferenceEntry) -> str:
    """Get stable key for a reference (for deduplication)."""
    if ref.doi:
        return f"doi:{ref.doi.lower()}"
    if ref.arxiv_id:
        return f"arxiv:{ref.arxiv_id}"
    return ""


def _get_stable_key_from_record(record: ReferenceRecord) -> str:
    """Get stable key from a ReferenceRecord."""
    if record.doi:
        return f"doi:{record.doi.lower()}"
    if record.arxiv_id:
        return f"arxiv:{record.arxiv_id}"
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
