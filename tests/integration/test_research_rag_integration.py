"""Integration tests for research ↔ RAG/search integration (Spec 025)."""

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

    index_dir = tmp_path / "index"
    index_dir.mkdir()
    index_path = index_dir / "erdos.sqlite"

    return {
        "ERDOS_DATA_PATH": str(data_dir),
        "ERDOS_INDEX_PATH": str(index_path),
        "ERDOS_REPO_ROOT": str(tmp_path),
    }


def test_ask_includes_synthesis_baseline_without_index_build(
    tmp_path: Path, sample_problems_yaml: Path
) -> None:
    env = _setup_env(tmp_path, sample_problems_yaml)
    init = runner.invoke(app, ["--json", "research", "init", "6"], env=env)
    assert init.exit_code == 0

    synthesis_path = tmp_path / "research" / "problems" / "0006" / "SYNTHESIS.md"
    marker = "SYNTHESIS_MARKER_zzzz1234"
    synthesis_path.write_text(f"# Synthesis\n\n{marker}\n", encoding="utf-8")

    # No --build-index on purpose.
    ask = runner.invoke(app, ["--json", "ask", "6", "test", "--no-llm"], env=env)
    assert ask.exit_code == 0, ask.stdout

    payload = json.loads(ask.stdout)
    sources = payload["data"]["sources"]
    assert any(s["source_type"] == "research_synthesis" for s in sources)
    assert any(marker in (s.get("text") or "") for s in sources)


def test_search_build_index_indexes_research_records(
    tmp_path: Path, sample_problems_yaml: Path
) -> None:
    env = _setup_env(tmp_path, sample_problems_yaml)
    init = runner.invoke(app, ["--json", "research", "init", "6"], env=env)
    assert init.exit_code == 0

    unique = "UNIQUE_LEAD_MARKER_zzzz9999"
    add = runner.invoke(
        app,
        [
            "--json",
            "research",
            "lead",
            "add",
            "6",
            "--title",
            "Test",
            "--notes",
            unique,
        ],
        env=env,
    )
    assert add.exit_code == 0, add.stdout

    # Build index and search for the unique marker.
    search = runner.invoke(
        app,
        ["--json", "search", unique, "--build-index", "--problem", "6"],
        env=env,
    )
    assert search.exit_code == 0, search.stdout
    payload = json.loads(search.stdout)
    results = payload["data"]["results"]
    assert any(r.get("source_type") == "research_lead" for r in results)
