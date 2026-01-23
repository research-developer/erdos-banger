"""Shared helpers for CLI command modules."""

from __future__ import annotations

from rich.console import Console


_err_console = Console(stderr=True)


def print_if_human(message: str, *, json_output: bool, style: str = "dim") -> None:
    """Print a message only when not in JSON mode."""
    if json_output:
        return
    _err_console.print(f"[{style}]{message}[/{style}]")
