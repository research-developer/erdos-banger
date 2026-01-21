"""erdos lean - Lean 4 integration commands."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.console import Console

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.aristotle import AristotleError, run_aristotle_prove_from_file
from erdos.core.exit_codes import ExitCode
from erdos.core.formalizer import FormalizerError, generate_skeleton
from erdos.core.lean_runner import LeanRunner, LeanRunnerError
from erdos.core.models import CLIOutput, LeanCheckResult
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository


app = typer.Typer(help="Lean 4 theorem prover commands.")
console = Console()


def _print_human_check_result(result_data: dict[str, Any]) -> None:
    """Pretty-print Lean check result."""
    result = LeanCheckResult.model_validate(result_data, strict=False)

    if result.success:
        console.print(f"[green]✓[/green] {result.file} compiled successfully")
    else:
        console.print(f"[red]✗[/red] {result.file} has {result.error_count} error(s)")
        for error in result.errors:
            console.print(f"  {error}")


def _print_human_formalize_result(result_data: dict[str, Any]) -> None:
    """Pretty-print formalize result."""
    output_file = result_data["file"]
    console.print(f"[green]✓[/green] Created {output_file}")
    console.print(f"  Run: erdos lean check {output_file}")


def _print_human_prove_result(result_data: dict[str, Any]) -> None:
    """Pretty-print Aristotle prove result."""
    output_file = result_data["output_file"]
    console.print(f"[green]✓[/green] Proof generated at {output_file}")
    console.print(f"  Run: erdos lean check {output_file}")


def _print_human(result_data: Any) -> None:
    if isinstance(result_data, dict):
        # LeanCheckResult has "file" and "success" keys
        if {"file", "success"}.issubset(result_data.keys()):
            _print_human_check_result(result_data)
        # Formalize result has "problem_id" and "file" keys
        elif {"problem_id", "file"}.issubset(result_data.keys()):
            _print_human_formalize_result(result_data)
        # Aristotle prove result has "input_file", "output_file", "aristotle" keys
        elif {"input_file", "output_file", "aristotle"}.issubset(result_data.keys()):
            _print_human_prove_result(result_data)
        # Init result has "project_path" and "initialized" keys
        elif {"project_path", "initialized"}.issubset(result_data.keys()):
            console.print(
                f"[green]✓[/green] Initialized Lean project at {result_data['project_path']}"
            )
        else:
            console.print(result_data)
    else:
        console.print(result_data)


# ============================================================================
# Core Logic
# ============================================================================


def init_lean_project(project_path: Path, *, fetch_mathlib: bool = True) -> CLIOutput:
    """Initialize Lean project structure."""
    try:
        runner = LeanRunner(project_path)
        runner.init(fetch_mathlib=fetch_mathlib)
        return CLIOutput.ok(
            command="erdos lean init",
            data={"project_path": str(project_path), "initialized": True},
        )
    except LeanRunnerError as e:
        return CLIOutput.err(
            command="erdos lean init",
            error_type="InitError",
            message=str(e),
            code=ExitCode.ERROR,
        )
    except Exception as e:
        logger.exception("Unexpected error in lean init command")
        return CLIOutput.err(
            command="erdos lean init",
            error_type="InitError",
            message=str(e),
            code=ExitCode.ERROR,
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
    except LeanRunnerError as e:
        return CLIOutput.err(
            command="erdos lean check",
            error_type="LeanRunnerError",
            message=str(e),
            code=ExitCode.ERROR,
        )
    except FileNotFoundError:
        return CLIOutput.err(
            command="erdos lean check",
            error_type="NotFound",
            message=f"File not found: {file_path}",
            code=ExitCode.NOT_FOUND,
        )
    except Exception as e:
        logger.exception("Unexpected error in lean check command")
        return CLIOutput.err(
            command="erdos lean check",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


def formalize_problem(
    problem_id: int,
    project_path: Path,
    *,
    repo: ProblemRepository,
    force: bool,
) -> CLIOutput:
    """Generate a Lean skeleton for a problem."""
    try:
        problem = repo.get_by_id(problem_id)
        if problem is None:
            return CLIOutput.err(
                command="erdos lean formalize",
                error_type="NotFound",
                message=f"Problem {problem_id} not found",
                code=ExitCode.NOT_FOUND,
            )

        output_file = generate_skeleton(problem, project_path, overwrite=force)
        return CLIOutput.ok(
            command="erdos lean formalize",
            data={"problem_id": problem_id, "file": str(output_file)},
        )
    except FormalizerError as e:
        return CLIOutput.err(
            command="erdos lean formalize",
            error_type="FormalizerError",
            message=str(e),
            code=ExitCode.ERROR,
        )
    except Exception as e:
        logger.exception("Unexpected error in lean formalize command")
        return CLIOutput.err(
            command="erdos lean formalize",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


def prove_with_aristotle(
    input_file: Path,
    output_file: Path,
    *,
    timeout: int = 600,
    informal: bool = False,
    formal_input_context: bool = False,
) -> CLIOutput:
    """Run Aristotle prove-from-file command.

    Args:
        input_file: Path to the input Lean file
        output_file: Path for the output Lean file
        timeout: Maximum seconds to wait for completion
        informal: Pass --informal flag to Aristotle
        formal_input_context: Pass --formal-input-context flag to Aristotle

    Returns:
        CLIOutput with execution details
    """
    try:
        result = run_aristotle_prove_from_file(
            input_file,
            output_file,
            timeout=timeout,
            informal=informal,
            formal_input_context=formal_input_context,
        )
        if result.success:
            return CLIOutput.ok(
                command="erdos lean prove",
                data=result.to_dict(),
            )
        else:
            # Nonzero exit code - return error with stderr
            return CLIOutput.err(
                command="erdos lean prove",
                error_type="AristotleError",
                message=result.stderr
                or f"Aristotle exited with code {result.exit_code}",
                code=ExitCode.ERROR,
            )
    except AristotleError as e:
        # Map error types to exit codes
        error_type_to_exit_code = {
            "ConfigError": ExitCode.CONFIG_ERROR,
            "NotFound": ExitCode.NOT_FOUND,
            "UsageError": ExitCode.USAGE_ERROR,
            "Timeout": ExitCode.ERROR,
        }
        exit_code = error_type_to_exit_code.get(e.error_type, ExitCode.ERROR)
        return CLIOutput.err(
            command="erdos lean prove",
            error_type=e.error_type,
            message=str(e),
            code=exit_code,
        )
    except Exception as e:
        logger.exception("Unexpected error in lean prove command")
        return CLIOutput.err(
            command="erdos lean prove",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
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
    no_mathlib: Annotated[
        bool,
        typer.Option("--no-mathlib", help="Skip fetching mathlib"),
    ] = False,
) -> None:
    """
    Initialize Lean 4 project with mathlib.

    Creates lakefile.lean, lean-toolchain, and directory structure.
    """

    with measure_time_ms() as duration:
        path = project_path or Path("formal/lean")
        path.mkdir(parents=True, exist_ok=True)
        result = init_lean_project(path, fetch_mathlib=not no_mathlib)

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)


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
) -> None:
    """
    Check a Lean file for compilation errors.

    Example: erdos lean check Erdos/Problem006.lean
    """
    with measure_time_ms() as duration:
        path = project_path or Path("formal/lean")
        result = check_lean_file(file, path)

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)

    if (
        result.success
        and isinstance(result.data, dict)
        and not result.data.get("success", True)
    ):
        raise typer.Exit(code=ExitCode.LEAN_ERROR)


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
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing file"),
    ] = False,
) -> None:
    """
    Generate a Lean skeleton for a problem.

    Creates Erdos/Problem<ID>.lean with theorem stub.
    """
    with measure_time_ms() as duration:
        app_ctx, app_error = get_app_context(ctx, command="erdos lean formalize")
        if app_error is not None:
            exit_with_result(ctx, app_error)
            return
        if app_ctx is None:
            return  # Unreachable: get_app_context guarantees (ctx, None) or (None, error)

        path = project_path or Path("formal/lean")
        result = formalize_problem(problem_id, path, repo=app_ctx.problems, force=force)

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)


@app.command()
def prove(
    ctx: typer.Context,
    input_file: Annotated[
        Path,
        typer.Argument(
            help="Lean file to prove.",
            exists=True,
            readable=True,
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output file path (required; must differ from input).",
        ),
    ],
    timeout: Annotated[
        int,
        typer.Option(
            "--timeout",
            "-t",
            help="Maximum seconds to wait for completion.",
        ),
    ] = 600,
    informal: Annotated[
        bool,
        typer.Option("--informal", help="Pass --informal flag to Aristotle."),
    ] = False,
    formal_input_context: Annotated[
        bool,
        typer.Option(
            "--formal-input-context",
            help="Pass --formal-input-context flag to Aristotle.",
        ),
    ] = False,
) -> None:
    """
    Run Aristotle prove-from-file on a Lean file.

    Requires ARISTOTLE_API_KEY environment variable to be set.
    Writes output to a separate file (never overwrites the input).

    Example: erdos lean prove Problem006.lean --output Problem006.solved.lean
    """
    # Validate output is not the same as input
    if input_file.resolve() == output.resolve():
        result = CLIOutput.err(
            command="erdos lean prove",
            error_type="UsageError",
            message="Output file cannot be the same as input file.",
            code=ExitCode.USAGE_ERROR,
        )
        exit_with_result(ctx, result, print_human=_print_human)
        return

    with measure_time_ms() as duration:
        result = prove_with_aristotle(
            input_file,
            output,
            timeout=timeout,
            informal=informal,
            formal_input_context=formal_input_context,
        )

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)
