"""Literature path conventions (SPEC-010).

This module centralizes all path conventions for literature ingestion:
- Manifests: literature/manifests/{problem_id:04d}.yaml
- arXiv cache: literature/cache/arxiv/{arxiv_id}/source.tar.gz
- arXiv extracts: literature/extracts/arxiv/{arxiv_id}/fulltext.txt

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
