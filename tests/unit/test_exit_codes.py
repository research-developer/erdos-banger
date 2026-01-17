"""Tests for CLI exit codes."""

from erdos.core.exit_codes import ExitCode


def test_exit_codes_match_spec() -> None:
    assert ExitCode.SUCCESS.value == 0
    assert ExitCode.ERROR.value == 1
    assert ExitCode.USAGE_ERROR.value == 2
    assert ExitCode.NOT_FOUND.value == 3
    assert ExitCode.NETWORK_ERROR.value == 4
    assert ExitCode.LEAN_ERROR.value == 5
    assert ExitCode.CONFIG_ERROR.value == 10
