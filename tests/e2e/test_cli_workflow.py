"""End-to-end tests for core CLI workflows (DEBT-108)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.mark.e2e
def test_no_network_workflow_creates_index_research_and_logs(
    cli_runner, tmp_path: Path
) -> None:
    """Run a representative offline workflow across real subprocess invocations."""
    listed = cli_runner("--json", "list", "--limit", "1")
    list_payload = json.loads(listed.stdout)
    assert list_payload["success"] is True
    assert list_payload["command"] == "erdos list"
    assert isinstance(list_payload["data"], list)
    assert len(list_payload["data"]) == 1

    searched = cli_runner("--json", "search", "prime", "--build-index", "--limit", "1")
    search_payload = json.loads(searched.stdout)
    assert search_payload["success"] is True
    assert search_payload["command"] == "erdos search"

    db_path = tmp_path / "index" / "erdos.sqlite"
    assert db_path.exists()

    asked = cli_runner("--json", "ask", "6", "What is known?", "--no-llm")
    ask_payload = json.loads(asked.stdout)
    assert ask_payload["success"] is True
    assert ask_payload["command"] == "erdos ask"
    assert ask_payload["data"]["problem_id"] == 6
    assert ask_payload["data"]["answer"] is None
    assert ask_payload["data"]["sources"]

    initialized = cli_runner("--json", "research", "init", "6")
    init_payload = json.loads(initialized.stdout)
    assert init_payload["success"] is True
    problem_dir = Path(init_payload["data"]["problem_dir"])
    assert problem_dir.exists()

    noted = cli_runner("--json", "research", "note", "6", "e2e scratchpad entry")
    note_payload = json.loads(noted.stdout)
    assert note_payload["success"] is True
    assert Path(note_payload["data"]["scratchpad_path"]).exists()

    status = cli_runner("--json", "research", "status", "6")
    status_payload = json.loads(status.stdout)
    assert status_payload["success"] is True
    assert status_payload["data"]["counts"]["scratchpad_entries"] >= 1

    synthesized = cli_runner("--json", "research", "synthesize", "6")
    synth_payload = json.loads(synthesized.stdout)
    assert synth_payload["success"] is True
    assert Path(synth_payload["data"]["synthesis_path"]).exists()

    log_path = tmp_path / "logs" / "runs.jsonl"
    assert log_path.exists()

    logs = cli_runner("--json", "logs", "--limit", "50")
    logs_payload = json.loads(logs.stdout)
    assert logs_payload["success"] is True
    assert logs_payload["command"] == "erdos logs"
    assert logs_payload["data"]["entries"]
    commands = {e["command"] for e in logs_payload["data"]["entries"]}
    assert "erdos ask" in commands


@pytest.mark.e2e
def test_graceful_failures_without_paid_api_keys(cli_runner, tmp_path: Path) -> None:
    """Paid/network integrations should fail with structured errors (no tracebacks)."""
    exa = cli_runner(
        "--json",
        "research",
        "exa",
        "search",
        "6",
        "test query",
        check=False,
    )
    assert exa.returncode == 10
    exa_payload = json.loads(exa.stdout)
    assert exa_payload["success"] is False
    assert exa_payload["error"]["type"] == "ConfigError"
    assert "EXA_API_KEY" in exa_payload["error"]["message"]
    assert "Traceback" not in exa.stderr

    lean_file = tmp_path / "Test.lean"
    lean_file.write_text("theorem test : True := by trivial\n", encoding="utf-8")

    prove = cli_runner(
        "--json",
        "lean",
        "prove",
        str(lean_file),
        "--output",
        str(tmp_path / "Test.out.lean"),
        check=False,
    )
    assert prove.returncode == 10
    prove_payload = json.loads(prove.stdout)
    assert prove_payload["success"] is False
    assert prove_payload["error"]["type"] == "ConfigError"
    assert "ARISTOTLE_API_KEY" in prove_payload["error"]["message"]
    assert "Traceback" not in prove.stderr
