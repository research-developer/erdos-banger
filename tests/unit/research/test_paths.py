from __future__ import annotations

from pathlib import Path

from erdos.core.research.paths import get_problem_dir, get_research_root


def test_get_research_root_respects_repo_root(tmp_path: Path) -> None:
    assert get_research_root(tmp_path) == tmp_path.resolve() / "research"


def test_get_research_root_defaults_to_cwd(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert get_research_root(None) == tmp_path.resolve() / "research"


def test_get_problem_dir_formatting(tmp_path: Path) -> None:
    assert get_problem_dir(tmp_path, 6) == (
        tmp_path.resolve() / "research" / "problems" / "0006"
    )
