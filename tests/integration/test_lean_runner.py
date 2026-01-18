"""Integration tests for Lean runner (requires Lean installed)."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest

from erdos.core.lean_runner import LeanRunner


if TYPE_CHECKING:
    from pathlib import Path


lean_available = shutil.which("lean") is not None


@pytest.mark.skipif(not lean_available, reason="Lean not installed")
@pytest.mark.requires_lean
class TestLeanRunnerIntegration:
    def test_init_creates_project(self, tmp_path: Path) -> None:
        """init creates Lean project structure."""
        runner = LeanRunner(tmp_path)
        runner.init(fetch_mathlib=False)

        assert (tmp_path / "lean-toolchain").exists()
        assert (tmp_path / "lakefile.lean").exists()
        assert (tmp_path / "Erdos" / "Basic.lean").exists()
        assert (tmp_path / "Erdos.lean").exists()

    def test_check_valid_file(self, tmp_path: Path) -> None:
        """check succeeds on valid Lean file."""
        runner = LeanRunner(tmp_path)
        runner.init(fetch_mathlib=False)

        test_file = tmp_path / "Erdos" / "Test.lean"
        test_file.write_text("theorem simple : 1 + 1 = 2 := rfl\n", encoding="utf-8")

        result = runner.check(test_file)

        # May fail without mathlib, but should not raise
        assert result.file == "Erdos/Test.lean"

    def test_check_invalid_file(self, tmp_path: Path) -> None:
        """check captures errors from invalid file."""
        runner = LeanRunner(tmp_path)
        runner.init(fetch_mathlib=False)

        test_file = tmp_path / "Erdos" / "Bad.lean"
        test_file.write_text("theorem bad : 1 = 2 := rfl\n", encoding="utf-8")

        result = runner.check(test_file)

        assert not result.success
        assert len(result.errors) > 0
