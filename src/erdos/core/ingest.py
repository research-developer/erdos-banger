"""Literature ingestion core logic (SPEC-010-D).

This module orchestrates:
- Loading problem references from YAML
- Fetching metadata from arXiv/Crossref
- Downloading and extracting arXiv source tarballs
- Managing manifest creation/updates with idempotence
"""

import hashlib
import time
from datetime import UTC, datetime
from pathlib import Path

import requests
import yaml
from pydantic import TypeAdapter

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
from erdos.core.problem_loader import ProblemLoader


def ingest_problem_references(  # noqa: PLR0912, PLR0915
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
    # Load problem
    try:
        loader = ProblemLoader.from_default()
        problem = loader.get_by_id(problem_id)
        if problem is None:
            return CLIOutput.err(
                command="ingest",
                error_type="NotFoundError",
                message=f"Problem {problem_id} not found",
                code=ExitCode.NOT_FOUND,
            )
    except Exception as e:
        return CLIOutput.err(
            command="ingest",
            error_type="NotFoundError",
            message=f"Problem {problem_id} not found: {e}",
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
        except Exception:  # noqa: S110
            # If manifest is corrupted, proceed with fresh ingestion
            pass

    # Process references
    references_total = len(problem.references)
    entries: list[ManifestEntry] = []
    skipped = 0
    failed = 0

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
                no_download=no_download,
                no_network=no_network,
                timeout=timeout,
                mailto=mailto,
            )
            entries.append(entry)

            # Rate limiting
            if delay > 0:
                time.sleep(delay)
        except Exception as e:
            # Record failure but continue
            failed += 1
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

    # Check for duplicate stable keys
    seen_keys = set()
    for entry in entries:
        key = _get_stable_key_from_record(entry.reference)
        if key in seen_keys:
            return CLIOutput.err(
                command="ingest",
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
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        return CLIOutput.err(
            command="ingest",
            error_type="IOError",
            message=f"Failed to write manifest: {e}",
            code=ExitCode.ERROR,
        )

    # Return result
    entries_written = len([e for e in entries if e.error is None])
    data = {
        "problem_id": problem_id,
        "manifest_path": str(get_manifest_path(problem_id)),
        "references_total": references_total,
        "entries_written": entries_written,
        "skipped": skipped,
        "manifest": manifest.model_dump(mode="json"),
    }

    if failed > 0:
        return CLIOutput.err(
            command="ingest",
            error_type="NetworkError",
            message=f"{failed} reference(s) failed (see manifest)",
            code=ExitCode.NETWORK_ERROR,
        )

    return CLIOutput.ok(command="ingest", data=data)


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


def _fetch_reference_entry(  # noqa: PLR0915
    ref: ReferenceEntry,
    *,
    repo_root: Path,
    no_download: bool,
    no_network: bool,
    timeout: float,
    mailto: str,
) -> ManifestEntry:
    """Fetch metadata and optionally download content for a reference."""
    if no_network:
        raise RuntimeError("Network access disabled but required for fetching")

    # Case 1: Both DOI and arXiv ID (merged entry)
    if ref.doi and ref.arxiv_id:
        # Fetch metadata via Crossref (DOI is authoritative)
        crossref_data = fetch_crossref_work(ref.doi, mailto=mailto, timeout=timeout)
        reference = parse_crossref_work(crossref_data, doi=ref.doi)
        reference.arxiv_id = ref.arxiv_id

        # Download arXiv source if enabled
        cache_path = None
        cache_hash = None
        extract_path = None
        extracted = False
        error = None

        if not no_download:
            try:
                arxiv_cache_path = repo_root / get_arxiv_cache_path(ref.arxiv_id)
                arxiv_extract_path = repo_root / get_arxiv_extract_path(ref.arxiv_id)

                # Download source
                source_url = f"https://arxiv.org/e-print/{ref.arxiv_id}"
                response = requests.get(source_url, timeout=timeout)
                response.raise_for_status()
                tarball_bytes = response.content

                # Write cache
                arxiv_cache_path.parent.mkdir(parents=True, exist_ok=True)
                arxiv_cache_path.write_bytes(tarball_bytes)

                # Compute hash
                cache_hash = hashlib.md5(tarball_bytes).hexdigest()  # noqa: S324
                cache_path = get_arxiv_cache_path(ref.arxiv_id)

                # Extract text
                try:
                    text_bytes = extract_arxiv_text(tarball_bytes)
                    text = text_bytes.decode("utf-8", errors="replace")
                    arxiv_extract_path.parent.mkdir(parents=True, exist_ok=True)
                    arxiv_extract_path.write_text(text, encoding="utf-8")
                    extract_path = get_arxiv_extract_path(ref.arxiv_id)
                    extracted = True
                except Exception as e:
                    error = f"Extraction failed: {e}"
                    extracted = False
            except Exception as e:
                error = f"Download failed: {e}"

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

        cache_path = None
        cache_hash = None
        extract_path = None
        extracted = False
        error = None

        if not no_download:
            try:
                arxiv_cache_path = repo_root / get_arxiv_cache_path(ref.arxiv_id)
                arxiv_extract_path = repo_root / get_arxiv_extract_path(ref.arxiv_id)

                # Download source
                source_url = f"https://arxiv.org/e-print/{ref.arxiv_id}"
                response = requests.get(source_url, timeout=timeout)
                response.raise_for_status()
                tarball_bytes = response.content

                # Write cache
                arxiv_cache_path.parent.mkdir(parents=True, exist_ok=True)
                arxiv_cache_path.write_bytes(tarball_bytes)

                # Compute hash
                cache_hash = hashlib.md5(tarball_bytes).hexdigest()  # noqa: S324
                cache_path = get_arxiv_cache_path(ref.arxiv_id)

                # Extract text
                try:
                    text_bytes = extract_arxiv_text(tarball_bytes)
                    text = text_bytes.decode("utf-8", errors="replace")
                    arxiv_extract_path.parent.mkdir(parents=True, exist_ok=True)
                    arxiv_extract_path.write_text(text, encoding="utf-8")
                    extract_path = get_arxiv_extract_path(ref.arxiv_id)
                    extracted = True
                except Exception as e:
                    error = f"Extraction failed: {e}"
                    extracted = False
            except Exception as e:
                error = f"Download failed: {e}"

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
