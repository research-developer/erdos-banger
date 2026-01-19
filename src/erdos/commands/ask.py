"""erdos ask - RAG Q&A for Erdős problems (SPEC-011)."""

from __future__ import annotations

import sys
import time
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from erdos.commands.presenter import exit_with_result
from erdos.core.ask import ask_question


app = typer.Typer(
    help="Ask questions about Erdős problems using RAG.",
    context_settings={"allow_interspersed_args": True},
)
console = Console()
err_console = Console(stderr=True)


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
            text_preview = source.get("text", "")[:100]
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
    problem_id: Annotated[
        int,
        typer.Argument(
            help="Erdős problem ID to ask about.",
            min=1,
        ),
    ],
    question_arg: Annotated[
        str,
        typer.Argument(
            help="Question to ask. Use '-' to read from stdin.",
        ),
    ],
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-n",
            help="Maximum number of chunks to retrieve.",
        ),
    ] = 5,
    build_index: Annotated[
        bool,
        typer.Option(
            "--build-index",
            help="Build/rebuild the search index before retrieval.",
        ),
    ] = False,
    no_llm: Annotated[
        bool,
        typer.Option(
            "--no-llm",
            help="Skip LLM execution (prompt-only mode).",
        ),
    ] = False,
    llm_cmd: Annotated[
        str,
        typer.Option(
            "--llm-cmd",
            help="Override LLM command (default: ERDOS_LLM_COMMAND env).",
        ),
    ] = "",
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output as JSON for machine consumption.",
        ),
    ] = False,
) -> None:
    """
    Ask a question about an Erdős problem using RAG.

    Retrieves relevant text chunks from the search index,
    builds a citation-grounded prompt, and optionally runs
    an external LLM to generate an answer.

    Examples:

        erdos ask 6 "What partial results are known?" --no-llm

        ERDOS_LLM_COMMAND="./scripts/llm.sh" erdos ask 6 "Summarize known results"

        echo "What is the status?" | erdos ask 6 - --json
    """
    ctx.ensure_object(dict)
    if json_output:
        ctx.obj["json"] = True

    # Handle stdin question
    if question_arg == "-":
        question = sys.stdin.read()
        # Trim single trailing newline
        if question.endswith("\n"):
            question = question[:-1]
        # Validate non-empty
        if not question.strip():
            err_console.print("[red]Error:[/red] Question cannot be empty")
            raise typer.Exit(code=64)  # USAGE_ERROR
    else:
        question = question_arg

    # Show progress (only in human mode)
    if not json_output:
        err_console.print(f"[dim]Retrieving sources for Problem {problem_id}...[/dim]")

    start_time = time.perf_counter()

    # Call core ask logic
    result = ask_question(
        problem_id=problem_id,
        question=question,
        limit=limit,
        build_index_flag=build_index,
        no_llm=no_llm,
        llm_command=llm_cmd if llm_cmd else None,
    )

    # Add duration
    duration_ms = int((time.perf_counter() - start_time) * 1000)
    result.duration_ms = duration_ms

    # Exit with result
    exit_with_result(ctx, result, print_human=_print_human)
