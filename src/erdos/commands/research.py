"""erdos research - filesystem research workspace and state (v3)."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Annotated

import typer

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.problem_loader import ProblemLoaderError
from erdos.core.research import (
    FSResearchStore,
    append_scratchpad_entry,
    ensure_problem_workspace,
    fmt_problem_workspace,
    get_problem_dir,
    get_problem_status,
    synthesize_problem,
    validate_problem_workspace,
)
from erdos.core.research.errors import (
    ResearchRecordInvalidError,
    ResearchRecordNotFoundError,
)
from erdos.core.research.models import (
    AttemptKind,
    AttemptResult,
    Confidence,
    HypothesisStatus,
    LeadStatus,
    Priority,
    TaskStatus,
)


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository


app = typer.Typer(help="Manage per-problem research workspace and state.")
lead_app = typer.Typer(help="Manage leads.")
hypothesis_app = typer.Typer(help="Manage hypotheses.")
task_app = typer.Typer(help="Manage tasks.")
attempt_app = typer.Typer(help="Manage attempts.")


def _read_text_arg(text_arg: str) -> str:
    if text_arg != "-":
        return text_arg
    text = sys.stdin.read()
    if text.endswith("\n"):
        text = text[:-1]
    return text


def _load_problem_or_error(
    problem_id: int, *, repo: ProblemRepository, command: str
) -> CLIOutput | None:
    try:
        problem = repo.get_by_id(problem_id)
    except ProblemLoaderError as e:
        return CLIOutput.err(
            command=command,
            error_type="LoaderError",
            message=str(e),
            code=ExitCode.ERROR,
        )
    if problem is None:
        return CLIOutput.err(
            command=command,
            error_type="NotFound",
            message=f"Problem {problem_id} not found",
            code=ExitCode.NOT_FOUND,
        )
    return None


def _handle_store_error(command: str, exc: Exception) -> CLIOutput:
    if isinstance(exc, ResearchRecordNotFoundError):
        return CLIOutput.err(
            command=command,
            error_type="NotFound",
            message=str(exc),
            code=ExitCode.NOT_FOUND,
        )
    if isinstance(exc, ResearchRecordInvalidError):
        return CLIOutput.err(
            command=command,
            error_type="InvalidRecord",
            message=str(exc),
            code=ExitCode.ERROR,
        )
    return CLIOutput.err(
        command=command,
        error_type="ResearchError",
        message=str(exc),
        code=ExitCode.ERROR,
    )


@app.command()
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

    if error := _load_problem_or_error(
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


@app.command()
def open(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
) -> None:
    """Print the absolute path to the per-problem research workspace."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research open")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return

    if error := _load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research open"
    ):
        exit_with_result(ctx, error)
        return

    problem_dir = get_problem_dir(app_ctx.config.repo_root, problem_id)
    problem_dir_str = str(problem_dir.resolve(strict=False))

    data = {"problem_id": problem_id, "problem_dir": problem_dir_str}
    exit_with_result(ctx, CLIOutput.ok(command="erdos research open", data=data))


@app.command()
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

    if error := _load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research note"
    ):
        exit_with_result(ctx, error)
        return

    text = _read_text_arg(text_arg)
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


@app.command()
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

    if error := _load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research status"
    ):
        exit_with_result(ctx, error)
        return

    s = get_problem_status(problem_id, repo_root=app_ctx.config.repo_root)
    if not s.problem_dir.exists():
        exit_with_result(
            ctx,
            CLIOutput.err(
                command="erdos research status",
                error_type="NotInitialized",
                message=f"Research workspace not initialized for problem {problem_id}. Run: erdos research init {problem_id}",
                code=ExitCode.NOT_FOUND,
            ),
        )
        return

    data = {
        "problem_id": problem_id,
        "problem_dir": str(s.problem_dir),
        "files": s.files,
        "counts": s.counts,
    }
    exit_with_result(ctx, CLIOutput.ok(command="erdos research status", data=data))


@app.command()
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
    if error := _load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research fmt"
    ):
        exit_with_result(ctx, error)
        return
    try:
        rewritten = fmt_problem_workspace(
            problem_id, repo_root=app_ctx.config.repo_root
        )
    except Exception as e:
        exit_with_result(ctx, _handle_store_error("erdos research fmt", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research fmt",
            data={"problem_id": problem_id, "rewritten": rewritten},
        ),
    )


@app.command()
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
    if error := _load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research validate"
    ):
        exit_with_result(ctx, error)
        return

    try:
        validate_problem_workspace(problem_id, repo_root=app_ctx.config.repo_root)
    except Exception as e:
        exit_with_result(ctx, _handle_store_error("erdos research validate", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research validate", data={"problem_id": problem_id}
        ),
    )


@app.command()
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
    if error := _load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research synthesize"
    ):
        exit_with_result(ctx, error)
        return

    try:
        res = synthesize_problem(problem_id, repo_root=app_ctx.config.repo_root)
    except Exception as e:
        exit_with_result(ctx, _handle_store_error("erdos research synthesize", e))
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


@lead_app.command("add")
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
    if error := _load_problem_or_error(
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
        exit_with_result(ctx, _handle_store_error("erdos research lead add", e))
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


@lead_app.command("list")
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
    if error := _load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research lead list"
    ):
        exit_with_result(ctx, error)
        return
    store = FSResearchStore(repo_root=app_ctx.config.repo_root)
    try:
        records = store.lead_list(problem_id, status=status, priority=priority)
    except Exception as e:
        exit_with_result(ctx, _handle_store_error("erdos research lead list", e))
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


@lead_app.command("update")
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
    if error := _load_problem_or_error(
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
        exit_with_result(ctx, _handle_store_error("erdos research lead update", e))
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


@hypothesis_app.command("add")
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
    if error := _load_problem_or_error(
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
    except Exception as e:
        exit_with_result(ctx, _handle_store_error("erdos research hypothesis add", e))
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


@hypothesis_app.command("list")
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
    if error := _load_problem_or_error(
        problem_id,
        repo=app_ctx.problems,
        command="erdos research hypothesis list",
    ):
        exit_with_result(ctx, error)
        return
    store = FSResearchStore(repo_root=app_ctx.config.repo_root)
    try:
        records = store.hypothesis_list(problem_id, status=status)
    except Exception as e:
        exit_with_result(ctx, _handle_store_error("erdos research hypothesis list", e))
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


@hypothesis_app.command("update")
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
    if error := _load_problem_or_error(
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
    except Exception as e:
        exit_with_result(
            ctx, _handle_store_error("erdos research hypothesis update", e)
        )
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


@task_app.command("add")
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
    if error := _load_problem_or_error(
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
        exit_with_result(ctx, _handle_store_error("erdos research task add", e))
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


@task_app.command("list")
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
    if error := _load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research task list"
    ):
        exit_with_result(ctx, error)
        return
    store = FSResearchStore(repo_root=app_ctx.config.repo_root)
    try:
        records = store.task_list(problem_id, status=status, priority=priority)
    except Exception as e:
        exit_with_result(ctx, _handle_store_error("erdos research task list", e))
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


@task_app.command("update")
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
    if error := _load_problem_or_error(
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
        exit_with_result(ctx, _handle_store_error("erdos research task update", e))
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


@attempt_app.command("log")
def attempt_log(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    result: Annotated[AttemptResult, typer.Option("--result")],
    summary: Annotated[str, typer.Option("--summary")],
    kind: Annotated[AttemptKind, typer.Option("--kind")] = AttemptKind.LEAN_LOOP,
    lean_file: Annotated[str | None, typer.Option("--lean-file")] = None,
    loop_log: Annotated[str | None, typer.Option("--loop-log")] = None,
) -> None:
    """Log an attempt record."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research attempt log")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return
    if error := _load_problem_or_error(
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
        exit_with_result(ctx, _handle_store_error("erdos research attempt log", e))
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


@attempt_app.command("list")
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
    if error := _load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research attempt list"
    ):
        exit_with_result(ctx, error)
        return
    store = FSResearchStore(repo_root=app_ctx.config.repo_root)
    try:
        records = store.attempt_list(problem_id, result=result)
    except Exception as e:
        exit_with_result(ctx, _handle_store_error("erdos research attempt list", e))
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


app.add_typer(lead_app, name="lead")
app.add_typer(hypothesis_app, name="hypothesis")
app.add_typer(task_app, name="task")
app.add_typer(attempt_app, name="attempt")
