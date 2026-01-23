"""Ingest service: orchestrates reference ingestion for Erdős problems."""

import logging
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import TypeAdapter, ValidationError

from erdos.core.constants import API_RATE_LIMIT_DELAY
from erdos.core.exit_codes import ExitCode
from erdos.core.ingest.fetch import (
    MetadataSource,
    build_provider_from_source,
    process_all_references,
)
from erdos.core.ingest.stable_key import get_stable_key
from erdos.core.literature_paths import get_manifest_path
from erdos.core.models import (
    CLIOutput,
    ManifestEntry,
    ProblemManifest,
    ProblemRecord,
)
from erdos.core.ports import ProblemRepository
from erdos.core.problem_loader import ProblemLoaderError


logger = logging.getLogger(__name__)


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
    except (OSError, yaml.YAMLError, ValidationError, TypeError, ValueError) as e:
        logger.warning(
            "Manifest corrupted at %s; proceeding with fresh ingestion: %s",
            manifest_path,
            e,
        )
        return None


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


def _entries_content_equal(
    new_entries: list[ManifestEntry], existing_entries: list[ManifestEntry]
) -> bool:
    """Compare manifest entries for content equality (excluding operational timestamps).

    This comparison ignores:
    - `ingested_at` on each entry (operational metadata, not content)
    - `fetched_at` on references (operational metadata)

    Returns:
        True if entries are semantically equal (same content), False otherwise.
    """
    if len(new_entries) != len(existing_entries):
        return False

    for new, existing in zip(new_entries, existing_entries, strict=True):
        # Compare all fields except operational timestamps
        # Get dict representation excluding timestamps
        new_dict = new.model_dump(mode="json", exclude={"ingested_at"})
        existing_dict = existing.model_dump(mode="json", exclude={"ingested_at"})

        # Also exclude fetched_at from reference comparison
        if "reference" in new_dict and "fetched_at" in new_dict["reference"]:
            new_dict["reference"].pop("fetched_at", None)
        if "reference" in existing_dict and "fetched_at" in existing_dict["reference"]:
            existing_dict["reference"].pop("fetched_at", None)

        if new_dict != existing_dict:
            return False

    return True


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


def _create_manifest(
    problem_id: int,
    entries: list[ManifestEntry],
    existing_manifest: ProblemManifest | None,
    *,
    content_changed: bool,
) -> ProblemManifest:
    """Create manifest with entries.

    Args:
        problem_id: Problem ID.
        entries: Manifest entries.
        existing_manifest: Existing manifest to preserve timestamps.
        content_changed: If False and existing_manifest exists, preserve updated_at.

    Returns:
        New ProblemManifest.
    """
    now = datetime.now(UTC)

    # Preserve created_at from existing manifest if available
    created_at = existing_manifest.created_at if existing_manifest else now

    # Only update updated_at if content actually changed (DEBT-028)
    if existing_manifest and not content_changed:
        updated_at = existing_manifest.updated_at
    else:
        updated_at = now

    return ProblemManifest(
        problem_id=problem_id,
        entries=entries,
        created_at=created_at,
        updated_at=updated_at,
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
    delay: float = API_RATE_LIMIT_DELAY,
    mailto: str,
    pdf: bool = False,
    pdf_converter: str = "marker",
    pdf_use_llm: bool = False,
    source: MetadataSource = MetadataSource.OPENALEX,
    openalex_api_key: str | None = None,
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
        delay: Delay between processing references (not per-request). Defaults to
            API_RATE_LIMIT_DELAY. Per-reference throttling is sufficient since each
            reference makes at most 1-3 requests (DOI, arXiv metadata, arXiv source).
        mailto: Contact email for API polite pools.
        pdf: Enable PDF conversion for non-arXiv references (SPEC-019).
        pdf_converter: PDF converter backend (marker or pdfplumber).
        pdf_use_llm: Enable LLM-enhanced PDF extraction when supported.
        source: Metadata source to use (default: OpenAlex).
        openalex_api_key: Optional OpenAlex API key override (defaults to env/config).

    Returns:
        CLIOutput with ingestion results.

    Note:
        This function exceeds 80 LOC but is acceptable per DEBT-026 criteria:
        it is pure linear orchestration with no branching complexity - each step
        is a single helper call. The body contains ~12 orchestration steps with
        clear names; extracting further would obscure the workflow. Docstring
        and signature account for ~28 lines of the total.
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

    provider = None
    if allow_network:
        provider = build_provider_from_source(
            source,
            mailto=mailto,
            timeout=timeout,
            openalex_api_key=openalex_api_key,
        )

    # Process all references
    process_result = process_all_references(
        problem,
        existing_manifest=existing_manifest,
        force=force,
        repo_root=repo_root,
        allow_download=allow_download,
        allow_network=allow_network,
        timeout=timeout,
        mailto=mailto,
        delay=delay,
        pdf=pdf,
        pdf_converter=pdf_converter,
        pdf_use_llm=pdf_use_llm,
        source=source,
        provider=provider,
    )

    # Check for duplicate stable keys
    duplicate_error = _check_duplicate_keys(process_result.entries, command)
    if duplicate_error:
        return duplicate_error

    # Determine if content changed (DEBT-028: idempotent writes)
    content_changed = existing_manifest is None or not _entries_content_equal(
        process_result.entries, existing_manifest.entries
    )

    # Only write if content changed to avoid unnecessary file churn (DEBT-028)
    if content_changed:
        # Create new manifest with fresh timestamps
        manifest = _create_manifest(
            problem_id,
            process_result.entries,
            existing_manifest,
            content_changed=True,
        )
        success, error_msg = _write_manifest_atomic(manifest, manifest_path)
        if not success:
            return CLIOutput.err(
                command=command,
                error_type="IOError",
                message=error_msg or "Unknown write error",
                code=ExitCode.ERROR,
            )
    else:
        # Content unchanged - use existing manifest to ensure returned manifest
        # matches on-disk state (timestamps and all). The existing_manifest is
        # guaranteed non-None here since content_changed being False implies
        # existing_manifest exists (see content_changed condition above).
        if existing_manifest is None:
            raise RuntimeError(
                "Invariant violation: existing_manifest is None when content unchanged"
            )
        manifest = existing_manifest

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
