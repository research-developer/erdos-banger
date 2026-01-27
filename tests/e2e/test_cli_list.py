"""End-to-end tests for erdos list command."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable

import pytest


@pytest.mark.e2e
class TestErdosList:
    """E2E tests for erdos list JSON contract."""

    def test_list_json_output(
        self, cli_runner: Callable[..., subprocess.CompletedProcess[str]]
    ) -> None:
        """erdos --json list returns valid JSON array."""
        result = cli_runner("--json", "list", "--limit", "2")

        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["command"] == "erdos list"
        assert isinstance(data["data"], list)
        assert len(data["data"]) <= 2

    def test_list_json_schema_keys(
        self, cli_runner: Callable[..., subprocess.CompletedProcess[str]]
    ) -> None:
        """erdos --json list items have expected schema keys."""
        result = cli_runner("--json", "list", "--limit", "1")

        data = json.loads(result.stdout)
        assert isinstance(data.get("data"), list)
        assert data["data"], "Expected at least one problem in list output"
        item = data["data"][0]
        # Core schema keys that must be present
        assert "id" in item
        assert "title" in item
        assert "status" in item
        assert isinstance(item["id"], int)

    def test_list_exit_code_zero(
        self, cli_runner: Callable[..., subprocess.CompletedProcess[str]]
    ) -> None:
        """erdos list returns exit code 0 on success."""
        result = cli_runner("list", "--limit", "1")
        assert result.returncode == 0

    def test_list_filter_by_status(
        self, cli_runner: Callable[..., subprocess.CompletedProcess[str]]
    ) -> None:
        """erdos --json list --status filters correctly."""
        result = cli_runner("--json", "list", "--status", "proved", "--limit", "5")

        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["data"], "Expected at least one 'proved' problem in sample data"
        for item in data["data"]:
            assert item["status"] == "proved"
