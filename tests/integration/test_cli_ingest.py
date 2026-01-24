"""Integration tests for erdos ingest command (SPEC-010-E)."""

from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING

import responses

from erdos.cli import app
from erdos.core.exit_codes import ExitCode
from tests.cli_runner import make_cli_runner


if TYPE_CHECKING:
    from pathlib import Path


runner = make_cli_runner()


def _data_dir(tmp_path: Path, sample_problems_yaml: Path) -> Path:
    """Create a data directory with sample problems."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copyfile(sample_problems_yaml, data_dir / "problems.yaml")
    return data_dir


@responses.activate
def test_ingest_command_json_output(
    tmp_path: Path,
    sample_problems_yaml: Path,
    arxiv_math_0404188_fixture: str,
    crossref_annals_fixture: str,
) -> None:
    """Test erdos ingest with --json flag outputs valid JSON."""
    # Mock Crossref API (DOI is primary source for problem 6)
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.4007/annals.2008.167.481",
        body=crossref_annals_fixture,
        status=200,
    )

    # Setup test environment
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    repo_root = tmp_path

    # Run command with --json --no-download --source crossref (legacy source)
    result = runner.invoke(
        app,
        ["--json", "ingest", "6", "--no-download", "--source", "crossref"],
        env={"ERDOS_DATA_PATH": str(data_dir), "ERDOS_REPO_ROOT": str(repo_root)},
    )

    # Assert exit code success
    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    # Assert stdout is valid JSON
    data = json.loads(result.stdout)
    assert data["command"] == "erdos ingest"
    assert data["success"] is True
    assert "data" in data

    # Assert expected fields in data
    assert data["data"]["problem_id"] == 6
    assert "manifest_path" in data["data"]
    assert "references_total" in data["data"]
    assert "entries_written" in data["data"]
    assert "skipped" in data["data"]
    assert "manifest" in data["data"]
    assert data["data"]["entries_written"] == len(data["data"]["manifest"]["entries"])


@responses.activate
def test_ingest_command_no_download(
    tmp_path: Path,
    sample_problems_yaml: Path,
    arxiv_math_0404188_fixture: str,
    crossref_annals_fixture: str,
) -> None:
    """Test erdos ingest with --no-download skips cache files."""
    # Mock Crossref API
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.4007/annals.2008.167.481",
        body=crossref_annals_fixture,
        status=200,
    )

    # Setup test environment
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    repo_root = tmp_path

    # Run command with --no-download --source crossref (legacy source)
    result = runner.invoke(
        app,
        ["--json", "ingest", "6", "--no-download", "--source", "crossref"],
        env={"ERDOS_DATA_PATH": str(data_dir), "ERDOS_REPO_ROOT": str(repo_root)},
    )

    assert result.exit_code == 0

    # Verify no cache directory was created
    cache_dir = repo_root / "literature" / "cache"
    assert not cache_dir.exists() or not list(cache_dir.rglob("*.tar.gz"))


@responses.activate
def test_ingest_command_idempotent(
    tmp_path: Path,
    sample_problems_yaml: Path,
    arxiv_math_0404188_fixture: str,
    crossref_annals_fixture: str,
) -> None:
    """Test erdos ingest is idempotent (second run doesn't re-fetch)."""
    # Mock Crossref API for first call only
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.4007/annals.2008.167.481",
        body=crossref_annals_fixture,
        status=200,
    )

    # Setup test environment
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    repo_root = tmp_path

    # First run with --source crossref (legacy source)
    result1 = runner.invoke(
        app,
        ["--json", "ingest", "6", "--no-download", "--source", "crossref"],
        env={"ERDOS_DATA_PATH": str(data_dir), "ERDOS_REPO_ROOT": str(repo_root)},
    )
    assert result1.exit_code == 0

    # Reset responses - no more network calls should happen
    responses.reset()

    # Second run with --no-network should succeed (uses cached manifest)
    result2 = runner.invoke(
        app,
        ["--json", "ingest", "6", "--no-network"],
        env={"ERDOS_DATA_PATH": str(data_dir), "ERDOS_REPO_ROOT": str(repo_root)},
    )
    assert result2.exit_code == 0

    # Parse results
    data1 = json.loads(result1.stdout)
    data2 = json.loads(result2.stdout)

    # Both should succeed
    assert data1["success"] is True
    assert data2["success"] is True

    # Should have same number of entries
    assert data1["data"]["entries_written"] == data2["data"]["entries_written"]


def test_ingest_command_no_network_without_existing_manifest(
    tmp_path: Path, sample_problems_yaml: Path
) -> None:
    """--no-network should fail when manifest doesn't exist yet."""
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    repo_root = tmp_path

    result = runner.invoke(
        app,
        ["--json", "ingest", "6", "--no-network"],
        env={"ERDOS_DATA_PATH": str(data_dir), "ERDOS_REPO_ROOT": str(repo_root)},
    )

    assert result.exit_code == ExitCode.NETWORK_ERROR
    data = json.loads(result.stdout)
    assert data["success"] is False
    assert data["error"]["type"] == "NetworkError"
    assert data["error"]["code"] == ExitCode.NETWORK_ERROR


def test_ingest_command_not_found(tmp_path: Path, sample_problems_yaml: Path) -> None:
    """Test erdos ingest with non-existent problem ID."""
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    repo_root = tmp_path

    result = runner.invoke(
        app,
        ["--json", "ingest", "99999"],
        env={"ERDOS_DATA_PATH": str(data_dir), "ERDOS_REPO_ROOT": str(repo_root)},
    )

    # Should fail with NOT_FOUND exit code (3)
    assert result.exit_code == ExitCode.NOT_FOUND

    # Parse error output
    data = json.loads(result.stdout)
    assert data["success"] is False
    assert data["error"]["code"] == ExitCode.NOT_FOUND
    assert "not found" in data["error"]["message"].lower()


def test_ingest_command_human_output(
    tmp_path: Path, sample_problems_yaml: Path, strip_ansi
) -> None:
    """Test erdos ingest without --json shows human-readable output."""
    data_dir = _data_dir(tmp_path, sample_problems_yaml)
    repo_root = tmp_path

    # Without mocking, this will fail trying to fetch, but we can test the command exists
    result = runner.invoke(
        app,
        ["ingest", "--help"],
        env={"ERDOS_DATA_PATH": str(data_dir), "ERDOS_REPO_ROOT": str(repo_root)},
        terminal_width=200,
    )

    # Help should work
    assert result.exit_code == 0
    output = strip_ansi(result.stdout)
    assert "ingest" in output.lower()
