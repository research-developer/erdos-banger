"""Test helper for constructing a CliRunner across Click versions.

Click 8.1.x supports `CliRunner(mix_stderr=...)`.
Click 8.3.x removed that constructor argument and always captures stderr separately.

This helper keeps our tests compatible with both.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any, cast

from typer.testing import CliRunner


def make_cli_runner() -> CliRunner:
    try:
        runner: CliRunner = cast("Any", CliRunner)(mix_stderr=False)
        return runner
    except TypeError:
        return CliRunner()


def unset_env_vars(*names: str) -> dict[str, str | None]:
    """Return env overrides that unset variables for CliRunner.invoke().

    Click 8.2+ supports passing `None` values in `env=` to delete variables in
    the isolated environment. Older Click versions don't, so we fall back to
    empty strings (our routing code treats empty/whitespace-only as unset).
    """
    try:
        click_version = version("click")
    except PackageNotFoundError:
        click_version = "0.0.0"

    # Click 8.2 introduced `env: Mapping[str, str | None]` support.
    parts = click_version.split(".")
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        major, minor = 0, 0

    unset: str | None = None if (major, minor) >= (8, 2) else ""
    return dict.fromkeys(names, unset)
