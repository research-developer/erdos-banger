"""Integration tests for `erdos research` (Spec 023)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from erdos.cli import app
from tests.cli_runner import make_cli_runner


runner = make_cli_runner()


def _setup_env(tmp_path: Path, sample_problems_yaml: Path) -> dict[str, str]:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copyfile(sample_problems_yaml, data_dir / "problems.yaml")

    return {
        "ERDOS_DATA_PATH": str(data_dir),
        "ERDOS_REPO_ROOT": str(tmp_path),
    }


def test_research_init_creates_workspace(
    tmp_path: Path, sample_problems_yaml: Path
) -> None:
    env = _setup_env(tmp_path, sample_problems_yaml)
    result = runner.invoke(app, ["--json", "research", "init", "6"], env=env)
    assert result.exit_code == 0, result.stdout

    payload = json.loads(result.stdout)
    assert payload["command"] == "erdos research init"
    assert payload["success"] is True
    assert payload["data"]["problem_id"] == 6
    assert payload["data"]["workspace_version"] == 1
    assert (tmp_path / "research" / "VERSION").exists()
    assert (tmp_path / "research" / "problems" / "0006" / "SCRATCHPAD.md").exists()


def test_research_note_appends(tmp_path: Path, sample_problems_yaml: Path) -> None:
    env = _setup_env(tmp_path, sample_problems_yaml)
    init = runner.invoke(app, ["--json", "research", "init", "6"], env=env)
    assert init.exit_code == 0

    note = runner.invoke(
        app, ["--json", "research", "note", "6", "hello world"], env=env
    )
    assert note.exit_code == 0
    payload = json.loads(note.stdout)
    assert payload["command"] == "erdos research note"
    assert payload["success"] is True
    assert payload["data"]["problem_id"] == 6

    scratchpad = (
        tmp_path / "research" / "problems" / "0006" / "SCRATCHPAD.md"
    ).read_text(encoding="utf-8")
    assert "hello world" in scratchpad


def test_research_status_requires_init(
    tmp_path: Path, sample_problems_yaml: Path
) -> None:
    env = _setup_env(tmp_path, sample_problems_yaml)
    status = runner.invoke(app, ["--json", "research", "status", "6"], env=env)
    assert status.exit_code != 0
    payload = json.loads(status.stdout)
    assert payload["command"] == "erdos research status"
    assert payload["success"] is False
    assert payload["error"]["type"] == "NotInitialized"
