"""Integration tests for CLI commands (in-process)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from erdos.cli import app
from erdos.core.lean_runner import LeanRunner
from erdos.core.models import LeanCheckResult, LeanError
from tests.cli_runner import make_cli_runner


runner = make_cli_runner()


def _data_dir(tmp_path: Path, sample_problems_yaml: Path) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copyfile(sample_problems_yaml, data_dir / "problems.yaml")
    return data_dir


def _data_dir_with_yaml(tmp_path: Path, yaml_text: str) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "problems.yaml").write_text(yaml_text, encoding="utf-8")
    return data_dir


def test_cli_show_human(tmp_path: Path, sample_problems_yaml: Path) -> None:
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    result = runner.invoke(app, ["show", "6"], env={"ERDOS_DATA_PATH": str(data_dir)})

    assert result.exit_code == 0
    assert "Problem 6" in result.stdout


def test_cli_show_json(tmp_path: Path, sample_problems_yaml: Path) -> None:
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    result = runner.invoke(
        app, ["--json", "show", "6"], env={"ERDOS_DATA_PATH": str(data_dir)}
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["command"] == "erdos show"
    assert data["success"] is True


def test_cli_list_json(tmp_path: Path, sample_problems_yaml: Path) -> None:
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    result = runner.invoke(
        app, ["--json", "list", "--limit", "2"], env={"ERDOS_DATA_PATH": str(data_dir)}
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["command"] == "erdos list"
    assert data["success"] is True
    assert len(data["data"]) <= 2


def test_cli_list_human(tmp_path: Path, sample_problems_yaml: Path) -> None:
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    result = runner.invoke(
        app, ["list", "--limit", "2"], env={"ERDOS_DATA_PATH": str(data_dir)}
    )

    assert result.exit_code == 0
    assert "Erdős Problems" in result.stdout


def test_cli_list_error_human(tmp_path: Path) -> None:
    data_dir = _data_dir_with_yaml(tmp_path, "a: b\n")
    result = runner.invoke(
        app, ["list", "--limit", "1"], env={"ERDOS_DATA_PATH": str(data_dir)}
    )

    assert result.exit_code == 1
    assert "Error:" in result.stderr


def test_cli_refs_json(tmp_path: Path, sample_problems_yaml: Path) -> None:
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    result = runner.invoke(
        app, ["--json", "refs", "6"], env={"ERDOS_DATA_PATH": str(data_dir)}
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["command"] == "erdos refs"
    assert data["data"]["problem_id"] == 6


def test_cli_refs_human(tmp_path: Path, sample_problems_yaml: Path) -> None:
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    result = runner.invoke(app, ["refs", "6"], env={"ERDOS_DATA_PATH": str(data_dir)})

    assert result.exit_code == 0
    assert "References for Problem" in result.stdout


def test_cli_refs_not_found_human(tmp_path: Path, sample_problems_yaml: Path) -> None:
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    result = runner.invoke(
        app, ["refs", "99999"], env={"ERDOS_DATA_PATH": str(data_dir)}
    )

    assert result.exit_code == 3
    assert "Error:" in result.stderr


def test_cli_search_json(tmp_path: Path, sample_problems_yaml: Path) -> None:
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    index_path = tmp_path / "index" / "test.sqlite"
    result = runner.invoke(
        app,
        ["--json", "search", "prime"],
        env={"ERDOS_DATA_PATH": str(data_dir), "ERDOS_INDEX_PATH": str(index_path)},
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["command"] == "erdos search"
    assert data["success"] is True
    # Check new data structure
    assert "data" in data
    assert "query" in data["data"]


def test_cli_search_human(tmp_path: Path, sample_problems_yaml: Path) -> None:
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    index_path = tmp_path / "index" / "test.sqlite"
    result = runner.invoke(
        app,
        ["search", "prime"],
        env={"ERDOS_DATA_PATH": str(data_dir), "ERDOS_INDEX_PATH": str(index_path)},
    )

    assert result.exit_code == 0
    # New format uses "Search results for:" instead of table
    assert "Search results for:" in result.stdout or "No results for:" in result.stdout


def test_cli_search_empty_query_error(
    tmp_path: Path, sample_problems_yaml: Path
) -> None:
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    index_path = tmp_path / "index" / "test.sqlite"
    result = runner.invoke(
        app,
        ["search", ""],
        env={"ERDOS_DATA_PATH": str(data_dir), "ERDOS_INDEX_PATH": str(index_path)},
    )

    # Empty query in basic search returns error code 2
    # But if index exists and is empty, it falls back to basic search
    assert result.exit_code == 2 or "Query must not be empty" in str(result.stderr)


def test_cli_search_build_index_json_output_is_clean(
    tmp_path: Path, sample_problems_yaml: Path
) -> None:
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    index_path = tmp_path / "index" / "test.sqlite"
    result = runner.invoke(
        app,
        ["--json", "search", "prime", "--build-index"],
        env={"ERDOS_DATA_PATH": str(data_dir), "ERDOS_INDEX_PATH": str(index_path)},
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "erdos search"
    assert payload["success"] is True

    # Progress/logging must not contaminate JSON on stdout.
    assert "Building search index" not in result.stdout
    assert "Building search index" in result.stderr


def test_cli_search_fts_works_without_dataset_when_index_exists(
    tmp_path: Path, sample_problems_yaml: Path, monkeypatch
) -> None:
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    index_path = tmp_path / "index" / "test.sqlite"

    # Build index while dataset is present.
    build = runner.invoke(
        app,
        ["search", "prime", "--build-index"],
        env={"ERDOS_DATA_PATH": str(data_dir), "ERDOS_INDEX_PATH": str(index_path)},
    )
    assert build.exit_code == 0

    # Remove dataset and run from an isolated cwd so the loader can't fall back
    # to repository-local data paths.
    shutil.rmtree(data_dir)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["--json", "search", "prime"],
        env={"ERDOS_INDEX_PATH": str(index_path)},
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "erdos search"
    assert payload["success"] is True
    assert payload["data"]["use_fts"] is True
    assert payload["data"]["count"] > 0
    assert all(isinstance(r.get("title"), str) for r in payload["data"]["results"])


def test_cli_lean_init_no_mathlib_human(tmp_path: Path) -> None:
    project_path = tmp_path / "formal" / "lean"
    project_path.mkdir(parents=True)

    result = runner.invoke(
        app,
        ["lean", "init", "--no-mathlib", "--path", str(project_path)],
        env={},
    )

    assert result.exit_code == 0
    assert "Initialized Lean project" in result.stdout


def test_cli_lean_init_no_mathlib_json(tmp_path: Path) -> None:
    project_path = tmp_path / "formal" / "lean"
    project_path.mkdir(parents=True)

    result = runner.invoke(
        app,
        ["--json", "lean", "init", "--no-mathlib", "--path", str(project_path)],
        env={},
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["command"] == "erdos lean init"
    assert data["success"] is True
    assert data["data"]["project_path"] == str(project_path)


def test_cli_lean_formalize_success_json(
    tmp_path: Path, sample_problems_yaml: Path
) -> None:
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    project_path = tmp_path / "formal" / "lean"
    project_path.mkdir(parents=True)

    init = runner.invoke(
        app,
        ["lean", "init", "--no-mathlib", "--path", str(project_path)],
        env={},
    )
    assert init.exit_code == 0

    result = runner.invoke(
        app,
        ["--json", "lean", "formalize", "6", "--path", str(project_path)],
        env={"ERDOS_DATA_PATH": str(data_dir)},
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "erdos lean formalize"
    assert payload["success"] is True
    output_file = Path(payload["data"]["file"])
    assert output_file.exists()
    assert "Problem 6" in output_file.read_text(encoding="utf-8")


def test_cli_lean_formalize_not_found(
    tmp_path: Path, sample_problems_yaml: Path
) -> None:
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    result = runner.invoke(
        app, ["lean", "formalize", "99999"], env={"ERDOS_DATA_PATH": str(data_dir)}
    )

    assert result.exit_code == 3
    assert "Error:" in result.stderr


def test_cli_lean_check_success_and_failure(monkeypatch, tmp_path: Path) -> None:
    file_path = tmp_path / "Test.lean"
    file_path.write_text("-- test\n", encoding="utf-8")

    def fake_check_ok(self, file_path: Path) -> LeanCheckResult:
        return LeanCheckResult(file=file_path.name, success=True)

    def fake_check_fail(self, file_path: Path) -> LeanCheckResult:
        return LeanCheckResult(
            file=file_path.name,
            success=False,
            errors=[
                LeanError(
                    file=file_path.name, line=1, column=1, message="type mismatch"
                ),
            ],
        )

    monkeypatch.setattr(LeanRunner, "check", fake_check_ok)
    ok = runner.invoke(app, ["lean", "check", str(file_path)], env={})
    assert ok.exit_code == 0
    assert "compiled successfully" in ok.stdout

    monkeypatch.setattr(LeanRunner, "check", fake_check_fail)
    bad = runner.invoke(app, ["lean", "check", str(file_path)], env={})
    assert bad.exit_code == 5
    # Rich may wrap output; normalize whitespace for assertion
    normalized = " ".join(bad.stdout.split())
    assert "has 1 error" in normalized


def test_cli_lean_check_json_success(monkeypatch, tmp_path: Path) -> None:
    file_path = tmp_path / "Test.lean"
    file_path.write_text("-- test\n", encoding="utf-8")

    def fake_check_ok(self, file_path: Path) -> LeanCheckResult:
        return LeanCheckResult(file=file_path.name, success=True)

    monkeypatch.setattr(LeanRunner, "check", fake_check_ok)

    result = runner.invoke(app, ["--json", "lean", "check", str(file_path)], env={})

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "erdos lean check"
    assert payload["success"] is True
    assert payload["data"]["success"] is True
