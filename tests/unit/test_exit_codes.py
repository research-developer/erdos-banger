"""Tests for CLI exit codes."""

from erdos.core.exit_codes import ExitCode


def test_exit_codes_match_spec() -> None:
    assert ExitCode.SUCCESS == 0
    assert ExitCode.ERROR == 1
    assert ExitCode.USAGE_ERROR == 2
    assert ExitCode.NOT_FOUND == 3
    assert ExitCode.NETWORK_ERROR == 4
    assert ExitCode.LEAN_ERROR == 5
    assert ExitCode.CONFIG_ERROR == 10
