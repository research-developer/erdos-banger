"""Minimal passing E2E test placeholder."""

import pytest


@pytest.mark.e2e
def test_e2e_placeholder(cli_runner) -> None:
    result = cli_runner("--version")
    assert result.returncode == 0
    assert "erdos-harness" in result.stdout

