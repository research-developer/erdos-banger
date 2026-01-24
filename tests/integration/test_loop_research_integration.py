"""Integration tests for loop → research integration (Spec 027)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from erdos.cli import app
from tests.cli_runner import make_cli_runner


runner = make_cli_runner()

# Check if lake is available for skipping tests
lake_available = shutil.which("lake") is not None


def _setup_env(tmp_path: Path, sample_problems_yaml: Path) -> dict[str, str]:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copyfile(sample_problems_yaml, data_dir / "problems.yaml")
    return {"ERDOS_DATA_PATH": str(data_dir), "ERDOS_REPO_ROOT": str(tmp_path)}


@pytest.mark.skipif(not lake_available, reason="lake not found (Lean not installed)")
@pytest.mark.requires_lean
def test_loop_writes_attempt_record(tmp_path: Path, sample_problems_yaml: Path) -> None:
    env = _setup_env(tmp_path, sample_problems_yaml)

    # Create fake LLM script that outputs a Lean response (SPEC-032 requires configured LLM)
    fake_llm = tmp_path / "fake_llm.sh"
    fake_llm.write_text(
        "#!/bin/bash\n"
        "echo '```lean'\n"
        "echo 'theorem foo : True := trivial'\n"
        "echo '```'\n"
    )
    fake_llm.chmod(0o755)
    env["ERDOS_LLM_COMMAND"] = str(fake_llm)

    # Minimal Lean file with sorry so loop tries to fix it.
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
            "--no-apply",  # Don't apply patches, just run the loop
            "--max-iter",
            "1",  # Single iteration to keep test fast
            "--path",
            str(tmp_path / "formal" / "lean"),
        ],
        env=env,
    )
    # Loop may succeed or fail depending on LLM output, but should run
    payload = json.loads(result.stdout)
    assert payload["command"] == "erdos loop"

    attempts_dir = tmp_path / "research" / "problems" / "0006" / "attempts"
    attempt_files = sorted(attempts_dir.glob("att_*.yaml"))
    assert attempt_files, "Expected at least one attempt record to be written"
    text = attempt_files[-1].read_text(encoding="utf-8")
    assert "kind: lean_loop" in text
    assert "loop_run_log:" in text
