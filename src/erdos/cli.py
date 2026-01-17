"""Erdos CLI - main entry point."""

import logging
from typing import Annotated

import typer
from rich.console import Console

from erdos import __version__
from erdos.commands import lean, list_cmd, refs, search, show


def _configure_logging(level: str) -> None:
    """Configure Python logging with the specified level."""
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARN": logging.WARNING,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    log_level = level_map.get(level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


console = Console()
err_console = Console(stderr=True)

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
        console.print(f"erdos-banger {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
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
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output as JSON for machine consumption.",
        ),
    ] = False,
    log_level: Annotated[
        str,
        typer.Option(
            "--log-level",
            help="Logging level: DEBUG, INFO, WARN, ERROR.",
        ),
    ] = "INFO",
) -> None:
    """
    Erdos CLI - toolkit for Erdős problem research.

    Run 'erdos COMMAND --help' for command-specific help.
    """
    # Configure logging based on --log-level
    _configure_logging(log_level)

    ctx.ensure_object(dict)
    if isinstance(ctx.obj, dict):
        ctx.obj.update(
            {
                "json": json_output,
                "log_level": log_level,
            }
        )


app.add_typer(list_cmd.app, name="list")
app.add_typer(show.app, name="show")
app.add_typer(refs.app, name="refs")
app.add_typer(search.app, name="search")
app.add_typer(lean.app, name="lean")


if __name__ == "__main__":
    app()
