"""Unit tests for ProblemLoader."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest

from erdos.core.models import ProblemRecord, ProblemStatus
from erdos.core.problem_loader import ProblemLoader, ProblemLoaderError


if TYPE_CHECKING:
    from pathlib import Path


class TestProblemLoaderInit:
    def test_raises_if_file_not_found(self, tmp_path: Path) -> None:
        """Loader raises if YAML file doesn't exist."""
        with pytest.raises(ProblemLoaderError, match="not found"):
            ProblemLoader(tmp_path / "nonexistent.yaml")

    def test_raises_if_path_is_directory(self, tmp_path: Path) -> None:
        """Loader raises if path is a directory."""
        with pytest.raises(ProblemLoaderError, match="Not a file"):
            ProblemLoader(tmp_path)


class TestProblemLoaderLoadAll:
    def test_loads_valid_yaml(self, sample_problems_yaml: Path) -> None:
        """Loader successfully parses valid YAML."""
        loader = ProblemLoader(sample_problems_yaml)
        problems = loader.load_all()

        assert len(problems) > 0
        assert all(isinstance(p, ProblemRecord) for p in problems)

    def test_caches_results(self, sample_problems_yaml: Path) -> None:
        """Subsequent calls return cached results."""
        loader = ProblemLoader(sample_problems_yaml)
        first = loader.load_all()
        second = loader.load_all()

        assert first == second

    def test_cache_can_be_cleared(self, sample_problems_yaml: Path) -> None:
        """clear_cache() forces reload."""
        loader = ProblemLoader(sample_problems_yaml)
        loader.load_all()
        loader.clear_cache()

        assert loader._cache is None

    def test_rejects_non_list_root(self, tmp_path: Path) -> None:
        """Loader rejects YAML that isn't a list."""
        yaml_file = tmp_path / "problems.yaml"
        yaml_file.write_text("a: b\n", encoding="utf-8")

        loader = ProblemLoader(yaml_file)
        with pytest.raises(ProblemLoaderError, match="Expected list of problems"):
            loader.load_all(use_cache=False)

    def test_rejects_non_mapping_entry(self, tmp_path: Path) -> None:
        """Loader rejects list entries that aren't mappings."""
        yaml_file = tmp_path / "problems.yaml"
        yaml_file.write_text("- 1\n", encoding="utf-8")

        loader = ProblemLoader(yaml_file)
        with pytest.raises(
            ProblemLoaderError, match="Expected each problem to be a mapping"
        ):
            loader.load_all(use_cache=False)

    def test_rejects_upstream_metadata_only_format(self, tmp_path: Path) -> None:
        """Loader rejects upstream teorth/erdosproblems metadata-only format."""
        yaml_file = tmp_path / "problems.yaml"
        yaml_file.write_text(
            '- number: "6"\n  prize: "$100"\n  status:\n    state: "proved"\n',
            encoding="utf-8",
        )

        loader = ProblemLoader(yaml_file)
        with pytest.raises(ProblemLoaderError, match="Unsupported upstream"):
            loader.load_all(use_cache=False)

    def test_rejects_invalid_yaml(self, tmp_path: Path) -> None:
        """Loader rejects invalid YAML syntax."""
        yaml_file = tmp_path / "problems.yaml"
        yaml_file.write_text("- id: [1\n", encoding="utf-8")

        loader = ProblemLoader(yaml_file)
        with pytest.raises(ProblemLoaderError, match="Failed to parse YAML"):
            loader.load_all(use_cache=False)

    def test_rejects_references_not_a_list(self, tmp_path: Path) -> None:
        """Loader rejects references when not a list."""
        yaml_file = tmp_path / "problems.yaml"
        yaml_file.write_text(
            "- id: 1\n  title: Test\n  statement: X\n  status: open\n  references: {}\n",
            encoding="utf-8",
        )

        loader = ProblemLoader(yaml_file)
        with pytest.raises(ProblemLoaderError, match=r"references.*must be a list"):
            loader.load_all(use_cache=False)

    def test_rejects_reference_entry_not_a_mapping(self, tmp_path: Path) -> None:
        """Loader rejects references entries when not mappings."""
        yaml_file = tmp_path / "problems.yaml"
        yaml_file.write_text(
            "- id: 1\n  title: Test\n  statement: X\n  status: open\n  references:\n    - 1\n",
            encoding="utf-8",
        )

        loader = ProblemLoader(yaml_file)
        with pytest.raises(
            ProblemLoaderError, match="Each reference must be a mapping"
        ):
            loader.load_all(use_cache=False)


class TestProblemLoaderGetById:
    def test_returns_problem_when_found(self, sample_problems_yaml: Path) -> None:
        """get_by_id returns correct problem."""
        loader = ProblemLoader(sample_problems_yaml)
        problem = loader.get_by_id(6)

        assert problem is not None
        assert problem.id == 6

    def test_returns_none_when_not_found(self, sample_problems_yaml: Path) -> None:
        """get_by_id returns None for nonexistent ID."""
        loader = ProblemLoader(sample_problems_yaml)
        problem = loader.get_by_id(99999)

        assert problem is None


class TestProblemLoaderFilter:
    def test_filter_by_status(self, sample_problems_yaml: Path) -> None:
        """Filter by status works."""
        loader = ProblemLoader(sample_problems_yaml)
        open_problems = loader.filter(status=ProblemStatus.OPEN)

        assert all(p.status == ProblemStatus.OPEN for p in open_problems)

    def test_filter_by_prize_min(self, sample_problems_yaml: Path) -> None:
        """Filter by minimum prize works."""
        loader = ProblemLoader(sample_problems_yaml)
        big_prize = loader.filter(prize_min=1000)

        assert all(p.prize >= 1000 for p in big_prize)

    def test_filter_by_tags(self, sample_problems_yaml: Path) -> None:
        """Filter by tags matches any tag."""
        loader = ProblemLoader(sample_problems_yaml)
        number_theory = loader.filter(tags=["number theory"])

        for p in number_theory:
            assert any("number theory" in t.lower() for t in p.tags)

    def test_filter_combined(self, sample_problems_yaml: Path) -> None:
        """Multiple filters combine with AND."""
        loader = ProblemLoader(sample_problems_yaml)
        results = loader.filter(
            status=ProblemStatus.OPEN,
            prize_min=100,
        )

        for p in results:
            assert p.status == ProblemStatus.OPEN
            assert p.prize >= 100


class TestProblemLoaderFromDefault:
    def test_uses_env_var(
        self, tmp_path: Path, sample_problems_yaml: Path, monkeypatch
    ) -> None:
        """from_default() respects ERDOS_DATA_PATH env var."""
        problems_dir = tmp_path / "data"
        problems_dir.mkdir()
        yaml_file = problems_dir / "problems.yaml"
        shutil.copyfile(sample_problems_yaml, yaml_file)

        monkeypatch.setenv("ERDOS_DATA_PATH", str(problems_dir))
        loader = ProblemLoader.from_default()

        assert loader.yaml_path == yaml_file

    def test_uses_local_enriched_default(
        self, tmp_path: Path, sample_problems_yaml: Path, monkeypatch
    ) -> None:
        """from_default() falls back to ./data/problems_enriched.yaml."""
        monkeypatch.delenv("ERDOS_DATA_PATH", raising=False)
        monkeypatch.chdir(tmp_path)

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        yaml_file = data_dir / "problems_enriched.yaml"
        shutil.copyfile(sample_problems_yaml, yaml_file)

        loader = ProblemLoader.from_default()
        assert loader.yaml_path.resolve() == yaml_file.resolve()

    def test_uses_relative_upstream_path(
        self, tmp_path: Path, sample_problems_yaml: Path, monkeypatch
    ) -> None:
        """from_default() falls back to ./data/erdosproblems/data/problems.yaml."""
        monkeypatch.delenv("ERDOS_DATA_PATH", raising=False)
        monkeypatch.chdir(tmp_path)

        upstream = tmp_path / "data" / "erdosproblems" / "data"
        upstream.mkdir(parents=True)
        yaml_file = upstream / "problems.yaml"
        shutil.copyfile(sample_problems_yaml, yaml_file)

        loader = ProblemLoader.from_default()
        assert loader.yaml_path.resolve() == yaml_file.resolve()

    def test_raises_when_no_data_found(self, tmp_path: Path, monkeypatch) -> None:
        """from_default() raises when no dataset is available."""
        monkeypatch.delenv("ERDOS_DATA_PATH", raising=False)
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ProblemLoaderError, match="Could not find problems YAML"):
            ProblemLoader.from_default()


class TestProblemLoaderIterProblems:
    def test_yields_problems_lazily(self, sample_problems_yaml: Path) -> None:
        """iter_problems yields without loading all into memory."""
        loader = ProblemLoader(sample_problems_yaml)

        first = next(loader.iter_problems())

        assert isinstance(first, ProblemRecord)
        assert loader._cache is None
