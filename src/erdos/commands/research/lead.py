"""Lead commands for `erdos research` (Spec 024)."""

from __future__ import annotations

from typing import Annotated

import typer

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.research import FSResearchStore
from erdos.core.research.models import LeadStatus, Priority

from ._common import handle_store_error, load_problem_or_error


app = typer.Typer(help="Manage leads.")


@app.command("add")
def lead_add(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    title: Annotated[str, typer.Option("--title", help="Lead title")],
    doi: Annotated[str | None, typer.Option("--doi")] = None,
    arxiv_id: Annotated[str | None, typer.Option("--arxiv-id")] = None,
    url: Annotated[str | None, typer.Option("--url")] = None,
    status: Annotated[LeadStatus, typer.Option("--status")] = LeadStatus.NEW,
    priority: Annotated[Priority, typer.Option("--priority")] = Priority.MEDIUM,
    notes: Annotated[str, typer.Option("--notes")] = "",
) -> None:
    """Add a lead record."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research lead add")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return
    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research lead add"
    ):
        exit_with_result(ctx, error)
        return
    store = FSResearchStore(repo_root=app_ctx.config.repo_root)
    try:
        record, path = store.lead_add(
            problem_id,
            title=title,
            doi=doi,
            arxiv_id=arxiv_id,
            url=url,
            status=status,
            priority=priority,
            notes=notes,
        )
    except Exception as e:
        exit_with_result(ctx, handle_store_error("erdos research lead add", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research lead add",
            data={
                "problem_id": problem_id,
                "record_kind": "lead",
                "path": str(path.resolve()),
                "record": record.model_dump(mode="json"),
            },
        ),
    )


@app.command("list")
def lead_list(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    status: Annotated[LeadStatus | None, typer.Option("--status")] = None,
    priority: Annotated[Priority | None, typer.Option("--priority")] = None,
) -> None:
    """List lead records."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research lead list")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return
    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research lead list"
    ):
        exit_with_result(ctx, error)
        return
    store = FSResearchStore(repo_root=app_ctx.config.repo_root)
    try:
        records = store.lead_list(problem_id, status=status, priority=priority)
    except Exception as e:
        exit_with_result(ctx, handle_store_error("erdos research lead list", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research lead list",
            data={
                "problem_id": problem_id,
                "record_kind": "lead",
                "records": [r.model_dump(mode="json") for r in records],
            },
        ),
    )


@app.command("update")
def lead_update(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    lead_id: Annotated[str, typer.Argument(help="Lead ID (filename stem)")],
    status: Annotated[LeadStatus | None, typer.Option("--status")] = None,
    priority: Annotated[Priority | None, typer.Option("--priority")] = None,
    notes: Annotated[str | None, typer.Option("--notes")] = None,
) -> None:
    """Update a lead record."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research lead update")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return
    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research lead update"
    ):
        exit_with_result(ctx, error)
        return
    if status is None and priority is None and notes is None:
        exit_with_result(
            ctx,
            CLIOutput.err(
                command="erdos research lead update",
                error_type="UsageError",
                message="At least one of --status, --priority, or --notes is required",
                code=ExitCode.USAGE_ERROR,
            ),
        )
        return
    store = FSResearchStore(repo_root=app_ctx.config.repo_root)
    try:
        record, path = store.lead_update(
            problem_id, lead_id, status=status, priority=priority, notes=notes
        )
    except Exception as e:
        exit_with_result(ctx, handle_store_error("erdos research lead update", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research lead update",
            data={
                "problem_id": problem_id,
                "record_kind": "lead",
                "path": str(path.resolve()),
                "record": record.model_dump(mode="json"),
            },
        ),
    )
