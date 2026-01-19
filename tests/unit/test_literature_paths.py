"""Unit tests for literature path conventions.

Tests verify that:
1. Path functions return relative paths (not absolute)
2. Paths follow the canonical conventions from SPEC-010
3. Problem IDs are zero-padded to 4 digits
4. arXiv IDs preserve version suffixes when present
"""

from pathlib import Path

from erdos.core.literature_paths import (
    get_arxiv_cache_path,
    get_arxiv_extract_path,
    get_manifest_path,
)


class TestManifestPath:
    """Test manifest path generation."""

    def test_manifest_path_single_digit(self) -> None:
        """Manifest path for single-digit problem IDs uses zero-padding."""
        path = get_manifest_path(6)
        assert path == Path("literature/manifests/0006.yaml")
        assert not path.is_absolute()

    def test_manifest_path_two_digits(self) -> None:
        """Manifest path for two-digit problem IDs uses zero-padding."""
        path = get_manifest_path(42)
        assert path == Path("literature/manifests/0042.yaml")
        assert not path.is_absolute()

    def test_manifest_path_three_digits(self) -> None:
        """Manifest path for three-digit problem IDs uses zero-padding."""
        path = get_manifest_path(123)
        assert path == Path("literature/manifests/0123.yaml")
        assert not path.is_absolute()

    def test_manifest_path_four_digits(self) -> None:
        """Manifest path for four-digit problem IDs uses zero-padding."""
        path = get_manifest_path(9999)
        assert path == Path("literature/manifests/9999.yaml")
        assert not path.is_absolute()


class TestArxivCachePath:
    """Test arXiv cache path generation."""

    def test_cache_path_without_version(self) -> None:
        """Cache path for arXiv ID without version."""
        path = get_arxiv_cache_path("2203.00001")
        assert path == Path("literature/cache/arxiv/2203.00001/source.tar.gz")
        assert not path.is_absolute()

    def test_cache_path_with_version(self) -> None:
        """Cache path for arXiv ID with version preserves version suffix."""
        path = get_arxiv_cache_path("2203.00001v1")
        assert path == Path("literature/cache/arxiv/2203.00001v1/source.tar.gz")
        assert not path.is_absolute()

    def test_cache_path_old_format(self) -> None:
        """Cache path for old-format arXiv ID."""
        path = get_arxiv_cache_path("math/0701045")
        assert path == Path("literature/cache/arxiv/math/0701045/source.tar.gz")
        assert not path.is_absolute()


class TestArxivExtractPath:
    """Test arXiv extract path generation."""

    def test_extract_path_without_version(self) -> None:
        """Extract path for arXiv ID without version."""
        path = get_arxiv_extract_path("2203.00001")
        assert path == Path("literature/extracts/arxiv/2203.00001/fulltext.txt")
        assert not path.is_absolute()

    def test_extract_path_with_version(self) -> None:
        """Extract path for arXiv ID with version preserves version suffix."""
        path = get_arxiv_extract_path("2203.00001v1")
        assert path == Path("literature/extracts/arxiv/2203.00001v1/fulltext.txt")
        assert not path.is_absolute()

    def test_extract_path_old_format(self) -> None:
        """Extract path for old-format arXiv ID."""
        path = get_arxiv_extract_path("math/0701045")
        assert path == Path("literature/extracts/arxiv/math/0701045/fulltext.txt")
        assert not path.is_absolute()
