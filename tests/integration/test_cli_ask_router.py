"""Integration tests for erdos ask command with LLM router (SPEC-032)."""

from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING

from erdos.cli import app
from erdos.core.exit_codes import ExitCode
from erdos.core.problem_loader import ProblemLoader
from erdos.core.search.facade import SearchIndex
from erdos.core.search.index_builder import build_index
from tests.cli_runner import make_cli_runner, unset_env_vars


if TYPE_CHECKING:
    from pathlib import Path


runner = make_cli_runner()


def _setup_test_env(tmp_path: Path, sample_problems_yaml: Path) -> tuple[Path, Path]:
    """Create test environment with data and index."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copyfile(sample_problems_yaml, data_dir / "problems.yaml")

    index_dir = tmp_path / "index"
    index_dir.mkdir()
    index_path = index_dir / "erdos.sqlite"

    loader = ProblemLoader(data_dir / "problems.yaml")
    index = SearchIndex(index_path)
    build_index(loader=loader, index=index)

    return data_dir, index_path


class TestAskCommandRouterIntegration:
    """Tests for erdos ask using LLM router (SPEC-032)."""

    def test_ask_uses_router_with_task_specific_env_var(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """ask command uses ERDOS_LLM_COMMAND_MATH (task-specific) via router."""
        data_dir, index_path = _setup_test_env(tmp_path, sample_problems_yaml)

        # Create a fake LLM script
        fake_llm = tmp_path / "math_llm.sh"
        fake_llm.write_text("#!/bin/bash\necho 'Math LLM response'")
        fake_llm.chmod(0o755)

        result = runner.invoke(
            app,
            ["--json", "ask", "6", "test?"],
            env={
                "ERDOS_DATA_PATH": str(data_dir),
                "ERDOS_INDEX_PATH": str(index_path),
                "ERDOS_REPO_ROOT": str(tmp_path),
                # Task-specific takes precedence
                "ERDOS_LLM_COMMAND_MATH": str(fake_llm),
                "ERDOS_LLM_COMMAND": "/should/not/be/used",
            },
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert "Math LLM response" in data["data"]["answer"]
        # Verify the task-specific command was used
        assert data["data"]["llm"]["command"] == str(fake_llm)

    def test_ask_falls_back_to_global_llm_command(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """ask command falls back to ERDOS_LLM_COMMAND when MATH not set."""
        data_dir, index_path = _setup_test_env(tmp_path, sample_problems_yaml)

        fake_llm = tmp_path / "global_llm.sh"
        fake_llm.write_text("#!/bin/bash\necho 'Global LLM response'")
        fake_llm.chmod(0o755)

        result = runner.invoke(
            app,
            ["--json", "ask", "6", "test?"],
            env={
                "ERDOS_DATA_PATH": str(data_dir),
                "ERDOS_INDEX_PATH": str(index_path),
                "ERDOS_REPO_ROOT": str(tmp_path),
                # Only global set, no MATH
                "ERDOS_LLM_COMMAND": str(fake_llm),
            },
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert "Global LLM response" in data["data"]["answer"]
        assert data["data"]["llm"]["command"] == str(fake_llm)

    def test_ask_llm_cmd_override_bypasses_router(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """--llm-cmd override bypasses router entirely."""
        data_dir, index_path = _setup_test_env(tmp_path, sample_problems_yaml)

        # Create two scripts - one for env, one for override
        env_llm = tmp_path / "env_llm.sh"
        env_llm.write_text("#!/bin/bash\necho 'ENV LLM'")
        env_llm.chmod(0o755)

        override_llm = tmp_path / "override_llm.sh"
        override_llm.write_text("#!/bin/bash\necho 'OVERRIDE LLM'")
        override_llm.chmod(0o755)

        result = runner.invoke(
            app,
            ["--json", "ask", "6", "test?", "--llm-cmd", str(override_llm)],
            env={
                "ERDOS_DATA_PATH": str(data_dir),
                "ERDOS_INDEX_PATH": str(index_path),
                "ERDOS_REPO_ROOT": str(tmp_path),
                "ERDOS_LLM_COMMAND_MATH": str(env_llm),
                "ERDOS_LLM_COMMAND": str(env_llm),
            },
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        # Override should be used, not env var
        assert "OVERRIDE LLM" in data["data"]["answer"]
        assert data["data"]["llm"]["command"] == str(override_llm)

    def test_ask_no_llm_flag_skips_router(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """--no-llm flag skips LLM entirely (no router error)."""
        data_dir, index_path = _setup_test_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "ask", "6", "test?", "--no-llm"],
            env={
                "ERDOS_DATA_PATH": str(data_dir),
                "ERDOS_INDEX_PATH": str(index_path),
                "ERDOS_REPO_ROOT": str(tmp_path),
                # No LLM command configured - but --no-llm so no error
            },
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["data"]["answer"] is None
        assert data["data"]["llm"]["enabled"] is False

    def test_ask_error_when_no_llm_command_configured(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Error when LLM enabled but no command configured (router fails)."""
        data_dir, index_path = _setup_test_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "ask", "6", "test?"],  # No --no-llm, no --llm-cmd
            env={
                "ERDOS_DATA_PATH": str(data_dir),
                "ERDOS_INDEX_PATH": str(index_path),
                "ERDOS_REPO_ROOT": str(tmp_path),
                # Explicitly unset LLM commands (may be set via .env)
                **unset_env_vars(
                    "ERDOS_LLM_COMMAND",
                    "ERDOS_LLM_COMMAND_MATH",
                    "ERDOS_LLM_COMMAND_CODE",
                ),
            },
        )

        # Should fail with CONFIG_ERROR
        assert result.exit_code == ExitCode.CONFIG_ERROR, f"Output: {result.stdout}"
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert "No LLM command configured" in data["error"]["message"]
        # Should mention what env vars to set
        assert "ERDOS_LLM_COMMAND_MATH" in data["error"]["message"]
        assert "ERDOS_LLM_COMMAND" in data["error"]["message"]

    def test_ask_error_message_mentions_task_type(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Error message mentions the task type for debugging."""
        data_dir, index_path = _setup_test_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "ask", "6", "test?"],
            env={
                "ERDOS_DATA_PATH": str(data_dir),
                "ERDOS_INDEX_PATH": str(index_path),
                "ERDOS_REPO_ROOT": str(tmp_path),
                # Explicitly unset LLM commands (may be set via .env)
                **unset_env_vars(
                    "ERDOS_LLM_COMMAND",
                    "ERDOS_LLM_COMMAND_MATH",
                    "ERDOS_LLM_COMMAND_CODE",
                ),
            },
        )

        assert result.exit_code == ExitCode.CONFIG_ERROR
        data = json.loads(result.stdout)
        # Should mention task type for debugging
        assert "ask_question" in data["error"]["message"]
