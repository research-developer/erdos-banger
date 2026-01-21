"""erdos ask - RAG Q&A for Erdős problems (SPEC-011)."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.ask import ask_question
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.timing import measure_time_ms


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository, SearchIndexProtocol


app = typer.Typer(
    help="Ask questions about Erdős problems using RAG.",
    context_settings={"allow_interspersed_args": True},
)
console = Console()
err_console = Console(stderr=True)


@dataclass
class AskOptions:
    """Options for the ask command."""

    problem_id: int
    question: str
    limit: int
    build_index: bool
    no_llm: bool
    llm_cmd: str | None


def _read_question_from_stdin() -> str:
    """Read question text from stdin, trimming single trailing newline."""
    question = sys.stdin.read()
    if question.endswith("\n"):
        question = question[:-1]
    return question


def _validate_question_input(question: str) -> CLIOutput | None:
    """
    Validate question is non-empty.

    Returns None if valid, CLIOutput error if invalid.
    """
    if not question.strip():
        return CLIOutput.err(
            command="erdos ask",
            error_type="UsageError",
            message="Question cannot be empty",
            code=ExitCode.USAGE_ERROR,
        )
    return None


def _show_progress_message(problem_id: int, json_output: bool) -> None:
    """Show progress message (only in human mode)."""
    if not json_output:
        err_console.print(f"[dim]Retrieving sources for Problem {problem_id}...[/dim]")


def _execute_ask_query(
    options: AskOptions,
    *,
    repo: ProblemRepository,
    index: SearchIndexProtocol,
) -> CLIOutput:
    """Execute the ask query and return result with timing."""
    with measure_time_ms() as duration:
        result = ask_question(
            problem_id=options.problem_id,
            question=options.question,
            repo=repo,
            index=index,
            limit=options.limit,
            build_index_flag=options.build_index,
            no_llm=options.no_llm,
            llm_command=options.llm_cmd,
        )
    result.duration_ms = duration[0]
    return result


def _print_human(result_data: dict[str, Any]) -> None:
    """Pretty-print ask results."""
    problem_id = result_data.get("problem_id", "?")
    question = result_data.get("question", "")
    answer = result_data.get("answer")
    sources = result_data.get("sources", [])
    llm = result_data.get("llm", {})

    # Header
    console.print(f"\n[bold]Problem {problem_id}[/bold]")
    console.print(f"[dim]Question: {question}[/dim]\n")

    # Sources section
    console.print(f"[bold cyan]Retrieved {len(sources)} sources:[/bold cyan]")
    if sources:
        for source in sources:
            rank = source.get("rank", "?")
            source_type = source.get("source_type", "?")
            chunk_id = source.get("chunk_id", "?")
            text_preview = (source.get("text") or "")[:100]
            console.print(f"  [{rank}] ({source_type}) {chunk_id}")
            console.print(f"      {text_preview}...")
    else:
        console.print("  [dim](no sources found)[/dim]")

    console.print()

    # Answer section
    if answer:
        console.print("[bold green]Answer:[/bold green]")
        # Render answer as markdown for better formatting
        console.print(Panel(Markdown(answer), border_style="green"))
    else:
        console.print("[yellow]No answer generated (prompt-only mode)[/yellow]")
        console.print("[dim]Use ERDOS_LLM_COMMAND or --llm-cmd to enable LLM.[/dim]")

    # LLM info
    if llm.get("enabled"):
        llm_cmd = llm.get("command", "?")
        exit_code = llm.get("exit_code", "?")
        console.print(f"\n[dim]LLM: {llm_cmd} (exit: {exit_code})[/dim]")


@app.callback(invoke_without_command=True)
def ask(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    question_arg: Annotated[str, typer.Argument(help="Question or '-' for stdin")],
    limit: Annotated[int, typer.Option("--limit", "-n")] = 5,
    build_index: Annotated[bool, typer.Option("--build-index")] = False,
    no_llm: Annotated[bool, typer.Option("--no-llm")] = False,
    llm_cmd: Annotated[str, typer.Option("--llm-cmd")] = "",
) -> None:
    """
    Ask a question about an Erdős problem using RAG.

    Retrieves relevant text chunks from the search index,
    builds a citation-grounded prompt, and optionally runs
    an external LLM to generate an answer.

    Examples:

        erdos ask 6 "What partial results are known?" --no-llm

        ERDOS_LLM_COMMAND="./scripts/llm.sh" erdos ask 6 "Summarize known results"

        echo "What is the status?" | erdos --json ask 6 -
    """
    json_mode = bool((ctx.obj or {}).get("json"))

    # Get and validate question
    question = _read_question_from_stdin() if question_arg == "-" else question_arg
    if validation_error := _validate_question_input(question):
        exit_with_result(ctx, validation_error)
        return

    # Execute query
    _show_progress_message(problem_id, json_mode)
    options = AskOptions(
        problem_id=problem_id,
        question=question,
        limit=limit,
        build_index=build_index,
        no_llm=no_llm,
        llm_cmd=llm_cmd if llm_cmd else None,
    )
    app_ctx, app_error = get_app_context(ctx, command="erdos ask", require_index=True)
    if app_error is not None or app_ctx is None:
        exit_with_result(ctx, app_error)  # type: ignore[arg-type]
        return

    result = _execute_ask_query(
        options, repo=app_ctx.problems, index=app_ctx.ensure_index()
    )
    exit_with_result(ctx, result, print_human=_print_human)
