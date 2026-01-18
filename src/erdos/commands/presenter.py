from collections.abc import Callable
from typing import Any, cast

import typer
from rich.console import Console

from erdos.core.models import CLIOutput


console = Console()
err_console = Console(stderr=True)

HumanPrinter = Callable[[Any], None]


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

    error = cast("dict[str, Any]", result.error)
    err_console.print(f"[red]Error:[/red] {error['message']}")


def exit_with_result(
    ctx: typer.Context,
    result: CLIOutput,
    *,
    print_human: HumanPrinter | None = None,
) -> None:
    """Render output and exit non-zero on failure."""
    output_result(ctx, result, print_human=print_human)

    if not result.success:
        error = cast("dict[str, Any]", result.error)
        raise typer.Exit(code=int(error.get("code", 1)))
