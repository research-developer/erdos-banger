import logging
from collections.abc import Callable
from typing import Any

import typer
from rich.console import Console

from erdos.core.context import AppContext
from erdos.core.models import CLIOutput
from erdos.core.run_logger import RunLogger, get_run_logger


logger = logging.getLogger(__name__)

console = Console()
err_console = Console(stderr=True)

HumanPrinter = Callable[[Any], None]

# Commands that should not be logged (to avoid infinite recursion or noise)
EXCLUDED_COMMANDS = frozenset({"erdos logs"})


def _get_configured_run_logger(ctx: typer.Context) -> RunLogger:
    """Prefer the AppConfig log path when AppContext is available."""
    obj = ctx.obj
    if isinstance(obj, dict):
        app_ctx = obj.get("app_context")
        if isinstance(app_ctx, AppContext):
            return RunLogger(log_file=app_ctx.config.run_log_path)
    return get_run_logger()


def _error_details(result: CLIOutput) -> tuple[str, int]:
    error = result.error
    if isinstance(error, dict):
        message = error.get("message", error)
        raw_code = error.get("code", 1)
        try:
            code = int(raw_code)
        except (TypeError, ValueError):
            code = 1
        return str(message), code
    return str(error), 1


def output_result(
    ctx: typer.Context,
    result: CLIOutput,
    *,
    print_human: HumanPrinter | None = None,
) -> None:
    """Render a CLIOutput according to global output settings."""
    json_mode = bool((ctx.obj or {}).get("json", False))

    if json_mode:
        console.print_json(result.model_dump_json())
        return

    if result.success:
        if print_human is None:
            console.print(result.data)
        else:
            print_human(result.data)
        return

    message, _ = _error_details(result)
    err_console.print(f"[red]Error:[/red] {message}")


def _get_command_args(ctx: typer.Context) -> dict[str, Any]:
    """Extract command arguments from typer context."""
    args: dict[str, Any] = {}

    # Get params from the current context and any parent invocation contexts
    current: Any = ctx
    while current is not None:
        if hasattr(current, "params") and current.params:
            # Don't overwrite already collected args
            for key, value in current.params.items():
                if key not in args:
                    args[key] = value
        current = getattr(current, "parent", None)

    return args


def exit_with_result(
    ctx: typer.Context,
    result: CLIOutput,
    *,
    print_human: HumanPrinter | None = None,
) -> None:
    """Render output, log the command, and exit non-zero on failure."""
    # Log the command (unless excluded)
    if result.command not in EXCLUDED_COMMANDS:
        try:
            run_logger = _get_configured_run_logger(ctx)
            args = _get_command_args(ctx)
            run_logger.log(result, args)
        except Exception as e:
            # Don't fail the command if logging fails
            logger.debug("Failed to log command: %s", e)

    output_result(ctx, result, print_human=print_human)

    if not result.success:
        _, code = _error_details(result)
        raise typer.Exit(code=code)
