"""erdos lean copilot - Lean Copilot integration commands (SPEC-033)."""

from __future__ import annotations

import logging
from typing import Annotated

import typer

from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput


logger = logging.getLogger(__name__)


# Create subgroup for copilot commands
copilot_app = typer.Typer(
    help="Lean Copilot integration commands.",
    context_settings={"help_option_names": ["-h", "--help"]},
)


@copilot_app.command(name="serve")
def serve(
    ctx: typer.Context,
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Server port"),
    ] = 8000,
    host: Annotated[
        str,
        typer.Option("--host", "-H", help="Bind address"),
    ] = "127.0.0.1",
    llm_cmd: Annotated[
        str | None,
        typer.Option(
            "--llm-cmd",
            help="Override LLM command for /generate (bypasses router)",
        ),
    ] = None,
    log_level: Annotated[
        str,
        typer.Option("--log-level", help="Logging verbosity"),
    ] = "info",
) -> None:
    """Start the Lean Copilot external API server.

    Implements the external model API for Lean Copilot:
    - POST /generate - Generate tactic suggestions

    Requires the 'copilot' extra: uv sync --extra copilot

    Example:
        erdos lean copilot serve --port 8080
    """
    # Check if copilot dependencies are available
    from erdos.lean_copilot import (  # noqa: PLC0415
        CopilotNotAvailableError,
        is_copilot_available,
    )

    if not is_copilot_available():
        result = CLIOutput.err(
            command="erdos lean copilot serve",
            error_type="DependencyError",
            message=(
                "Copilot server requires the 'copilot' extra. "
                "Install with: uv sync --extra copilot"
            ),
            code=ExitCode.CONFIG_ERROR,
        )
        exit_with_result(ctx, result, print_human=_print_human)
        return

    # Import server components (only available if copilot extra installed)
    try:
        import uvicorn  # noqa: PLC0415

        from erdos.lean_copilot.server import create_app  # noqa: PLC0415
    except ImportError as e:
        result = CLIOutput.err(
            command="erdos lean copilot serve",
            error_type="DependencyError",
            message=f"Failed to import copilot dependencies: {e}",
            code=ExitCode.CONFIG_ERROR,
        )
        exit_with_result(ctx, result, print_human=_print_human)
        return

    # Create the FastAPI app
    try:
        app = create_app(llm_command_override=llm_cmd)
    except CopilotNotAvailableError as e:
        result = CLIOutput.err(
            command="erdos lean copilot serve",
            error_type="DependencyError",
            message=str(e),
            code=ExitCode.CONFIG_ERROR,
        )
        exit_with_result(ctx, result, print_human=_print_human)
        return

    # Log startup info
    logger.info("Starting Lean Copilot API server on %s:%d", host, port)
    if llm_cmd:
        logger.info("Using LLM command override: %s", llm_cmd)
    else:
        logger.info("Using SPEC-032 router for LLM command resolution")

    normalized_log_level = log_level.strip().lower()
    valid_levels = {"critical", "error", "warning", "info", "debug", "trace"}
    if normalized_log_level not in valid_levels:
        result = CLIOutput.err(
            command="erdos lean copilot serve",
            error_type="UsageError",
            message=(
                f"Invalid --log-level {log_level!r}. "
                f"Expected one of: {', '.join(sorted(valid_levels))}"
            ),
            code=ExitCode.USAGE_ERROR,
        )
        exit_with_result(ctx, result, print_human=_print_human)
        return

    # Run the server (this blocks until interrupted)
    # Note: uvicorn.run() doesn't return until the server stops
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=normalized_log_level,
    )


def _print_human(result: CLIOutput) -> None:
    """Print human-readable output for copilot commands."""
    from rich.console import Console  # noqa: PLC0415

    console = Console()

    if result.success:
        console.print("[green]✓[/green] Success")
        if result.data and isinstance(result.data, dict):
            for key, value in result.data.items():
                console.print(f"  {key}: {value}")
    else:
        # Error info is in result.error dict, not result.message
        error_msg = "Error"
        if result.error and isinstance(result.error, dict):
            error_msg = result.error.get("message", "Error")
        console.print(f"[red]✗[/red] {error_msg}")


def register(app: typer.Typer) -> None:
    """Register copilot subcommand group on the lean app."""
    app.add_typer(copilot_app, name="copilot")
