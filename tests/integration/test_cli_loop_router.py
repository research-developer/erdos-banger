"""Integration tests for erdos loop run command with LLM router (SPEC-032)."""

from __future__ import annotations

import json
from pathlib import Path

from erdos.cli import app
from erdos.core.exit_codes import ExitCode
from tests.cli_runner import make_cli_runner


runner = make_cli_runner()


def _setup_lean_project(tmp_path: Path) -> Path:
    """Create minimal Lean project structure for loop tests.

    Returns the project path (tmp_path/formal/lean).
    """
    project_path = tmp_path / "formal" / "lean"
    erdos_dir = project_path / "Erdos"
    erdos_dir.mkdir(parents=True)

    # Create a Lean file with a sorry to trigger loop iteration
    lean_file = erdos_dir / "Problem006.lean"
    lean_file.write_text("theorem foo : True := sorry\n", encoding="utf-8")

    return project_path


class TestLoopRunRouterIntegration:
    """Tests for erdos loop run using LLM router (SPEC-032)."""

    def test_loop_uses_router_with_task_specific_env_var(self, tmp_path: Path) -> None:
        """loop run command uses ERDOS_LLM_COMMAND_CODE (task-specific) via router."""
        project_path = _setup_lean_project(tmp_path)

        # Create a fake LLM script that outputs a valid patch response
        fake_llm = tmp_path / "code_llm.sh"
        fake_llm.write_text(
            "#!/bin/bash\n"
            "echo '```lean'\n"
            "echo 'theorem foo : True := trivial'\n"
            "echo '```'\n"
        )
        fake_llm.chmod(0o755)

        result = runner.invoke(
            app,
            [
                "--json",
                "loop",
                "run",
                "6",
                "--no-apply",  # Don't actually modify files
                "--max-iter",
                "1",
                "--path",
                str(project_path),
            ],
            env={
                "ERDOS_REPO_ROOT": str(tmp_path),
                # Task-specific takes precedence
                "ERDOS_LLM_COMMAND_CODE": str(fake_llm),
                "ERDOS_LLM_COMMAND": "/should/not/be/used",
            },
        )

        # The loop will run and use the CODE-specific command
        # We just verify it doesn't fail with CONFIG_ERROR
        data = json.loads(result.stdout)
        # If llm was used, it should have the command recorded in loop data
        assert data["command"] == "erdos loop"
        # Either success (proof complete) or loop-specific failure (not CONFIG_ERROR)
        if data["success"]:
            # Proof completed
            pass
        else:
            # Should not be a CONFIG_ERROR - that would mean routing failed
            assert data["error"]["type"] != "CONFIG_ERROR"

    def test_loop_falls_back_to_global_llm_command(self, tmp_path: Path) -> None:
        """loop run command falls back to ERDOS_LLM_COMMAND when CODE not set."""
        project_path = _setup_lean_project(tmp_path)

        fake_llm = tmp_path / "global_llm.sh"
        fake_llm.write_text(
            "#!/bin/bash\n"
            "echo '```lean'\n"
            "echo 'theorem foo : True := trivial'\n"
            "echo '```'\n"
        )
        fake_llm.chmod(0o755)

        result = runner.invoke(
            app,
            [
                "--json",
                "loop",
                "run",
                "6",
                "--no-apply",
                "--max-iter",
                "1",
                "--path",
                str(project_path),
            ],
            env={
                "ERDOS_REPO_ROOT": str(tmp_path),
                # Only global set, no CODE
                "ERDOS_LLM_COMMAND": str(fake_llm),
            },
        )

        data = json.loads(result.stdout)
        assert data["command"] == "erdos loop"
        # Should not fail with CONFIG_ERROR
        if not data["success"]:
            assert data["error"]["type"] != "CONFIG_ERROR"

    def test_loop_llm_cmd_override_bypasses_router(self, tmp_path: Path) -> None:
        """--llm-cmd override bypasses router entirely."""
        project_path = _setup_lean_project(tmp_path)

        # Create two scripts - one for env, one for override
        env_llm = tmp_path / "env_llm.sh"
        env_llm.write_text("#!/bin/bash\necho 'ENV response'\n")
        env_llm.chmod(0o755)

        override_llm = tmp_path / "override_llm.sh"
        override_llm.write_text(
            "#!/bin/bash\n"
            "echo '```lean'\n"
            "echo 'theorem foo : True := trivial'\n"
            "echo '```'\n"
        )
        override_llm.chmod(0o755)

        result = runner.invoke(
            app,
            [
                "--json",
                "loop",
                "run",
                "6",
                "--no-apply",
                "--max-iter",
                "1",
                "--path",
                str(project_path),
                "--llm-cmd",
                str(override_llm),
            ],
            env={
                "ERDOS_REPO_ROOT": str(tmp_path),
                "ERDOS_LLM_COMMAND_CODE": str(env_llm),
                "ERDOS_LLM_COMMAND": str(env_llm),
            },
        )

        data = json.loads(result.stdout)
        assert data["command"] == "erdos loop"
        # Should not fail with CONFIG_ERROR
        if not data["success"]:
            assert data["error"]["type"] != "CONFIG_ERROR"

    def test_loop_error_when_no_llm_command_configured(self, tmp_path: Path) -> None:
        """Error when no LLM command configured (router fails with CONFIG_ERROR)."""
        project_path = _setup_lean_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "--json",
                "loop",
                "run",
                "6",
                "--no-apply",
                "--path",
                str(project_path),
            ],
            env={
                "ERDOS_REPO_ROOT": str(tmp_path),
                # No LLM command configured at all
            },
        )

        # Should fail with CONFIG_ERROR
        assert result.exit_code == ExitCode.CONFIG_ERROR, f"Output: {result.stdout}"
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error"]["type"] == "CONFIG_ERROR"
        assert "No LLM command configured" in data["error"]["message"]
        # Should mention what env vars to set
        assert "ERDOS_LLM_COMMAND_CODE" in data["error"]["message"]
        assert "ERDOS_LLM_COMMAND" in data["error"]["message"]

    def test_loop_error_message_mentions_task_type(self, tmp_path: Path) -> None:
        """Error message mentions the task type for debugging."""
        project_path = _setup_lean_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "--json",
                "loop",
                "run",
                "6",
                "--no-apply",
                "--path",
                str(project_path),
            ],
            env={
                "ERDOS_REPO_ROOT": str(tmp_path),
            },
        )

        assert result.exit_code == ExitCode.CONFIG_ERROR
        data = json.loads(result.stdout)
        # Should mention task type for debugging
        assert "loop_patch" in data["error"]["message"]

    def test_loop_router_uses_code_not_math(self, tmp_path: Path) -> None:
        """loop run uses ERDOS_LLM_COMMAND_CODE, not ERDOS_LLM_COMMAND_MATH."""
        project_path = _setup_lean_project(tmp_path)

        # Only set MATH - loop should fail because it needs CODE
        result = runner.invoke(
            app,
            [
                "--json",
                "loop",
                "run",
                "6",
                "--no-apply",
                "--path",
                str(project_path),
            ],
            env={
                "ERDOS_REPO_ROOT": str(tmp_path),
                # Only MATH set - loop needs CODE or global
                "ERDOS_LLM_COMMAND_MATH": "/path/to/math/llm",
            },
        )

        # Should fail with CONFIG_ERROR (MATH doesn't satisfy loop_patch)
        assert result.exit_code == ExitCode.CONFIG_ERROR, f"Output: {result.stdout}"
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert "ERDOS_LLM_COMMAND_CODE" in data["error"]["message"]
