"""Reference fetching orchestration (thin coordinator).

This module orchestrates reference fetching by:
- Converting MetadataSource enum to MetadataProvider instances
- Delegating metadata resolution to providers
- Delegating arXiv download/extraction to arxiv_download module
- Delegating PDF download/conversion to pdf_download module (SPEC-019)
- Building ManifestEntry results

Follows SRP: orchestration only, no direct client usage.

# exempt: DEBT-122 — 568 LOC is 68 over threshold. Justified: URL-only PDF
# handling (BUG-055) added necessary complexity for feature completeness.
"""

from __future__ import annotations

import logging
import tarfile
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, assert_never

import defusedxml.ElementTree as ET
import requests

from erdos.core.clients.openalex import OpenAlexConfig
from erdos.core.ingest.arxiv_download import download_and_extract_arxiv
from erdos.core.ingest.config import (
    FetchConfig,
    IngestConfig,
    MetadataSource,
    PDFConfig,
)
from erdos.core.ingest.models import (
    ArxivDownloadResult,
    ProcessAllReferencesResult,
    ReferenceProcessResult,
)
from erdos.core.ingest.pdf_download import download_and_extract_pdf
from erdos.core.ingest.stable_key import get_stable_key
from erdos.core.literature_paths import sanitize_reference_id
from erdos.core.models import (
    ManifestEntry,
    ProblemManifest,
    ProblemRecord,
    ReferenceEntry,
    ReferenceRecord,
)
from erdos.core.providers import ArxivProvider, CrossrefProvider, OpenAlexProvider
from erdos.core.providers.fallback import FallbackProvider


if TYPE_CHECKING:
    from pathlib import Path

    from erdos.core.ports import MetadataProvider


logger = logging.getLogger(__name__)

# Public exports for orchestrator consumers (CLI/services)
__all__ = [
    "ArxivDownloadResult",
    "FetchConfig",
    "IngestConfig",
    "MetadataSource",
    "PDFConfig",
    "build_provider_from_source",
    "download_and_extract_arxiv",
    "fetch_reference_entry",
    "process_all_references",
    "process_single_reference",
]


def build_provider_from_source(
    source: MetadataSource,
    *,
    mailto: str,
    timeout: float,
    openalex_api_key: str | None = None,
) -> MetadataProvider:
    """Build a MetadataProvider from a MetadataSource enum.

    ISP-compliant: returns a FallbackProvider with capability-specific chains.
    For single-source providers (ARXIV, CROSSREF), only the supported chain
    is populated.

    Args:
        source: The metadata source to use.
        mailto: Contact email for API polite pools.
        timeout: HTTP timeout in seconds.
        openalex_api_key: Optional OpenAlex API key. If not provided, falls back
            to OpenAlexConfig.from_env().

    Returns:
        A MetadataProvider instance for the specified source.
    """
    if source == MetadataSource.OPENALEX:
        # Full capability: OpenAlex primary with Crossref/arXiv fallback
        api_key = (openalex_api_key or "").strip() or OpenAlexConfig.from_env().api_key
        openalex_config = OpenAlexConfig(email=mailto, api_key=api_key, timeout=timeout)
        openalex = OpenAlexProvider.from_config(openalex_config)
        crossref = CrossrefProvider(mailto=mailto, timeout=timeout)
        arxiv = ArxivProvider(timeout=timeout)
        return FallbackProvider(
            doi_chain=[openalex, crossref],
            arxiv_chain=[openalex, arxiv],
            search_chain=[openalex],
        )
    if source == MetadataSource.ARXIV:
        # arXiv-only: no DOI or search capability
        arxiv = ArxivProvider(timeout=timeout)
        return FallbackProvider(
            doi_chain=[],
            arxiv_chain=[arxiv],
            search_chain=[],
        )
    if source == MetadataSource.CROSSREF:
        # Crossref-only: no arXiv or search capability
        crossref = CrossrefProvider(mailto=mailto, timeout=timeout)
        return FallbackProvider(
            doi_chain=[crossref],
            arxiv_chain=[],
            search_chain=[],
        )
    # Exhaustive match - type checker will catch missing enum cases
    assert_never(source)


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
    # Use DOI or arXiv ID if available, otherwise use a synthetic openalex_id
    # to satisfy the ReferenceRecord identifier requirement
    openalex_id = None
    if not ref.doi and not ref.arxiv_id:
        openalex_id = f"error:{ref.key}"
    return ManifestEntry(
        reference=ReferenceRecord(
            doi=ref.doi,
            arxiv_id=ref.arxiv_id,
            openalex_id=openalex_id,
            title=title,
            authors=[],
            source="error",
        ),
        error=error,
        ingested_at=datetime.now(UTC),
    )


def _build_manifest_entry_with_arxiv(
    reference: ReferenceRecord,
    arxiv_id: str,
    *,
    repo_root: Path,
    allow_download: bool,
    timeout: float,
) -> ManifestEntry:
    """Build a ManifestEntry with optional arXiv download.

    Args:
        reference: Reference metadata (already fetched)
        arxiv_id: arXiv identifier for downloading
        repo_root: Repository root directory
        allow_download: Whether to download arXiv source
        timeout: HTTP timeout in seconds

    Returns:
        ManifestEntry with cache/extract info if downloaded
    """
    if not allow_download:
        return ManifestEntry(reference=reference, ingested_at=datetime.now(UTC))

    download_result = download_and_extract_arxiv(
        arxiv_id=arxiv_id,
        repo_root=repo_root,
        timeout=timeout,
    )
    return ManifestEntry(
        reference=reference,
        cached=download_result.cache_path is not None,
        cache_path=download_result.cache_path,
        cache_hash=download_result.cache_hash,
        extracted=download_result.extracted,
        extract_path=download_result.extract_path,
        ingested_at=datetime.now(UTC),
        error=download_result.error,
    )


def _build_manifest_entry_with_pdf(
    reference: ReferenceRecord,
    pdf_url: str,
    *,
    repo_root: Path,
    reference_id: str,
    timeout: float,
    converter: str,
    use_llm: bool,
) -> ManifestEntry:
    """Build a ManifestEntry with PDF download + conversion (SPEC-019)."""
    download_result = download_and_extract_pdf(
        pdf_url,
        repo_root=repo_root,
        reference_id=reference_id,
        timeout=timeout,
        converter=converter,
        use_llm=use_llm,
    )
    return ManifestEntry(
        reference=reference,
        cached=download_result.cache_path is not None,
        cache_path=download_result.cache_path,
        cache_hash=download_result.cache_hash,
        extracted=download_result.extracted,
        extract_path=download_result.extract_path,
        ingested_at=datetime.now(UTC),
        error=download_result.error,
    )


def _process_url_only_pdf_reference(
    ref: ReferenceEntry,
    *,
    fetch: FetchConfig,
    pdf: PDFConfig,
) -> ReferenceProcessResult:
    """Process a URL-only PDF reference (BUG-055).

    Creates a minimal ReferenceRecord from the ReferenceEntry and downloads
    the PDF content. This handles references that have only a URL (no DOI or
    arXiv ID) pointing to a PDF file.

    Uses the reference key prefixed with "url:" as a synthetic openalex_id
    to satisfy the ReferenceRecord identifier requirement.

    Args:
        ref: Reference entry with URL pointing to a PDF.
        fetch: Fetch configuration.
        pdf: PDF extraction configuration.

    Returns:
        ReferenceProcessResult with the processed entry.
    """
    if not ref.url:
        raise ValueError("Reference has no URL")

    # Create minimal ReferenceRecord from the entry
    # Use a synthetic openalex_id based on the key to satisfy the identifier requirement
    reference = ReferenceRecord(
        title=ref.citation or ref.key,
        authors=[],
        source="pdf-url",
        pdf_url=ref.url,
        openalex_id=f"url:{ref.key}",  # Synthetic ID for URL-only refs
    )

    reference_id = sanitize_reference_id(ref.key)
    entry = _build_manifest_entry_with_pdf(
        reference,
        ref.url,
        repo_root=fetch.repo_root,
        reference_id=reference_id,
        timeout=fetch.timeout,
        converter=pdf.converter,
        use_llm=pdf.use_llm,
    )
    return _success_result(entry)


def _fetch_with_provider(
    ref: ReferenceEntry,
    provider: MetadataProvider,
    *,
    fetch: FetchConfig,
    pdf: PDFConfig,
) -> ManifestEntry:
    """Fetch reference metadata using MetadataProvider (SPEC-022).

    Args:
        ref: Reference entry with DOI and/or arXiv ID.
        provider: MetadataProvider for fetching metadata.
        fetch: Fetch configuration (repo root, network/download flags, timeouts).
        pdf: PDF extraction configuration (SPEC-019).

    Returns:
        ManifestEntry with metadata and optional cache info.

    Raises:
        ValueError: If reference has no identifiers or not found.
    """
    # Try DOI first, then arXiv ID
    reference: ReferenceRecord | None = None

    if ref.doi:
        reference = provider.get_by_doi(ref.doi)
        if reference is not None and ref.arxiv_id and not reference.arxiv_id:
            reference.arxiv_id = ref.arxiv_id

    if reference is None and ref.arxiv_id:
        reference = provider.get_by_arxiv(ref.arxiv_id)

    if reference is None:
        if not ref.doi and not ref.arxiv_id:
            raise ValueError("Reference has no DOI or arXiv ID")
        raise ValueError(
            f"Reference not found in {provider.provider_name}: "
            f"DOI={ref.doi}, arXiv={ref.arxiv_id}"
        )

    # Download arXiv source if we have an arXiv ID
    # Prefer ref.arxiv_id (original input without version suffix) for download URL,
    # falling back to reference.arxiv_id (metadata may include version suffix)
    arxiv_id = ref.arxiv_id or reference.arxiv_id
    if arxiv_id:
        return _build_manifest_entry_with_arxiv(
            reference,
            arxiv_id,
            repo_root=fetch.repo_root,
            allow_download=fetch.allow_download,
            timeout=fetch.timeout,
        )

    # Optional PDF conversion (SPEC-019): only for non-arXiv references.
    if fetch.allow_download and pdf.enabled and reference.pdf_url:
        reference_id = sanitize_reference_id(get_stable_key(reference))
        return _build_manifest_entry_with_pdf(
            reference,
            reference.pdf_url,
            repo_root=fetch.repo_root,
            reference_id=reference_id,
            timeout=fetch.timeout,
            converter=pdf.converter,
            use_llm=pdf.use_llm,
        )

    return ManifestEntry(reference=reference, ingested_at=datetime.now(UTC))


def fetch_reference_entry(
    ref: ReferenceEntry,
    *,
    config: IngestConfig,
    provider: MetadataProvider | None = None,
) -> ManifestEntry:
    """Fetch metadata and optionally download content for a reference.

    Args:
        ref: Reference entry with DOI and/or arXiv ID.
        config: Ingest configuration (network/download flags, timeouts, source, pdf).
        provider: Optional MetadataProvider for dependency injection (SPEC-022).
            When provided, config.source is ignored and the caller is responsible
            for including any API key overrides in the provider.

    Returns:
        ManifestEntry with metadata and optional cache info.

    Raises:
        RuntimeError: If network access is required but disabled.
        ValueError: If reference has no identifiers.
    """
    if not config.fetch.allow_network:
        raise RuntimeError("Network access disabled but required for fetching")

    # Use injected provider or build from source enum
    actual_provider = provider or build_provider_from_source(
        config.source,
        mailto=config.fetch.mailto,
        timeout=config.fetch.timeout,
        openalex_api_key=config.openalex_api_key,
    )

    return _fetch_with_provider(
        ref,
        actual_provider,
        fetch=config.fetch,
        pdf=config.pdf,
    )


def _error_result(
    ref: ReferenceEntry,
    error: Exception,
    *,
    network_failed: bool,
    internal_error: Exception | None = None,
) -> ReferenceProcessResult:
    """Create a ReferenceProcessResult for an error case."""
    title = "Unexpected error" if internal_error else "Failed to fetch"
    error_msg = f"{type(error).__name__}: {error}" if internal_error else str(error)
    entry = _error_manifest_entry(ref, title=f"{title}: {ref.key}", error=error_msg)
    return ReferenceProcessResult(
        entry=entry,
        failed=True,
        network_failed=network_failed,
        internal_error=internal_error,
    )


def _success_result(entry: ManifestEntry) -> ReferenceProcessResult:
    """Create a ReferenceProcessResult from a successful fetch."""
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


def process_single_reference(
    ref: ReferenceEntry,
    *,
    existing_manifest: ProblemManifest | None,
    config: IngestConfig,
    provider: MetadataProvider | None = None,
) -> ReferenceProcessResult:
    """Process a single reference, reusing a cached manifest entry unless forced.

    Args:
        ref: Reference entry to process.
        existing_manifest: Existing manifest for idempotence.
        config: Ingest configuration (fetch/pdf settings, force flag, source).
        provider: Optional MetadataProvider for dependency injection (SPEC-022).

    Returns:
        ReferenceProcessResult with entry and status.
    """
    if existing_entry := _find_existing_manifest_entry(
        ref, existing_manifest, force=config.force
    ):
        return ReferenceProcessResult(
            entry=existing_entry,
            failed=False,
            network_failed=False,
            internal_error=None,
        )

    try:
        entry = fetch_reference_entry(
            ref=ref,
            config=config,
            provider=provider,
        )
        return _success_result(entry)
    except (requests.RequestException, RuntimeError) as e:
        return _error_result(ref, e, network_failed=True)
    except (
        ET.ParseError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        tarfile.TarError,
    ) as e:
        return _error_result(ref, e, network_failed=False)
    except Exception as e:  # defensive catch; unexpected errors should not crash ingest
        # Log unexpected errors with full traceback for debugging
        logger.exception("Unexpected error processing reference %s", ref.key)
        return _error_result(ref, e, network_failed=False, internal_error=e)


def _is_url_only_pdf_ref(ref: ReferenceEntry, config: IngestConfig) -> bool:
    """Check if a reference is a URL-only PDF that should be processed (BUG-055)."""
    return bool(
        not ref.doi
        and not ref.arxiv_id
        and ref.url
        and ref.url.lower().endswith(".pdf")
        and config.pdf.enabled
    )


def process_all_references(
    problem: ProblemRecord,
    *,
    existing_manifest: ProblemManifest | None,
    config: IngestConfig,
    provider: MetadataProvider | None = None,
) -> ProcessAllReferencesResult:
    """Process all references for a problem.

    Args:
        problem: Problem record with references.
        existing_manifest: Existing manifest for idempotence.
        config: Ingest configuration (fetch/pdf settings, force flag, source).
        provider: Optional MetadataProvider for dependency injection (SPEC-022).

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
        result: ReferenceProcessResult | None = None

        # Skip references without identifiers (unless URL-only PDF - BUG-055)
        if not ref.doi and not ref.arxiv_id:
            if _is_url_only_pdf_ref(ref, config):
                try:
                    result = _process_url_only_pdf_reference(
                        ref, fetch=config.fetch, pdf=config.pdf
                    )
                except Exception as e:  # defensive catch for URL-only processing
                    logger.exception(
                        "Unexpected error processing URL-only ref %s", ref.key
                    )
                    result = _error_result(
                        ref, e, network_failed=False, internal_error=e
                    )
            else:
                skipped += 1
                continue
        else:
            # Process reference with DOI or arXiv ID
            result = process_single_reference(
                ref,
                existing_manifest=existing_manifest,
                config=config,
                provider=provider,
            )

        entries.append(result.entry)

        if result.failed:
            failed += 1
            network_failed = network_failed or result.network_failed
            non_network_failed = non_network_failed or not result.network_failed
            if result.internal_error and internal_error is None:
                internal_error = result.internal_error

        # Rate limiting
        if config.fetch.delay > 0:
            time.sleep(config.fetch.delay)

    return ProcessAllReferencesResult(
        entries=entries,
        skipped=skipped,
        failed=failed,
        internal_error=internal_error,
        network_failed=network_failed,
        non_network_failed=non_network_failed,
    )
