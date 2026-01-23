"""Task commands for `erdos research` (Spec 024)."""

from __future__ import annotations

from typing import Annotated

import typer

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.research import FSResearchStore
from erdos.core.research.models import Priority, TaskStatus

from ._common import handle_store_error, load_problem_or_error


app = typer.Typer(help="Manage tasks.")


@app.command("add")
def task_add(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    title: Annotated[str, typer.Option("--title", help="Task title")],
    status: Annotated[TaskStatus, typer.Option("--status")] = TaskStatus.TODO,
    priority: Annotated[Priority, typer.Option("--priority")] = Priority.MEDIUM,
) -> None:
    """Add a task record."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research task add")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return
    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research task add"
    ):
        exit_with_result(ctx, error)
        return
    store = FSResearchStore(repo_root=app_ctx.config.repo_root)
    try:
        record, path = store.task_add(
            problem_id,
            title=title,
            status=status,
            priority=priority,
        )
    except Exception as e:
        exit_with_result(ctx, handle_store_error("erdos research task add", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research task add",
            data={
                "problem_id": problem_id,
                "record_kind": "task",
                "path": str(path.resolve()),
                "record": record.model_dump(mode="json"),
            },
        ),
    )


@app.command("list")
def task_list(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    status: Annotated[TaskStatus | None, typer.Option("--status")] = None,
    priority: Annotated[Priority | None, typer.Option("--priority")] = None,
) -> None:
    """List task records."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research task list")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return
    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research task list"
    ):
        exit_with_result(ctx, error)
        return
    store = FSResearchStore(repo_root=app_ctx.config.repo_root)
    try:
        records = store.task_list(problem_id, status=status, priority=priority)
    except Exception as e:
        exit_with_result(ctx, handle_store_error("erdos research task list", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research task list",
            data={
                "problem_id": problem_id,
                "record_kind": "task",
                "records": [r.model_dump(mode="json") for r in records],
            },
        ),
    )


@app.command("update")
def task_update(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    task_id: Annotated[str, typer.Argument(help="Task ID (filename stem)")],
    status: Annotated[TaskStatus | None, typer.Option("--status")] = None,
    priority: Annotated[Priority | None, typer.Option("--priority")] = None,
) -> None:
    """Update a task record."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research task update")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return
    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research task update"
    ):
        exit_with_result(ctx, error)
        return
    if status is None and priority is None:
        exit_with_result(
            ctx,
            CLIOutput.err(
                command="erdos research task update",
                error_type="UsageError",
                message="At least one of --status or --priority is required",
                code=ExitCode.USAGE_ERROR,
            ),
        )
        return
    store = FSResearchStore(repo_root=app_ctx.config.repo_root)
    try:
        record, path = store.task_update(
            problem_id, task_id, status=status, priority=priority
        )
    except Exception as e:
        exit_with_result(ctx, handle_store_error("erdos research task update", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research task update",
            data={
                "problem_id": problem_id,
                "record_kind": "task",
                "path": str(path.resolve()),
                "record": record.model_dump(mode="json"),
            },
        ),
    )
