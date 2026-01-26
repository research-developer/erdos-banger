"""End-to-end tests for graceful failure handling.

These tests verify that missing configuration returns structured errors
(ConfigError) without Python tracebacks leaking to users.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.e2e
class TestGracefulFailures:
    """E2E tests for graceful failure without API keys."""

    def test_exa_search_without_api_key_returns_config_error(self, cli_runner) -> None:
        """erdos research exa search without EXA_API_KEY returns ConfigError."""
        # cli_runner already clears API keys, so this should fail gracefully
        result = cli_runner(
            "--json",
            "research",
            "exa",
            "search",
            "6",
            "test query",
            check=False,
        )

        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error"]["type"] == "ConfigError"
        assert "EXA_API_KEY" in data["error"]["message"]
        assert data["error"]["code"] == 10  # ConfigError exit code

    def test_exa_search_no_traceback(self, cli_runner) -> None:
        """erdos research exa search failure doesn't leak Python traceback."""
        result = cli_runner(
            "--json",
            "research",
            "exa",
            "search",
            "6",
            "test query",
            check=False,
        )

        # No traceback in stderr
        assert "Traceback" not in result.stderr
        assert "raise " not in result.stderr

    def test_lean_prove_without_api_key_returns_config_error(
        self, tmp_path: Path
    ) -> None:
        """erdos lean prove without ARISTOTLE_API_KEY returns ConfigError."""
        # Need to create a minimal Lean file to pass Typer validation
        project_root = Path(__file__).resolve().parents[2]
        uv_exe = shutil.which("uv")
        if uv_exe is None:
            pytest.skip("uv executable not found on PATH")

        lean_file = tmp_path / "test.lean"
        lean_file.write_text("-- placeholder")
        output_file = tmp_path / "test.out.lean"

        env = os.environ.copy()
        env["UV_PROJECT"] = str(project_root)
        env["ERDOS_LOAD_DOTENV"] = "0"
        # Explicitly unset the API key
        env.pop("ARISTOTLE_API_KEY", None)

        result = subprocess.run(  # noqa: S603
            [
                uv_exe,
                "run",
                "erdos",
                "--json",
                "lean",
                "prove",
                str(lean_file),
                "-o",
                str(output_file),
            ],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env=env,
            check=False,
        )

        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error"]["type"] == "ConfigError"
        assert "ARISTOTLE_API_KEY" in data["error"]["message"]
        assert data["error"]["code"] == 10

    def test_lean_prove_no_traceback(self, tmp_path: Path) -> None:
        """erdos lean prove failure doesn't leak Python traceback."""
        project_root = Path(__file__).resolve().parents[2]
        uv_exe = shutil.which("uv")
        if uv_exe is None:
            pytest.skip("uv executable not found on PATH")

        lean_file = tmp_path / "test.lean"
        lean_file.write_text("-- placeholder")
        output_file = tmp_path / "test.out.lean"

        env = os.environ.copy()
        env["UV_PROJECT"] = str(project_root)
        env["ERDOS_LOAD_DOTENV"] = "0"
        env.pop("ARISTOTLE_API_KEY", None)

        result = subprocess.run(  # noqa: S603
            [
                uv_exe,
                "run",
                "erdos",
                "--json",
                "lean",
                "prove",
                str(lean_file),
                "-o",
                str(output_file),
            ],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env=env,
            check=False,
        )

        # No traceback in stderr
        assert "Traceback" not in result.stderr
        assert "raise " not in result.stderr
