"""Attempt commands for `erdos research` (Spec 024)."""

from __future__ import annotations

from typing import Annotated

import typer

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.models import CLIOutput
from erdos.core.research import FSResearchStore
from erdos.core.research.models import AttemptKind, AttemptResult

from ._common import handle_store_error, load_problem_or_error


app = typer.Typer(help="Manage attempts.")


@app.command("log")
def attempt_log(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    result: Annotated[AttemptResult, typer.Option("--result")],
    summary: Annotated[str, typer.Option("--summary")],
    kind: Annotated[AttemptKind, typer.Option("--kind")] = AttemptKind.LEAN_LOOP,
    lean_file: Annotated[str | None, typer.Option("--lean-file")] = None,
    loop_log: Annotated[
        str | None, typer.Option("--loop-run-log", "--loop-log")
    ] = None,
) -> None:
    """Log an attempt record."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research attempt log")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return
    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research attempt log"
    ):
        exit_with_result(ctx, error)
        return
    store = FSResearchStore(repo_root=app_ctx.config.repo_root)
    try:
        record, path = store.attempt_log(
            problem_id,
            result=result,
            summary=summary,
            kind=kind,
            lean_file=lean_file,
            loop_log=loop_log,
        )
    except Exception as e:
        exit_with_result(ctx, handle_store_error("erdos research attempt log", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research attempt log",
            data={
                "problem_id": problem_id,
                "record_kind": "attempt",
                "path": str(path.resolve()),
                "record": record.model_dump(mode="json"),
            },
        ),
    )


@app.command("list")
def attempt_list(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    result: Annotated[AttemptResult | None, typer.Option("--result")] = None,
) -> None:
    """List attempt records."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research attempt list")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return
    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research attempt list"
    ):
        exit_with_result(ctx, error)
        return
    store = FSResearchStore(repo_root=app_ctx.config.repo_root)
    try:
        records = store.attempt_list(problem_id, result=result)
    except Exception as e:
        exit_with_result(ctx, handle_store_error("erdos research attempt list", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research attempt list",
            data={
                "problem_id": problem_id,
                "record_kind": "attempt",
                "records": [r.model_dump(mode="json") for r in records],
            },
        ),
    )
