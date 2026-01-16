"""Exit codes for CLI commands."""

from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    ERROR = 1
    USAGE_ERROR = 2
    NOT_FOUND = 3
    NETWORK_ERROR = 4
    LEAN_ERROR = 5
    CONFIG_ERROR = 10
