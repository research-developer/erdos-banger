"""Unit tests for sync dataset helpers (SPEC-035)."""

from __future__ import annotations

from pathlib import Path

import yaml

from erdos.core.config import AppConfig
from erdos.core.models import ProblemRecord, ProblemStatus
from erdos.core.sync.dataset import (
    load_enriched_problems,
    resolve_enriched_dataset_path,
    resolve_sync_cache_dir,
    save_enriched_problems,
)


class TestLoadEnrichedProblems:
    """Tests for loading enriched problems YAML."""

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """Missing dataset file should return an empty dict."""
        assert load_enriched_problems(tmp_path / "missing.yaml") == {}

    def test_invalid_root_type_returns_empty(self, tmp_path: Path) -> None:
        """Non-list YAML root should return an empty dict."""
        path = tmp_path / "problems.yaml"
        path.write_text(yaml.dump({"not": "a list"}), encoding="utf-8")
        assert load_enriched_problems(path) == {}

    def test_skips_invalid_entries_and_loads_valid(self, tmp_path: Path) -> None:
        """Loader should skip malformed entries and keep valid ProblemRecords."""
        path = tmp_path / "problems.yaml"
        data = [
            "not a dict",
            {"title": "missing id", "statement": "s", "status": "open"},
            {"id": 1, "title": "", "statement": "s", "status": "open"},  # invalid
            {"id": 2, "title": "T2", "statement": "S2", "status": "open"},
        ]
        path.write_text(yaml.dump(data), encoding="utf-8")

        problems = load_enriched_problems(path)
        assert set(problems.keys()) == {2}
        assert problems[2].title == "T2"


class TestSaveEnrichedProblems:
    """Tests for saving enriched problems YAML."""

    def test_saves_sorted_by_id(self, tmp_path: Path) -> None:
        """Saved YAML should be a list sorted by problem id ascending."""
        path = tmp_path / "problems_enriched.yaml"
        problems = {
            2: ProblemRecord(
                id=2, title="T2", statement="S2", status=ProblemStatus.OPEN
            ),
            1: ProblemRecord(
                id=1, title="T1", statement="S1", status=ProblemStatus.OPEN
            ),
        }
        save_enriched_problems(path, problems)

        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(loaded, list)
        assert [item["id"] for item in loaded] == [1, 2]


class TestResolveDatasetPaths:
    """Tests for dataset and cache directory resolution helpers."""

    def test_defaults_to_repo_root_data_file(self, tmp_path: Path) -> None:
        """When data_path is unset, use <repo_root>/data/problems_enriched.yaml."""
        config = AppConfig(repo_root=tmp_path)
        assert (
            resolve_enriched_dataset_path(config)
            == tmp_path / "data" / "problems_enriched.yaml"
        )

    def test_directory_prefers_existing_dataset_file(self, tmp_path: Path) -> None:
        """Directory data_path should choose problems_enriched.yaml if present."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "problems_enriched.yaml").write_text("[]\n", encoding="utf-8")
        config = AppConfig(repo_root=tmp_path, data_path=data_dir)
        assert (
            resolve_enriched_dataset_path(config) == data_dir / "problems_enriched.yaml"
        )

    def test_directory_falls_back_to_problems_yaml(self, tmp_path: Path) -> None:
        """Directory data_path should choose problems.yaml if enriched file missing."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "problems.yaml").write_text("[]\n", encoding="utf-8")
        config = AppConfig(repo_root=tmp_path, data_path=data_dir)
        assert resolve_enriched_dataset_path(config) == data_dir / "problems.yaml"

    def test_relative_file_path_is_resolved_against_repo_root(
        self, tmp_path: Path
    ) -> None:
        """Relative file paths are resolved against repo_root."""
        config = AppConfig(repo_root=tmp_path, data_path=Path("custom.yaml"))
        assert resolve_enriched_dataset_path(config) == tmp_path / "custom.yaml"

    def test_sync_cache_dir_is_under_dataset_parent(self, tmp_path: Path) -> None:
        """Sync cache directory should be adjacent to the dataset file."""
        dataset_path = tmp_path / "data" / "problems_enriched.yaml"
        assert resolve_sync_cache_dir(dataset_path) == tmp_path / "data" / "sync_cache"
