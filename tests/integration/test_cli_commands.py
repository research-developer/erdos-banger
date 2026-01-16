"""Integration tests for CLI commands (in-process)."""

from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING

from typer.testing import CliRunner

from erdos.cli import app
from erdos.commands import lean as lean_cmd
from erdos.core.models import LeanCheckResult, LeanError


if TYPE_CHECKING:
    from pathlib import Path


runner = CliRunner()


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
        app, ["show", "6", "--json"], env={"ERDOS_DATA_PATH": str(data_dir)}
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["command"] == "erdos show"
    assert data["success"] is True


def test_cli_list_json(tmp_path: Path, sample_problems_yaml: Path) -> None:
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    result = runner.invoke(
        app, ["list", "--limit", "2", "--json"], env={"ERDOS_DATA_PATH": str(data_dir)}
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
        app, ["refs", "6", "--json"], env={"ERDOS_DATA_PATH": str(data_dir)}
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
    result = runner.invoke(
        app, ["search", "prime", "--json"], env={"ERDOS_DATA_PATH": str(data_dir)}
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["command"] == "erdos search"
    assert data["success"] is True


def test_cli_search_human(tmp_path: Path, sample_problems_yaml: Path) -> None:
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    result = runner.invoke(
        app, ["search", "prime"], env={"ERDOS_DATA_PATH": str(data_dir)}
    )

    assert result.exit_code == 0
    assert "Search Results" in result.stdout


def test_cli_search_empty_query_error(
    tmp_path: Path, sample_problems_yaml: Path
) -> None:
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    result = runner.invoke(app, ["search", ""], env={"ERDOS_DATA_PATH": str(data_dir)})

    assert result.exit_code == 2
    assert "Error:" in result.stderr


def test_cli_lean_init_not_implemented(tmp_path: Path) -> None:
    result = runner.invoke(app, ["lean", "init"], env={})

    assert result.exit_code == 1
    assert "Feature not yet implemented" in result.stderr


def test_cli_lean_init_json_not_implemented(tmp_path: Path) -> None:
    result = runner.invoke(app, ["lean", "init", "--json"], env={})

    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["command"] == "erdos lean init"
    assert data["success"] is False


def test_cli_lean_check_not_implemented(tmp_path: Path) -> None:
    file_path = tmp_path / "Test.lean"
    file_path.write_text("-- test\n", encoding="utf-8")

    result = runner.invoke(app, ["lean", "check", str(file_path)], env={})

    assert result.exit_code == 1
    assert "Feature not yet implemented" in result.stderr


def test_cli_lean_check_json_not_implemented(tmp_path: Path) -> None:
    file_path = tmp_path / "Test.lean"
    file_path.write_text("-- test\n", encoding="utf-8")

    result = runner.invoke(app, ["lean", "check", str(file_path), "--json"], env={})

    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["command"] == "erdos lean check"
    assert data["success"] is False


def test_cli_lean_formalize_not_implemented(
    tmp_path: Path, sample_problems_yaml: Path
) -> None:
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    result = runner.invoke(
        app, ["lean", "formalize", "6"], env={"ERDOS_DATA_PATH": str(data_dir)}
    )

    assert result.exit_code == 1
    assert "Feature not yet implemented" in result.stderr


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
        return LeanCheckResult(file=str(file_path), success=True)

    def fake_check_fail(self, file_path: Path) -> LeanCheckResult:
        return LeanCheckResult(
            file=str(file_path),
            success=False,
            errors=[
                LeanError(
                    file=str(file_path), line=1, column=1, message="type mismatch"
                ),
            ],
        )

    monkeypatch.setattr(lean_cmd.LeanRunner, "check", fake_check_ok)
    ok = runner.invoke(app, ["lean", "check", str(file_path)], env={})
    assert ok.exit_code == 0
    assert "compiled successfully" in ok.stdout

    monkeypatch.setattr(lean_cmd.LeanRunner, "check", fake_check_fail)
    bad = runner.invoke(app, ["lean", "check", str(file_path)], env={})
    assert bad.exit_code == 5
    assert "has 1 error" in bad.stdout


def test_cli_lean_init_and_formalize_success(
    monkeypatch, tmp_path: Path, sample_problems_yaml: Path
) -> None:
    def fake_init(self) -> None:
        return None

    def fake_generate(problem, project_path: Path) -> Path:
        out = project_path / "Erdos" / f"Problem{problem.id:03d}.lean"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("-- skeleton\n", encoding="utf-8")
        return out

    monkeypatch.setattr(lean_cmd.LeanRunner, "init", fake_init)
    init = runner.invoke(app, ["lean", "init"], env={})
    assert init.exit_code == 0
    assert "initialized" in init.stdout.lower()

    monkeypatch.setattr(lean_cmd, "generate_skeleton", fake_generate)
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    project_path = tmp_path / "formal" / "lean"
    formalize = runner.invoke(
        app,
        ["lean", "formalize", "6", "--json", "--path", str(project_path)],
        env={"ERDOS_DATA_PATH": str(data_dir)},
    )
    assert formalize.exit_code == 0
    payload = json.loads(formalize.stdout)
    assert payload["command"] == "erdos lean formalize"
    assert payload["success"] is True
