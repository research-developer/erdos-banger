"""End-to-end test for default data/index persistence workflow."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


@pytest.mark.e2e
def test_search_index_persists_across_process_restart(fixtures_dir: Path) -> None:
    """Build index once, then reuse it in a new process via default paths."""
    with tempfile.TemporaryDirectory() as workdir:
        root = Path(workdir)
        data_dir = root / "data"
        data_dir.mkdir(parents=True)

        fixture = fixtures_dir / "sample_problems.yaml"
        shutil.copyfile(fixture, data_dir / "problems_enriched.yaml")

        env = os.environ.copy()
        env.pop("ERDOS_DATA_PATH", None)
        env.pop("ERDOS_INDEX_PATH", None)
        env["ERDOS_LOAD_DOTENV"] = "0"
        env.pop("ERDOS_REPO_ROOT", None)

        build_cmd = [
            sys.executable,
            "-m",
            "erdos.cli",
            "--json",
            "search",
            "prime",
            "--build-index",
            "--limit",
            "1",
        ]
        built = subprocess.run(  # noqa: S603
            build_cmd,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert built.returncode == 0, (
            f"stderr:\n{built.stderr}\nstdout:\n{built.stdout}"
        )

        first = json.loads(built.stdout)
        assert first["success"] is True
        assert first["data"]["use_fts"] is True

        db_path = root / "index" / "erdos.sqlite"
        assert db_path.exists()

        search_cmd = [
            sys.executable,
            "-m",
            "erdos.cli",
            "--json",
            "search",
            "prime",
            "--limit",
            "1",
        ]
        searched = subprocess.run(  # noqa: S603
            search_cmd,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert searched.returncode == 0, (
            f"stderr:\n{searched.stderr}\nstdout:\n{searched.stdout}"
        )

        second = json.loads(searched.stdout)
        assert second["success"] is True
        assert second["data"]["use_fts"] is True
        assert second["data"]["count"] >= 1
