"""Paths centralization: relative defaults must resolve under the data home."""

from pathlib import Path

import pytest


@pytest.fixture
def home(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("ERDOS_HOME", str(tmp_path))
    return tmp_path.resolve()


def test_run_log_path_under_home(home: Path) -> None:
    from erdos.core.config import AppConfig

    assert AppConfig.from_env().run_log_path == home / "logs" / "runs.jsonl"


def test_run_log_path_default_construction_under_home(home: Path) -> None:
    from erdos.core.config import AppConfig

    assert AppConfig().run_log_path == home / "logs" / "runs.jsonl"


def test_search_index_default_under_home(home: Path, monkeypatch) -> None:
    monkeypatch.delenv("ERDOS_INDEX_PATH", raising=False)
    from erdos.core.search.facade import SearchIndex

    idx = SearchIndex.from_default()
    assert Path(idx.db_path) == home / "index" / "erdos.sqlite"


def test_submodule_default_under_home(home: Path, monkeypatch) -> None:
    monkeypatch.delenv("ERDOS_SUBMODULE_PATH", raising=False)
    from erdos.core.sync.submodule import get_submodule_path

    assert get_submodule_path() == home / "data" / "erdosproblems"
