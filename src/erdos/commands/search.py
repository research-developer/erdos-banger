"""erdos search - search problem statements."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.console import Console

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.constants import PREVIEW_LENGTH
from erdos.core.exit_codes import ExitCode
from erdos.core.index_builder import build_index as do_build_index
from erdos.core.models import CLIOutput, ProblemRecord
from erdos.core.problem_loader import ProblemLoaderError
from erdos.core.search_index import SearchIndexError
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository, SearchIndexProtocol
    from erdos.core.problem_loader import ProblemLoader


@dataclass
class SearchOptions:
    """Options for the search command."""

    query: str
    limit: int
    problem_id: int | None
    build_index: bool


app = typer.Typer(
    help="Search problem statements.",
    context_settings={"allow_interspersed_args": True},
)
console = Console()
err_console = Console(stderr=True)


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
        title = r.get("title") or ""
        snippet = r.get("snippet") or ""
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
    index: SearchIndexProtocol,
    repo: ProblemRepository | None = None,
    limit: int = 10,
    problem_id: int | None = None,
) -> CLIOutput:
    """Search using FTS5 index (preferred)."""
    try:
        # Guard against empty query (consistent with basic search)
        if not query.strip():
            return CLIOutput.err(
                command="erdos search",
                error_type="UsageError",
                message="Query must not be empty",
                code=ExitCode.USAGE_ERROR,
            )

        # Check if index has data
        if index.problem_count() == 0:
            return CLIOutput.err(
                command="erdos search",
                error_type="IndexEmpty",
                message="Search index is empty. Run with --build-index to populate it.",
                code=0,  # Not really an error, just needs index built
            )

        results = index.search(query, limit=limit, problem_id=problem_id)

        enriched_results = []
        for r in results:
            problem = None
            if repo is not None and r.problem_id is not None:
                try:
                    problem = repo.get_by_id(r.problem_id)
                except Exception:
                    logger.debug(
                        "Failed to enrich result for problem %s",
                        r.problem_id,
                        exc_info=True,
                    )
                    problem = None
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
            code=ExitCode.ERROR,
        )
    except Exception as e:
        logger.exception("Unexpected error in FTS search")
        return CLIOutput.err(
            command="erdos search",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


def search_problems_basic(
    query: str,
    repo: ProblemRepository,
    limit: int = 10,
    problem_id: int | None = None,
) -> CLIOutput:
    """Fallback: basic substring search (no ranking)."""
    try:
        q = query.lower().strip()
        if not q:
            return CLIOutput.err(
                command="erdos search",
                error_type="UsageError",
                message="Query must not be empty",
                code=ExitCode.USAGE_ERROR,
            )

        # If problem_id specified, search only that problem
        if problem_id is not None:
            problem = repo.get_by_id(problem_id)
            if problem is None:
                return CLIOutput.err(
                    command="erdos search",
                    error_type="NotFound",
                    message=f"Problem {problem_id} not found",
                    code=ExitCode.NOT_FOUND,
                )
            candidates = [problem]
        else:
            candidates = repo.load_all()

        matches: list[ProblemRecord] = []
        for problem in candidates:
            if q in problem.title.lower() or q in problem.statement.lower():
                matches.append(problem)

        matches = sorted(matches, key=lambda p: p.id)[:limit]

        results = [
            {
                "problem_id": p.id,
                "title": p.title,
                "snippet": p.statement[:PREVIEW_LENGTH] + "..."
                if len(p.statement) > PREVIEW_LENGTH
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
        logger.exception("Unexpected error in search command")
        return CLIOutput.err(
            command="erdos search",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


# Keep for backward compatibility
def search_problems(query: str, loader: ProblemLoader) -> CLIOutput:
    """Legacy search function (for backward compatibility)."""
    return search_problems_basic(query, loader)


def _build_index_if_requested(
    build_index: bool,
    progress_console: Console,
    *,
    repo: ProblemRepository,
    index: SearchIndexProtocol,
) -> CLIOutput | None:
    """Build index if requested, returning error or None on success."""
    if not build_index:
        return None
    progress_console.print("Building search index...")
    try:
        stats = do_build_index(loader=repo, index=index, rebuild=True)
        progress_console.print(
            f"[green]✓[/green] Indexed {stats['problems_indexed']} problems"
        )
        return None
    except (ProblemLoaderError, SearchIndexError) as e:
        error_type = (
            "LoaderError" if isinstance(e, ProblemLoaderError) else "IndexError"
        )
        return CLIOutput.err(
            command="erdos search",
            error_type=error_type,
            message=str(e),
            code=ExitCode.ERROR,
        )


def _search_with_fallback(
    options: SearchOptions,
    *,
    index: SearchIndexProtocol | None,
    repo: ProblemRepository,
) -> CLIOutput:
    """Execute FTS search with fallback to basic substring search."""
    if index is None:
        return search_problems_basic(
            options.query, repo, options.limit, options.problem_id
        )

    result = search_problems_fts(
        options.query,
        index=index,
        repo=repo,
        limit=options.limit,
        problem_id=options.problem_id,
    )

    # If index is empty, fall back to basic search
    if not result.success and result.error and result.error.get("type") == "IndexEmpty":
        result = search_problems_basic(
            options.query, repo, options.limit, options.problem_id
        )

    return result


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
    json_mode = bool((ctx.obj or {}).get("json"))
    progress_console = err_console if json_mode else console

    # Store result to assign duration after context manager exits
    result: CLIOutput | None = None

    with measure_time_ms() as duration:
        app_ctx, app_error = get_app_context(ctx, command="erdos search")
        if app_error is not None or app_ctx is None:
            result = app_error
        else:
            # Best-effort index: if it can't be opened, fall back to basic search.
            index: SearchIndexProtocol | None
            try:
                index = app_ctx.ensure_index()
            except SearchIndexError:
                index = None

            if build_index:
                if index is None:
                    result = CLIOutput.err(
                        command="erdos search",
                        error_type="IndexError",
                        message="Search index is unavailable in this environment",
                        code=ExitCode.ERROR,
                    )
                elif build_error := _build_index_if_requested(
                    build_index,
                    progress_console,
                    repo=app_ctx.problems,
                    index=index,
                ):
                    result = build_error

            # If no error yet, perform the search
            if result is None:
                options = SearchOptions(
                    query=query,
                    limit=limit,
                    problem_id=problem_filter,
                    build_index=build_index,
                )
                result = _search_with_fallback(
                    options, index=index, repo=app_ctx.problems
                )

    # Duration is now set correctly after context manager exits.
    # Result is guaranteed to be set by one of the branches above.
    if result is not None:
        result.duration_ms = duration[0]
        exit_with_result(ctx, result, print_human=_print_human)
