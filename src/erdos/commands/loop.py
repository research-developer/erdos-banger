"""erdos loop - Iterative Lean proof attempts.

LLM routing per SPEC-032: uses TaskType.loop_patch to select the appropriate
LLM command via environment variable chain (ERDOS_LLM_COMMAND_CODE -> ERDOS_LLM_COMMAND).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import console, exit_with_result
from erdos.core.constants import DEFAULT_RAG_LIMIT, LEAN_COMPILE_TIMEOUT
from erdos.core.exit_codes import ExitCode
from erdos.core.llm import LLMRouterError, TaskType, resolve_llm_command
from erdos.core.loop import LoopConfig, execute_proof_loop
from erdos.core.models import CLIOutput
from erdos.core.timing import measure_time_ms


app = typer.Typer(help="Iterative Lean proof loop.")


def _print_human_result(result_data: dict[str, Any]) -> None:
    """Pretty-print loop result."""
    status = result_data.get("status", "unknown")
    problem_id = result_data.get("problem_id")
    iterations = result_data.get("iterations_completed", 0)
    max_iter = result_data.get("iterations_max", 0)
    file_path = result_data.get("file", "")

    if status == "success":
        console.print(f"[green]✓[/green] Problem {problem_id} proof complete!")
        console.print(f"  File: {file_path}")
        console.print(f"  Iterations: {iterations}/{max_iter}")
    elif status == "no_fix_possible":
        console.print(f"[yellow]![/yellow] No fix possible for problem {problem_id}")
        console.print("  The LLM indicated it cannot fix the current state.")
    elif status == "max_iterations":
        console.print(
            f"[yellow]![/yellow] Reached maximum iterations ({max_iter}) "
            f"for problem {problem_id}"
        )
    elif status == "llm_required":
        console.print(
            f"[yellow]![/yellow] LLM required but not configured for problem {problem_id}"
        )
        console.print(
            "  Set ERDOS_LLM_COMMAND or use --llm-cmd to specify an LLM command."
        )
    elif status == "no_progress":
        console.print(
            f"[yellow]![/yellow] No progress after {iterations} iterations "
            f"for problem {problem_id}"
        )
    elif status == "regression":
        console.print(f"[red]✗[/red] Regression detected for problem {problem_id}")
        console.print("  File size shrank unexpectedly (possible deletion attack).")
    else:
        console.print(f"[red]✗[/red] Loop failed for problem {problem_id}: {status}")

    # Show iteration details
    iter_records = result_data.get("iterations", [])
    if iter_records:
        console.print("\nIterations:")
        for rec in iter_records:
            patch_str = (
                "[green]applied[/green]"
                if rec.get("patch_applied")
                else "[dim]skipped[/dim]"
            )
            sorry_before = rec.get("sorry_before", "?")
            sorry_after = rec.get("sorry_after", "?")
            console.print(
                f"  [{rec['iteration']}] {patch_str} "
                f"sorry: {sorry_before} → {sorry_after}"
            )


@app.command()
def run(
    ctx: typer.Context,
    problem_id: Annotated[
        int,
        typer.Argument(
            help="Problem ID to work on.",
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
    max_iter: Annotated[
        int,
        typer.Option(
            "--max-iter",
            "-n",
            help="Maximum iterations (default: 10).",
            min=1,
        ),
    ] = 10,
    no_apply: Annotated[
        bool,
        typer.Option(
            "--no-apply",
            help="Propose changes only; never write to disk.",
        ),
    ] = False,
    timeout: Annotated[
        int,
        typer.Option(
            "--timeout",
            help=f"Lean check timeout in seconds (default: {LEAN_COMPILE_TIMEOUT}).",
            min=1,
        ),
    ] = LEAN_COMPILE_TIMEOUT,
    allow_sorry_increase: Annotated[
        int,
        typer.Option(
            "--allow-sorry-increase",
            help="Allow patch to increase sorry count by up to N (default: 0).",
            min=0,
        ),
    ] = 0,
    max_patch_lines: Annotated[
        int,
        typer.Option(
            "--max-patch-lines",
            help="Reject patches larger than this many lines (default: 50).",
            min=1,
        ),
    ] = 50,
    max_patch_bytes: Annotated[
        int,
        typer.Option(
            "--max-patch-bytes",
            help="Reject patches larger than this many bytes (default: 8192).",
            min=1,
        ),
    ] = 8192,
    rag_limit: Annotated[
        int,
        typer.Option(
            "--rag-limit",
            help=f"Maximum retrieved context chunks in prompt (default: {DEFAULT_RAG_LIMIT}).",
            min=0,
        ),
    ] = DEFAULT_RAG_LIMIT,
    llm_cmd: Annotated[
        str | None,
        typer.Option(
            "--llm-cmd",
            help="Override LLM command (default: from ERDOS_LLM_COMMAND env var).",
        ),
    ] = None,
) -> None:
    """
    Run iterative proof loop for a problem.

    This command runs an iterative "propose → apply → check" cycle to assist
    Lean formalization. Each iteration:

    1. Checks the current Lean file for errors
    2. Builds a prompt with the file, errors, and problem context
    3. Calls an external LLM to propose a fix
    4. Validates and applies the fix (if --no-apply is not set)
    5. Repeats until success or max iterations

    Safety guardrails:
    - Only modifies files under formal/lean/Erdos/
    - Rejects patches that add sorry or admit (by default)
    - Rejects patches larger than configured limits
    - Aborts if file shrinks by > 20%

    Example (propose only; does not write to disk):

        ERDOS_LLM_COMMAND="./scripts/llm.sh" erdos loop run 6 --no-apply

    Example (auto-apply):

        ERDOS_LLM_COMMAND="./scripts/llm.sh" erdos loop run 6
    """
    with measure_time_ms() as duration:
        app_ctx, app_error = get_app_context(ctx, command="erdos loop")
        if app_error is not None:
            exit_with_result(ctx, app_error)
            return
        if app_ctx is None:
            return  # Unreachable

        path = project_path or Path("formal/lean")

        # Resolve LLM command via router (SPEC-032)
        # - --llm-cmd: explicit override bypasses router
        # - otherwise: use router with TaskType.loop_patch
        try:
            # Pass llm_cmd as override - router uses it if non-empty, else checks env vars
            llm_command = resolve_llm_command(
                TaskType.loop_patch,
                override=llm_cmd,
            )
        except LLMRouterError as e:
            exit_with_result(
                ctx,
                CLIOutput.err(
                    command="erdos loop",
                    error_type="ConfigError",
                    message=str(e),
                    code=ExitCode.CONFIG_ERROR,
                ),
            )
            return

        config = LoopConfig.from_cli(
            max_iterations=max_iter,
            lean_timeout_seconds=timeout,
            allow_sorry_increase=allow_sorry_increase,
            max_patch_lines=max_patch_lines,
            max_patch_bytes=max_patch_bytes,
            rag_limit=rag_limit,
        )

        result = execute_proof_loop(
            problem_id,
            repo=app_ctx.problems,
            project_path=path,
            config=config,
            llm_command=llm_command,
            no_apply=no_apply,
            repo_root=app_ctx.config.repo_root,
        )

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human_result)
