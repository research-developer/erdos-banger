"""Integration tests for deterministic synthesis (Spec 026)."""

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
    return {"ERDOS_DATA_PATH": str(data_dir), "ERDOS_REPO_ROOT": str(tmp_path)}


def test_research_synthesize_writes_file(
    tmp_path: Path, sample_problems_yaml: Path
) -> None:
    env = _setup_env(tmp_path, sample_problems_yaml)
    init = runner.invoke(app, ["--json", "research", "init", "6"], env=env)
    assert init.exit_code == 0

    synth = runner.invoke(app, ["--json", "research", "synthesize", "6"], env=env)
    assert synth.exit_code == 0, synth.stdout
    payload = json.loads(synth.stdout)
    assert payload["command"] == "erdos research synthesize"
    assert payload["success"] is True
    assert payload["data"]["problem_id"] == 6
    assert (tmp_path / "research" / "problems" / "0006" / "SYNTHESIS.md").exists()
