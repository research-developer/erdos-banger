"""Workspace-level commands for `erdos research` (Spec 023)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.research import (
    append_scratchpad_entry,
    ensure_problem_workspace,
    fmt_problem_workspace,
    get_problem_dir,
    get_problem_status,
    synthesize_problem,
    validate_problem_workspace,
)

from ._common import handle_store_error, load_problem_or_error, read_text_arg


if TYPE_CHECKING:
    from pathlib import Path


def _require_workspace_dir(
    ctx: typer.Context, *, problem_id: int, command: str, repo_root: Path | None
) -> bool:
    s = get_problem_status(problem_id, repo_root=repo_root)
    if s.problem_dir.exists():
        return True
    exit_with_result(
        ctx,
        CLIOutput.err(
            command=command,
            error_type="NotInitialized",
            message=f"Research workspace not initialized for problem {problem_id}. Run: erdos research init {problem_id}",
            code=ExitCode.NOT_FOUND,
        ),
    )
    return False


def init(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
) -> None:
    """Initialize the research workspace for a problem."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research init")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return

    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research init"
    ):
        exit_with_result(ctx, error)
        return

    result = ensure_problem_workspace(problem_id, repo_root=app_ctx.config.repo_root)
    data = {
        "problem_id": problem_id,
        "research_root": str(result.research_root),
        "problem_dir": str(result.problem_dir),
        "created": result.created,
        "created_paths": list(result.created_paths),
        "workspace_version": result.workspace_version,
    }
    exit_with_result(ctx, CLIOutput.ok(command="erdos research init", data=data))


def open(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
) -> None:
    """Print the absolute path to the per-problem research workspace.

    This command intentionally does not require the workspace to exist yet.
    """
    app_ctx, app_error = get_app_context(ctx, command="erdos research open")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return

    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research open"
    ):
        exit_with_result(ctx, error)
        return

    problem_dir = get_problem_dir(app_ctx.config.repo_root, problem_id)
    problem_dir_str = str(problem_dir.resolve(strict=False))

    data = {"problem_id": problem_id, "problem_dir": problem_dir_str}
    exit_with_result(ctx, CLIOutput.ok(command="erdos research open", data=data))


def note(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    text_arg: Annotated[
        str, typer.Argument(help="Note text, or '-' to read from stdin")
    ],
) -> None:
    """Append a note to the per-problem scratchpad."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research note")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return

    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research note"
    ):
        exit_with_result(ctx, error)
        return

    if not _require_workspace_dir(
        ctx,
        problem_id=problem_id,
        command="erdos research note",
        repo_root=app_ctx.config.repo_root,
    ):
        return

    text = read_text_arg(text_arg)
    if not text.strip():
        exit_with_result(
            ctx,
            CLIOutput.err(
                command="erdos research note",
                error_type="UsageError",
                message="Note cannot be empty",
                code=ExitCode.USAGE_ERROR,
            ),
        )
        return

    res = append_scratchpad_entry(problem_id, text, repo_root=app_ctx.config.repo_root)
    data = {
        "problem_id": problem_id,
        "scratchpad_path": str(res.scratchpad_path),
        "appended_bytes": res.appended_bytes,
    }
    exit_with_result(ctx, CLIOutput.ok(command="erdos research note", data=data))


def status(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
) -> None:
    """Show a minimal dashboard for the research workspace."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research status")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return

    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research status"
    ):
        exit_with_result(ctx, error)
        return

    if not _require_workspace_dir(
        ctx,
        problem_id=problem_id,
        command="erdos research status",
        repo_root=app_ctx.config.repo_root,
    ):
        return

    s = get_problem_status(problem_id, repo_root=app_ctx.config.repo_root)
    data = {
        "problem_id": problem_id,
        "problem_dir": str(s.problem_dir),
        "files": s.files,
        "counts": s.counts,
    }
    exit_with_result(ctx, CLIOutput.ok(command="erdos research status", data=data))


def fmt(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
) -> None:
    """Rewrite YAML records into canonical formatting."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research fmt")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return
    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research fmt"
    ):
        exit_with_result(ctx, error)
        return
    if not _require_workspace_dir(
        ctx,
        problem_id=problem_id,
        command="erdos research fmt",
        repo_root=app_ctx.config.repo_root,
    ):
        return

    try:
        rewritten = fmt_problem_workspace(
            problem_id, repo_root=app_ctx.config.repo_root
        )
    except Exception as e:  # map store failures to CLIOutput
        exit_with_result(ctx, handle_store_error("erdos research fmt", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research fmt",
            data={"problem_id": problem_id, "rewritten": rewritten},
        ),
    )


def validate(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
) -> None:
    """Validate all YAML records in the workspace."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research validate")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return
    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research validate"
    ):
        exit_with_result(ctx, error)
        return
    if not _require_workspace_dir(
        ctx,
        problem_id=problem_id,
        command="erdos research validate",
        repo_root=app_ctx.config.repo_root,
    ):
        return

    try:
        validate_problem_workspace(problem_id, repo_root=app_ctx.config.repo_root)
    except Exception as e:  # map store failures to CLIOutput
        exit_with_result(ctx, handle_store_error("erdos research validate", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research validate", data={"problem_id": problem_id}
        ),
    )


def synthesize(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
) -> None:
    """Generate/update `SYNTHESIS.md` deterministically (no LLM)."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research synthesize")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return
    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research synthesize"
    ):
        exit_with_result(ctx, error)
        return
    if not _require_workspace_dir(
        ctx,
        problem_id=problem_id,
        command="erdos research synthesize",
        repo_root=app_ctx.config.repo_root,
    ):
        return

    try:
        res = synthesize_problem(problem_id, repo_root=app_ctx.config.repo_root)
    except Exception as e:  # map store failures to CLIOutput
        exit_with_result(ctx, handle_store_error("erdos research synthesize", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research synthesize",
            data={
                "problem_id": problem_id,
                "synthesis_path": str(res.synthesis_path.resolve()),
                "written_bytes": res.written_bytes,
                "counts": res.counts,
            },
        ),
    )


def register(app: typer.Typer) -> None:
    """Register research workspace commands on the app."""
    app.command()(init)
    app.command()(open)
    app.command()(note)
    app.command()(status)
    app.command()(fmt)
    app.command()(validate)
    app.command()(synthesize)
