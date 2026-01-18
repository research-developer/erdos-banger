"""Unit tests for LeanRunner."""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from erdos.core.lean_runner import LeanRunner, LeanRunnerError


if TYPE_CHECKING:
    from pathlib import Path


class TestLeanRunnerInit:
    def test_raises_if_path_not_found(self, tmp_path: Path) -> None:
        """Raises if project path doesn't exist."""
        with pytest.raises(LeanRunnerError, match="not found"):
            LeanRunner(tmp_path / "nonexistent")

    def test_init_raises_on_lake_update_timeout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runner = LeanRunner(tmp_path)
        monkeypatch.setattr(
            shutil,
            "which",
            lambda name: "/usr/bin/lake" if name == "lake" else None,
        )

        def fake_run(*args: object, **kwargs: object) -> object:
            raise subprocess.TimeoutExpired(cmd=["lake", "update"], timeout=600)

        monkeypatch.setattr(subprocess, "run", fake_run)

        with pytest.raises(LeanRunnerError, match="timed out"):
            runner.init(fetch_mathlib=True)


class TestLeanRunnerParseErrors:
    def test_parses_single_error(self) -> None:
        """Parses a single Lean error."""
        runner = LeanRunner.__new__(LeanRunner)
        stderr = "Erdos/Problem006.lean:12:5: error: unknown identifier 'Nat.prime'"

        errors = runner._parse_errors(stderr, "test.lean")

        assert len(errors) == 1
        assert errors[0].file == "Erdos/Problem006.lean"
        assert errors[0].line == 12
        assert errors[0].column == 5
        assert "unknown identifier" in errors[0].message
        assert errors[0].severity == "error"

    def test_parses_multiple_errors(self) -> None:
        """Parses multiple errors."""
        runner = LeanRunner.__new__(LeanRunner)
        stderr = """Erdos/Test.lean:10:1: error: first error
Erdos/Test.lean:20:5: warning: some warning"""

        errors = runner._parse_errors(stderr, "test.lean")

        assert len(errors) == 2
        assert errors[0].severity == "error"
        assert errors[1].severity == "warning"

    def test_handles_multiline_message(self) -> None:
        """Parses error with multiline message."""
        runner = LeanRunner.__new__(LeanRunner)
        stderr = """Erdos/Test.lean:10:1: error: type mismatch
  has type
    Nat
  but is expected to have type
    Prop"""

        errors = runner._parse_errors(stderr, "test.lean")

        assert len(errors) == 1
        assert "type mismatch" in errors[0].message

    def test_handles_empty_stderr(self) -> None:
        """Empty stderr produces no errors."""
        runner = LeanRunner.__new__(LeanRunner)
        errors = runner._parse_errors("", "test.lean")
        assert errors == []

    def test_parses_type_error_fixture(self, fixtures_dir: Path) -> None:
        """Parses a golden type-error sample from fixtures."""
        runner = LeanRunner.__new__(LeanRunner)
        stderr = (fixtures_dir / "lean_outputs" / "type_error.txt").read_text(
            encoding="utf-8"
        )

        errors = runner._parse_errors(stderr, "hint.lean")

        assert [e.severity for e in errors] == ["error", "error"]
        assert errors[0].file == "Erdos/Problem006.lean"
        assert errors[0].line == 12
        assert "type mismatch" in errors[0].message
        assert errors[1].file == "Erdos/Problem006.lean"
        assert errors[1].line == 15
        assert "unknown identifier" in errors[1].message

    def test_parses_sorry_warning_fixture(self, fixtures_dir: Path) -> None:
        """Parses a golden sorry-warning sample from fixtures."""
        runner = LeanRunner.__new__(LeanRunner)
        stderr = (fixtures_dir / "lean_outputs" / "sorry_warning.txt").read_text(
            encoding="utf-8"
        )

        errors = runner._parse_errors(stderr, "hint.lean")

        assert len(errors) == 1
        assert errors[0].severity == "warning"
        assert "sorry" in errors[0].message


class TestLeanRunnerCheckEnvironment:
    def test_returns_environment_info(self, tmp_path: Path) -> None:
        """check_environment returns LeanEnvironment."""
        (tmp_path / "lakefile.lean").write_text("-- minimal", encoding="utf-8")
        runner = LeanRunner(tmp_path)

        env = runner.check_environment()

        assert env.project_path == tmp_path
        assert isinstance(env.elan_installed, bool)
        assert isinstance(env.lean_version, str)
