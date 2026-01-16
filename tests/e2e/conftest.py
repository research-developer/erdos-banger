"""Fixtures for end-to-end tests - full CLI invocation."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def cli_runner(tmp_path: Path):
    """Run CLI commands in an isolated environment."""
    project_root = Path(__file__).resolve().parents[2]
    uv_exe = shutil.which("uv")
    if uv_exe is None:
        raise AssertionError("`uv` executable not found on PATH")

    def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["UV_PROJECT"] = str(project_root)
        result = subprocess.run(  # noqa: S603
            [uv_exe, "run", "erdos", *args],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env=env,
            check=False,
        )
        if check and result.returncode != 0:
            raise AssertionError(
                f"CLI failed with code {result.returncode}:\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )
        return result

    return run
