"""Test helper for constructing a CliRunner across Click versions.

Click 8.1.x supports `CliRunner(mix_stderr=...)`.
Click 8.3.x removed that constructor argument and always captures stderr separately.

This helper keeps our tests compatible with both.
"""

from __future__ import annotations

from typing import Any, cast

from typer.testing import CliRunner


def make_cli_runner() -> CliRunner:
    try:
        runner: CliRunner = cast("Any", CliRunner)(mix_stderr=False)
        return runner
    except TypeError:
        return CliRunner()
