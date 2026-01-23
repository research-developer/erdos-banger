"""Integration tests for loop → research integration (Spec 027)."""

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


def test_loop_writes_attempt_record(tmp_path: Path, sample_problems_yaml: Path) -> None:
    env = _setup_env(tmp_path, sample_problems_yaml)

    # Minimal Lean file with sorry so loop exits early with LLM_REQUIRED (no lake needed).
    lean_dir = tmp_path / "formal" / "lean" / "Erdos"
    lean_dir.mkdir(parents=True)
    (lean_dir / "Problem006.lean").write_text(
        "theorem foo : True := sorry\n", encoding="utf-8"
    )

    result = runner.invoke(
        app,
        [
            "--json",
            "loop",
            "run",
            "6",
            "--no-apply",
            "--path",
            str(tmp_path / "formal" / "lean"),
        ],
        env=env,
    )
    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "erdos loop"

    attempts_dir = tmp_path / "research" / "problems" / "0006" / "attempts"
    attempt_files = sorted(attempts_dir.glob("att_*.yaml"))
    assert attempt_files, "Expected at least one attempt record to be written"
    text = attempt_files[-1].read_text(encoding="utf-8")
    assert "kind: lean_loop" in text
    assert "loop_run_log:" in text
