"""Fixtures for end-to-end tests - full CLI invocation."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


@pytest.fixture
def cli_runner(
    tmp_path: Path, sample_problems_yaml: Path
) -> Iterator[Callable[..., subprocess.CompletedProcess[str]]]:
    """Run CLI commands in an isolated environment."""
    project_root = Path(__file__).resolve().parents[2]
    uv_exe = shutil.which("uv")
    if uv_exe is None:
        raise AssertionError("`uv` executable not found on PATH")

    data_dir = tmp_path / "data" / "erdosproblems"
    data_dir.mkdir(parents=True)
    shutil.copyfile(sample_problems_yaml, data_dir / "problems.yaml")

    def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["UV_PROJECT"] = str(project_root)
        env["ERDOS_DATA_PATH"] = str(data_dir)
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

    yield run
