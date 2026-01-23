"""PDF download and text extraction.

This module handles:
- Downloading PDFs with retry logic
- Caching downloaded PDFs under the literature cache
- Converting PDFs to text/markdown via the PDF converter abstraction (SPEC-019)
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING

import requests

from erdos.core.ingest.models import PDFDownloadResult
from erdos.core.literature_paths import get_pdf_cache_path, get_pdf_extract_path
from erdos.core.pdf.converter import PDFConversionConfig, convert_pdf
from erdos.core.retry import fetch_with_retry


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pathlib import Path


def download_and_extract_pdf(
    pdf_url: str,
    *,
    repo_root: Path,
    reference_id: str,
    timeout: float,
    converter: str,
    use_llm: bool,
) -> PDFDownloadResult:
    """Download a PDF and extract text to the literature extracts directory.

    Args:
        pdf_url: Direct URL to a PDF file.
        repo_root: Repository root directory.
        reference_id: Filesystem-safe identifier (e.g. sanitized stable key).
        timeout: HTTP timeout in seconds.
        converter: PDF converter backend ("marker" or "pdfplumber").
        use_llm: Enable LLM-enhanced extraction when supported.

    Returns:
        PDFDownloadResult with cache/extract paths or error.
    """
    cache_path: Path | None = None
    cache_hash: str | None = None
    extract_path: Path | None = None
    extracted = False
    error: str | None = None

    cache_rel = get_pdf_cache_path(reference_id)
    extract_rel = get_pdf_extract_path(reference_id)
    cache_abs = repo_root / cache_rel
    extract_abs = repo_root / extract_rel

    try:
        # Download PDF with retry for transient failures
        logger.debug("Downloading PDF: %s", pdf_url)
        response = fetch_with_retry(pdf_url, timeout=timeout)
        pdf_bytes = response.content

        # Cache PDF
        cache_abs.parent.mkdir(parents=True, exist_ok=True)
        cache_abs.write_bytes(pdf_bytes)
        cache_path = cache_rel
        cache_hash = hashlib.sha256(pdf_bytes).hexdigest()

        # Convert PDF to text/markdown
        config = PDFConversionConfig(converter=converter, use_llm=use_llm)
        conversion = convert_pdf(cache_abs, config)
        if not conversion.success or not conversion.text:
            error = conversion.error or "PDF conversion failed"
            return PDFDownloadResult(
                cache_path=cache_path,
                cache_hash=cache_hash,
                extract_path=None,
                extracted=False,
                error=f"Conversion failed: {error}",
            )

        # Write extract
        extract_abs.parent.mkdir(parents=True, exist_ok=True)
        extract_abs.write_text(conversion.text, encoding="utf-8")
        extract_path = extract_rel
        extracted = True
    except (OSError, requests.RequestException) as e:
        logger.warning("PDF download/extract failed for %s: %s", pdf_url, e)
        error = f"Download failed: {e}"

    return PDFDownloadResult(
        cache_path=cache_path,
        cache_hash=cache_hash,
        extract_path=extract_path,
        extracted=extracted,
        error=error,
    )
