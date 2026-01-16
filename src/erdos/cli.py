"""Erdos CLI - main entry point."""

from typing import Annotated

import typer
from rich.console import Console

from erdos import __version__


console = Console()

app = typer.Typer(
    name="erdos",
    help="CLI toolkit for Erdős problem research.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=True,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"erdos-harness {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    _version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = None,
) -> None:
    """Main entry point."""
