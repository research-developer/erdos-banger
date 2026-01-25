"""Generate the CLI reference markdown from the live Typer command tree.

This script keeps docs aligned with the code by capturing `--help` output for
every command and subcommand.

Usage:
    uv run python scripts/generate_cli_reference.py
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import click
from typer.main import get_command
from typer.testing import CliRunner

from erdos.cli import app


if TYPE_CHECKING:
    from collections.abc import Iterable


_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _strip_trailing_whitespace(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines()).rstrip()


def _make_cli_runner() -> CliRunner:
    # Click 8.1 supports `mix_stderr`; Click 8.3 removed it.
    try:
        return CliRunner(mix_stderr=False)  # type: ignore[call-arg]
    except TypeError:
        return CliRunner()


def _iter_command_paths(
    command: click.Command, *, prefix: list[str] | None = None
) -> Iterable[list[str]]:
    path = prefix or []
    yield path
    if isinstance(command, click.Group):
        for name in sorted(command.commands):
            yield from _iter_command_paths(command.commands[name], prefix=[*path, name])


def _render_command_tree(command: click.Command, *, prefix: str = "erdos") -> list[str]:
    lines: list[str] = [f"- `{prefix}`"]
    if isinstance(command, click.Group):
        for name in sorted(command.commands):
            sub_prefix = f"{prefix} {name}"
            sub_lines = _render_command_tree(command.commands[name], prefix=sub_prefix)
            lines.extend([f"  {line}" for line in sub_lines])
    return lines


def main() -> int:
    out_path = Path("docs/developer/cli-reference.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    root_cmd = get_command(app)
    runner = _make_cli_runner()

    header = [
        "# CLI Reference (Generated)",
        "",
        "This file is generated from the live Typer command tree to keep it aligned with the code.",
        "",
        "Do not edit by hand.",
        "",
        "To regenerate:",
        "",
        "```bash",
        "uv run python scripts/generate_cli_reference.py",
        "```",
        "",
        "## Command Tree",
        "",
        *_render_command_tree(root_cmd),
        "",
        "## Help Output",
        "",
    ]

    lines: list[str] = list(header)

    # Include root (`erdos --help`) and every subcommand help in a stable order.
    for path in _iter_command_paths(root_cmd):
        display = "erdos" if not path else "erdos " + " ".join(path)
        args = ["--help"] if not path else [*path, "--help"]

        result = runner.invoke(app, args, env={"PY_COLORS": "0"})
        if result.exit_code != 0:
            msg = _strip_ansi(result.output)
            raise RuntimeError(f"Failed to render help for {display}: {msg}")

        output = _strip_trailing_whitespace(_strip_ansi(result.output))
        lines.extend(
            [
                f"### `{display}`",
                "",
                "```text",
                output,
                "```",
                "",
            ]
        )

    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
