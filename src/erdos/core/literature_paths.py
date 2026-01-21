"""Literature path conventions (SPEC-010, SPEC-019).

This module centralizes all path conventions for literature ingestion:
- Manifests: literature/manifests/{problem_id:04d}.yaml
- arXiv cache: literature/cache/arxiv/{arxiv_id}/source.tar.gz
- arXiv extracts: literature/extracts/arxiv/{arxiv_id}/fulltext.txt
- PDF cache: literature/cache/pdf/{reference_id}/paper.pdf (SPEC-019)
- PDF extracts: literature/extracts/pdf/{reference_id}/fulltext.md (SPEC-019)

All paths are relative to the repository root for portability.
"""

from pathlib import Path


def get_manifest_path(problem_id: int) -> Path:
    """Get the manifest path for a problem.

    Args:
        problem_id: Erdős problem ID

    Returns:
        Relative path to manifest file (e.g., literature/manifests/0006.yaml)
    """
    return Path(f"literature/manifests/{problem_id:04d}.yaml")


def get_arxiv_cache_path(arxiv_id: str) -> Path:
    """Get the cache path for an arXiv source tarball.

    Args:
        arxiv_id: arXiv identifier (with or without version suffix)

    Returns:
        Relative path to cached tarball (e.g., literature/cache/arxiv/2203.00001/source.tar.gz)
    """
    return Path(f"literature/cache/arxiv/{arxiv_id}/source.tar.gz")


def get_arxiv_extract_path(arxiv_id: str) -> Path:
    """Get the extract path for an arXiv fulltext.

    Args:
        arxiv_id: arXiv identifier (with or without version suffix)

    Returns:
        Relative path to extracted text (e.g., literature/extracts/arxiv/2203.00001/fulltext.txt)
    """
    return Path(f"literature/extracts/arxiv/{arxiv_id}/fulltext.txt")


def get_pdf_cache_path(reference_id: str) -> Path:
    """Get the cache path for a PDF file (SPEC-019).

    Args:
        reference_id: Unique reference identifier (DOI or arXiv ID, sanitized)

    Returns:
        Relative path to cached PDF (e.g., literature/cache/pdf/10.1000_example/paper.pdf)
    """
    return Path(f"literature/cache/pdf/{reference_id}/paper.pdf")


def get_pdf_extract_path(reference_id: str) -> Path:
    """Get the extract path for PDF-derived text (SPEC-019).

    Args:
        reference_id: Unique reference identifier (DOI or arXiv ID, sanitized)

    Returns:
        Relative path to extracted markdown (e.g., literature/extracts/pdf/10.1000_example/fulltext.md)
    """
    return Path(f"literature/extracts/pdf/{reference_id}/fulltext.md")


def sanitize_reference_id(identifier: str) -> str:
    """Sanitize a DOI or arXiv ID for use as directory name (SPEC-019).

    Args:
        identifier: DOI (e.g., "10.1000/example") or arXiv ID (e.g., "2203.00001")

    Returns:
        Sanitized string safe for filesystem paths (e.g., "10.1000_example")
    """
    # Replace characters that are problematic in file paths
    return identifier.replace("/", "_").replace(":", "_").replace("\\", "_")
