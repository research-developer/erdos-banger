"""erdos lean - Lean 4 integration commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, cast

import typer
from rich.console import Console

from erdos.core.formalizer import generate_skeleton
from erdos.core.lean_runner import LeanRunner
from erdos.core.models import CLIOutput, LeanCheckResult
from erdos.core.problem_loader import ProblemLoader


app = typer.Typer(help="Lean 4 theorem prover commands.")
console = Console()
err_console = Console(stderr=True)


def _output(ctx: typer.Context, data: CLIOutput) -> None:
    if (ctx.obj or {}).get("json"):
        console.print_json(data.model_dump_json())
    elif data.success:
        if isinstance(data.data, dict) and {"file", "success"}.issubset(
            data.data.keys()
        ):
            _print_human_check_result(cast("dict[str, Any]", data.data))
        else:
            console.print(data.data)
    else:
        error = cast("dict[str, Any]", data.error)
        err_console.print(f"[red]Error:[/red] {error['message']}")


def _print_human_check_result(result_data: dict[str, Any]) -> None:
    """Pretty-print Lean check result."""
    result = LeanCheckResult.model_validate(result_data, strict=False)

    if result.success:
        console.print(f"[green]✓[/green] {result.file} compiled successfully")
    else:
        console.print(f"[red]✗[/red] {result.file} has {result.error_count} error(s)")
        for error in result.errors:
            console.print(f"  {error}")


# ============================================================================
# Core Logic
# ============================================================================


def init_lean_project(project_path: Path) -> CLIOutput:
    """Initialize Lean project structure."""
    try:
        runner = LeanRunner(project_path)
        runner.init()
        return CLIOutput.ok(
            command="erdos lean init",
            data={"project_path": str(project_path), "initialized": True},
        )
    except NotImplementedError as e:
        return CLIOutput.err(
            command="erdos lean init",
            error_type="NotImplemented",
            message=str(e),
            code=1,
        )
    except Exception as e:
        return CLIOutput.err(
            command="erdos lean init",
            error_type="InitError",
            message=str(e),
            code=1,
        )


def check_lean_file(file_path: Path, project_path: Path) -> CLIOutput:
    """Check a Lean file for errors."""
    try:
        runner = LeanRunner(project_path)
        result = runner.check(file_path)
        return CLIOutput.ok(
            command="erdos lean check",
            data=result.model_dump(mode="json"),
        )
    except NotImplementedError as e:
        return CLIOutput.err(
            command="erdos lean check",
            error_type="NotImplemented",
            message=str(e),
            code=1,
        )
    except FileNotFoundError:
        return CLIOutput.err(
            command="erdos lean check",
            error_type="NotFound",
            message=f"File not found: {file_path}",
            code=3,
        )
    except Exception as e:
        return CLIOutput.err(
            command="erdos lean check",
            error_type="Error",
            message=str(e),
            code=1,
        )


# ============================================================================
# CLI Commands
# ============================================================================


@app.command()
def init(
    ctx: typer.Context,
    project_path: Annotated[
        Path | None,
        typer.Option(
            "--path",
            "-p",
            help="Path to Lean project (default: formal/lean/)",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output as JSON for machine consumption.",
        ),
    ] = False,
) -> None:
    """
    Initialize Lean 4 project with mathlib.

    Creates lakefile.lean, lean-toolchain, and directory structure.
    """
    ctx.ensure_object(dict)
    if json_output:
        ctx.obj["json"] = True

    path = project_path or Path("formal/lean")
    result = init_lean_project(path)
    _output(ctx, result)
    if not result.success:
        error = cast("dict[str, Any]", result.error)
        raise typer.Exit(code=int(error.get("code", 1)))


@app.command()
def check(
    ctx: typer.Context,
    file: Annotated[
        Path,
        typer.Argument(
            help="Lean file to check.",
            exists=True,
            readable=True,
        ),
    ],
    project_path: Annotated[
        Path | None,
        typer.Option(
            "--path",
            "-p",
            help="Path to Lean project (default: formal/lean/)",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output as JSON for machine consumption.",
        ),
    ] = False,
) -> None:
    """
    Check a Lean file for compilation errors.

    Example: erdos lean check Erdos/Problem006.lean
    """
    ctx.ensure_object(dict)
    if json_output:
        ctx.obj["json"] = True

    path = project_path or Path("formal/lean")
    result = check_lean_file(file, path)
    _output(ctx, result)

    if (
        result.success
        and isinstance(result.data, dict)
        and not result.data.get("success", True)
    ):
        raise typer.Exit(code=5)
    if not result.success:
        error = cast("dict[str, Any]", result.error)
        raise typer.Exit(code=int(error.get("code", 1)))


@app.command()
def formalize(
    ctx: typer.Context,
    problem_id: Annotated[
        int,
        typer.Argument(
            help="Problem ID to formalize.",
            min=1,
        ),
    ],
    project_path: Annotated[
        Path | None,
        typer.Option(
            "--path",
            "-p",
            help="Path to Lean project (default: formal/lean/)",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output as JSON for machine consumption.",
        ),
    ] = False,
) -> None:
    """
    Generate a Lean skeleton for a problem.

    Creates Erdos/Problem<ID>.lean with theorem stub.
    """
    ctx.ensure_object(dict)
    if json_output:
        ctx.obj["json"] = True

    path = project_path or Path("formal/lean")
    loader = ProblemLoader.from_default()

    problem = loader.get_by_id(problem_id)
    if problem is None:
        err_console.print(f"[red]Error:[/red] Problem {problem_id} not found")
        raise typer.Exit(code=3)

    try:
        output_file = generate_skeleton(problem, path)
    except NotImplementedError as e:
        result = CLIOutput.err(
            command="erdos lean formalize",
            error_type="NotImplemented",
            message=str(e),
            code=1,
        )
        _output(ctx, result)
        raise typer.Exit(code=1) from None

    if (ctx.obj or {}).get("json"):
        console.print_json(
            CLIOutput.ok(
                command="erdos lean formalize",
                data={"problem_id": problem_id, "file": str(output_file)},
            ).model_dump_json()
        )
    else:
        console.print(f"[green]✓[/green] Created {output_file}")
        console.print(f"  Run: erdos lean check {output_file}")
