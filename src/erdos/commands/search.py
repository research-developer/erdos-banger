"""erdos search - search problem statements."""

from __future__ import annotations

import time
from typing import Annotated, Any, cast

import typer
from rich.console import Console

from erdos.core.index_builder import build_index as do_build_index
from erdos.core.models import CLIOutput, ProblemRecord
from erdos.core.problem_loader import ProblemLoader, ProblemLoaderError
from erdos.core.search_index import SearchIndex, SearchIndexError


app = typer.Typer(
    help="Search problem statements.",
    context_settings={"allow_interspersed_args": True},
)
console = Console()
err_console = Console(stderr=True)


def _output(ctx: typer.Context, data: CLIOutput) -> None:
    if (ctx.obj or {}).get("json"):
        console.print_json(data.model_dump_json())
    elif data.success:
        _print_human(cast("dict[str, Any]", data.data))
    else:
        error = cast("dict[str, Any]", data.error)
        err_console.print(f"[red]Error:[/red] {error['message']}")


def _print_human(result_data: dict[str, Any]) -> None:
    """Pretty-print search results."""
    results = result_data.get("results", [])
    query = result_data.get("query", "")
    use_fts = result_data.get("use_fts", False)

    if not results:
        console.print(f"No results for: {query}")
        return

    console.print(f"[bold]Search results for:[/bold] {query}")
    if use_fts:
        console.print("[dim]Using FTS5 index with BM25 ranking[/dim]\n")
    else:
        console.print(
            "[dim]Using basic substring search (run 'erdos search --build-index' for better results)[/dim]\n"
        )

    for i, r in enumerate(results, 1):
        problem_id = r.get("problem_id")
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        score = r.get("score")
        source_type = r.get("source_type", "")

        if problem_id:
            console.print(f"[cyan]{i}.[/cyan] Problem {problem_id}: {title}")
        else:
            console.print(f"[cyan]{i}.[/cyan] Reference")

        if snippet:
            console.print(f"   {snippet}")
        if score is not None:
            console.print(f"   [dim]Score: {score:.2f} | Source: {source_type}[/dim]")
        console.print()


def search_problems_fts(
    query: str,
    *,
    limit: int = 10,
    problem_id: int | None = None,
) -> CLIOutput:
    """Search using FTS5 index (preferred)."""
    try:
        index = SearchIndex.from_default()

        # Check if index has data
        if index.problem_count() == 0:
            return CLIOutput.err(
                command="erdos search",
                error_type="IndexEmpty",
                message="Search index is empty. Run with --build-index to populate it.",
                code=0,  # Not really an error, just needs index built
            )

        results = index.search(query, limit=limit, problem_id=problem_id)

        # Enrich results with problem titles
        loader = ProblemLoader.from_default()
        enriched_results = []
        for r in results:
            problem = loader.get_by_id(r.problem_id) if r.problem_id else None
            enriched_results.append(
                {
                    "chunk_id": r.chunk_id,
                    "snippet": r.snippet,
                    "score": r.score,
                    "source_type": r.source_type.value,
                    "problem_id": r.problem_id,
                    "title": problem.title if problem else None,
                    "reference_doi": r.reference_doi,
                }
            )

        return CLIOutput.ok(
            command="erdos search",
            data={
                "query": query,
                "count": len(enriched_results),
                "results": enriched_results,
                "use_fts": True,
            },
        )

    except SearchIndexError as e:
        return CLIOutput.err(
            command="erdos search",
            error_type="IndexError",
            message=str(e),
            code=1,
        )


def search_problems_basic(
    query: str, loader: ProblemLoader, limit: int = 10
) -> CLIOutput:
    """Fallback: basic substring search (no ranking)."""
    try:
        q = query.lower().strip()
        if not q:
            return CLIOutput.err(
                command="erdos search",
                error_type="UsageError",
                message="Query must not be empty",
                code=2,
            )

        matches: list[ProblemRecord] = []
        for problem in loader.load_all():
            if q in problem.title.lower() or q in problem.statement.lower():
                matches.append(problem)

        matches = sorted(matches, key=lambda p: p.id)[:limit]

        results = [
            {
                "problem_id": p.id,
                "title": p.title,
                "snippet": p.statement[:200] + "..."
                if len(p.statement) > 200
                else p.statement,
                "score": None,
                "source_type": "problem_statement",
            }
            for p in matches
        ]

        return CLIOutput.ok(
            command="erdos search",
            data={
                "query": query,
                "count": len(results),
                "results": results,
                "use_fts": False,
            },
        )
    except Exception as e:
        return CLIOutput.err(
            command="erdos search",
            error_type="Error",
            message=str(e),
            code=1,
        )


# Keep for backward compatibility
def search_problems(query: str, loader: ProblemLoader) -> CLIOutput:
    """Legacy search function (for backward compatibility)."""
    return search_problems_basic(query, loader)


@app.callback(invoke_without_command=True)
def search(
    ctx: typer.Context,
    query: Annotated[
        str,
        typer.Argument(help="Search query (supports FTS5 syntax when index exists)"),
    ],
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum results to return"),
    ] = 10,
    problem_filter: Annotated[
        int | None,
        typer.Option("--problem", "-p", help="Filter to specific problem ID"),
    ] = None,
    build_index: Annotated[
        bool,
        typer.Option(
            "--build-index", help="Build/rebuild the search index before searching"
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON for machine consumption."),
    ] = False,
) -> None:
    """
    Search problem statements for a query.

    Supports FTS5 syntax when index exists:
      - "exact phrase" for phrase match
      - word* for prefix match
      - word1 OR word2 for alternatives
      - NOT word to exclude

    Example: erdos search "prime"
    Example: erdos search "arithmetic progression" --limit 5
    """
    ctx.ensure_object(dict)
    if json_output:
        ctx.obj["json"] = True

    # Build index if requested
    if build_index:
        console.print("Building search index...")
        try:
            stats = do_build_index(rebuild=True)
            console.print(
                f"[green]✓[/green] Indexed {stats['problems_indexed']} problems"
            )
        except ProblemLoaderError as e:
            result = CLIOutput.err(
                command="erdos search",
                error_type="LoaderError",
                message=str(e),
                code=1,
            )
            _output(ctx, result)
            raise typer.Exit(code=1) from None

    start_time = time.perf_counter()

    # Try FTS search first, fall back to basic
    result = search_problems_fts(query, limit=limit, problem_id=problem_filter)

    # If index is empty, fall back to basic search
    if not result.success and result.error and result.error.get("type") == "IndexEmpty":
        try:
            loader = ProblemLoader.from_default()
            result = search_problems_basic(query, loader, limit)
        except ProblemLoaderError as e:
            result = CLIOutput.err(
                command="erdos search",
                error_type="LoaderError",
                message=str(e),
                code=1,
            )

    duration_ms = int((time.perf_counter() - start_time) * 1000)

    # Add duration to result
    result.duration_ms = duration_ms
    _output(ctx, result)

    if not result.success:
        error = cast("dict[str, Any]", result.error)
        raise typer.Exit(code=int(error.get("code", 1)))
