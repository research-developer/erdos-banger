from collections.abc import Callable
from typing import Any

import typer
from rich.console import Console

from erdos.core.models import CLIOutput


console = Console()
err_console = Console(stderr=True)

HumanPrinter = Callable[[Any], None]


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


def exit_with_result(
    ctx: typer.Context,
    result: CLIOutput,
    *,
    print_human: HumanPrinter | None = None,
) -> None:
    """Render output and exit non-zero on failure."""
    output_result(ctx, result, print_human=print_human)

    if not result.success:
        _, code = _error_details(result)
        raise typer.Exit(code=code)


def set_json_mode(ctx: typer.Context, enabled: bool) -> None:
    """Enable JSON output mode on the Typer context."""
    ctx.ensure_object(dict)
    if enabled and isinstance(ctx.obj, dict):
        ctx.obj["json"] = True
