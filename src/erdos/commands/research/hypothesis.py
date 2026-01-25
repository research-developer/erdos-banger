"""Hypothesis commands for `erdos research` (Spec 024)."""

from __future__ import annotations

from typing import Annotated

import typer

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.research import FSResearchStore
from erdos.core.research.models import Confidence, HypothesisStatus

from ._common import handle_store_error, load_problem_or_error


app = typer.Typer(help="Manage hypotheses.")


@app.command("add")
def hypothesis_add(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    statement: Annotated[str, typer.Option("--statement", help="Hypothesis statement")],
    status: Annotated[
        HypothesisStatus, typer.Option("--status")
    ] = HypothesisStatus.ACTIVE,
    confidence: Annotated[Confidence, typer.Option("--confidence")] = Confidence.MEDIUM,
    notes: Annotated[str, typer.Option("--notes")] = "",
) -> None:
    """Add a hypothesis record."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research hypothesis add")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return
    if error := load_problem_or_error(
        problem_id,
        repo=app_ctx.problems,
        command="erdos research hypothesis add",
    ):
        exit_with_result(ctx, error)
        return
    store = FSResearchStore(repo_root=app_ctx.config.repo_root)
    try:
        record, path = store.hypothesis_add(
            problem_id,
            statement=statement,
            status=status,
            confidence=confidence,
            notes=notes,
        )
    except Exception as e:  # map store failures to CLIOutput
        exit_with_result(ctx, handle_store_error("erdos research hypothesis add", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research hypothesis add",
            data={
                "problem_id": problem_id,
                "record_kind": "hypothesis",
                "path": str(path.resolve()),
                "record": record.model_dump(mode="json"),
            },
        ),
    )


@app.command("list")
def hypothesis_list(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    status: Annotated[HypothesisStatus | None, typer.Option("--status")] = None,
) -> None:
    """List hypothesis records."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research hypothesis list")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return
    if error := load_problem_or_error(
        problem_id,
        repo=app_ctx.problems,
        command="erdos research hypothesis list",
    ):
        exit_with_result(ctx, error)
        return
    store = FSResearchStore(repo_root=app_ctx.config.repo_root)
    try:
        records = store.hypothesis_list(problem_id, status=status)
    except Exception as e:  # map store failures to CLIOutput
        exit_with_result(ctx, handle_store_error("erdos research hypothesis list", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research hypothesis list",
            data={
                "problem_id": problem_id,
                "record_kind": "hypothesis",
                "records": [r.model_dump(mode="json") for r in records],
            },
        ),
    )


@app.command("update")
def hypothesis_update(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    hyp_id: Annotated[str, typer.Argument(help="Hypothesis ID (filename stem)")],
    status: Annotated[HypothesisStatus | None, typer.Option("--status")] = None,
    confidence: Annotated[Confidence | None, typer.Option("--confidence")] = None,
    notes: Annotated[str | None, typer.Option("--notes")] = None,
) -> None:
    """Update a hypothesis record."""
    app_ctx, app_error = get_app_context(
        ctx, command="erdos research hypothesis update"
    )
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return
    if error := load_problem_or_error(
        problem_id,
        repo=app_ctx.problems,
        command="erdos research hypothesis update",
    ):
        exit_with_result(ctx, error)
        return
    if status is None and confidence is None and notes is None:
        exit_with_result(
            ctx,
            CLIOutput.err(
                command="erdos research hypothesis update",
                error_type="UsageError",
                message="At least one of --status, --confidence, or --notes is required",
                code=ExitCode.USAGE_ERROR,
            ),
        )
        return
    store = FSResearchStore(repo_root=app_ctx.config.repo_root)
    try:
        record, path = store.hypothesis_update(
            problem_id,
            hyp_id,
            status=status,
            confidence=confidence,
            notes=notes,
        )
    except Exception as e:  # map store failures to CLIOutput
        exit_with_result(ctx, handle_store_error("erdos research hypothesis update", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research hypothesis update",
            data={
                "problem_id": problem_id,
                "record_kind": "hypothesis",
                "path": str(path.resolve()),
                "record": record.model_dump(mode="json"),
            },
        ),
    )
