"""Unit tests for repo_root module."""

from pathlib import Path

from erdos.core.repo_root import (
    discover_repo_root,
    repo_path,
    resolve_repo_root,
)


class TestDiscoverRepoRoot:
    """Tests for discover_repo_root()."""

    def test_discovers_from_cwd(self) -> None:
        """Should discover repo root from current directory."""
        root = discover_repo_root()
        # When running tests, we're in the repo
        assert root is not None
        assert (root / "pyproject.toml").is_file()
        assert (root / "src" / "erdos").is_dir()

    def test_discovers_from_subdirectory(self, tmp_path: Path) -> None:
        """Should discover repo root from nested subdirectory."""
        # Create a fake repo structure
        repo = tmp_path / "repo"
        (repo / "src" / "erdos").mkdir(parents=True)
        (repo / "pyproject.toml").write_text("[project]\n")
        subdir = repo / "formal" / "lean"
        subdir.mkdir(parents=True)

        discovered = discover_repo_root(start=subdir)
        assert discovered == repo

    def test_returns_none_when_not_in_repo(self, tmp_path: Path) -> None:
        """Should return None when not in a repo."""
        isolated_dir = tmp_path / "not_a_repo"
        isolated_dir.mkdir()

        discovered = discover_repo_root(start=isolated_dir)
        assert discovered is None


class TestResolveRepoRoot:
    """Tests for resolve_repo_root()."""

    def test_returns_explicit_path_when_provided(self, tmp_path: Path) -> None:
        """Should return resolved explicit path."""
        result = resolve_repo_root(tmp_path)
        assert result == tmp_path.resolve()

    def test_discovers_when_none(self) -> None:
        """Should discover repo root when None passed."""
        result = resolve_repo_root(None)
        # Should find our actual repo
        assert result.is_absolute()
        assert (result / "pyproject.toml").is_file()


class TestRepoPath:
    """Tests for repo_path() helper."""

    def test_returns_absolute_path(self) -> None:
        """repo_path() should always return an absolute path."""
        result = repo_path("data", "test.yaml")
        assert result.is_absolute()

    def test_path_ends_with_parts(self) -> None:
        """repo_path() should join parts correctly."""
        result = repo_path("data", "problems_enriched.yaml")
        assert result.parts[-2:] == ("data", "problems_enriched.yaml")

    def test_single_part(self) -> None:
        """repo_path() works with a single part."""
        result = repo_path("data")
        assert result.parts[-1] == "data"

    def test_multiple_parts(self) -> None:
        """repo_path() works with multiple parts."""
        result = repo_path("data", "sync_cache", "proofs")
        assert result.parts[-3:] == ("data", "sync_cache", "proofs")

    def test_formal_lean_path(self) -> None:
        """repo_path() correctly resolves formal/lean."""
        result = repo_path("formal", "lean")
        assert result.parts[-2:] == ("formal", "lean")

    def test_result_is_under_repo_root(self) -> None:
        """repo_path() result should be under the discovered repo root."""
        root = discover_repo_root()
        assert root is not None  # We're in the repo

        result = repo_path("data", "test.yaml")
        # Result should be under root
        assert str(result).startswith(str(root))
