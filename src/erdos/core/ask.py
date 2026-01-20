"""Ask command: retrieval-augmented Q&A for Erdős problems."""

import os
import re
import shlex
import subprocess
from typing import Any

from erdos.core.constants import PREVIEW_LENGTH
from erdos.core.exit_codes import ExitCode
from erdos.core.index_builder import build_index
from erdos.core.models import ChunkSource, CLIOutput, ProblemRecord
from erdos.core.ports import ProblemRepository, SearchIndexProtocol
from erdos.core.problem_loader import ProblemLoaderError
from erdos.core.search_index import SearchResult


def build_prompt(
    problem: ProblemRecord,
    sources: list[SearchResult],
    question: str,
) -> str:
    """
    Build a deterministic RAG prompt.

    Args:
        problem: The problem record
        sources: Retrieved text chunks (ordered by relevance)
        question: User's question

    Returns:
        Formatted prompt string
    """
    # Build prompt sections
    sections = []

    # Header
    sections.append("You are assisting with research on a specific Erdős problem.")
    sections.append("")

    # Problem metadata
    sections.append("Problem:")
    sections.append(f"- id: {problem.id}")
    sections.append(f"- title: {problem.title}")
    sections.append("")

    # Statement
    sections.append("Statement:")
    sections.append(problem.statement)
    sections.append("")

    # Notes section
    sections.append("Notes:")
    if problem.notes:
        sections.append(problem.notes)
    else:
        sections.append("(none)")
    sections.append("")

    # Sources
    sections.append("Sources (cite as [n]):")
    if sources:
        for idx, source in enumerate(sources, start=1):
            sections.append(f"[{idx}] ({source.source_type.value}) {source.chunk_id}")
            sections.append(source.text)
            sections.append("")
    else:
        sections.append("(no sources retrieved)")
        sections.append("")

    # Question
    sections.append("Question:")
    sections.append(question)
    sections.append("")

    # Instructions
    sections.append("Instructions:")
    sections.append("- Answer using only the sources above.")
    sections.append(
        "- When making a claim, cite the supporting source like [1] or [2]."
    )
    sections.append(
        "- If the sources are insufficient, say so explicitly and suggest what to ingest/search next."
    )

    return "\n".join(sections)


def perform_retrieval(
    index: SearchIndexProtocol,
    problem: ProblemRecord,
    question: str,
    limit: int,
) -> list[SearchResult]:
    """
    Retrieve relevant text chunks for a question about a problem.

    Args:
        index: The search index
        problem: The problem record
        question: User's question
        limit: Maximum number of chunks to retrieve

    Returns:
        List of search results, ordered by relevance
    """
    # Build a safe FTS5 query. Using an exact phrase match for the full question is
    # too strict (it often returns zero results). Instead, extract tokens from the
    # problem title + question and OR them together.
    haystack = f"{problem.title} {question}".lower()
    tokens = re.findall(r"[a-z0-9]+", haystack)

    # De-duplicate tokens while preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        unique.append(token)

    # Quote terms to avoid operators like OR/AND/NOT being interpreted.
    terms = [f'"{t}"' for t in unique if t]
    query = " OR ".join(terms[:25])

    # Search with problem_id filter to bias towards this problem
    results = index.search(
        query,
        limit=limit,
        problem_id=problem.id,
    )

    return results


def _fallback_sources(problem: ProblemRecord, *, limit: int) -> list[SearchResult]:
    """Fallback retrieval when the FTS index has no data yet."""
    sources: list[SearchResult] = []

    # Always include the statement first (matches TextChunk.from_problem conventions).
    statement = problem.statement
    sources.append(
        SearchResult(
            chunk_id=f"problem_{problem.id}_statement",
            text=statement,
            snippet=statement[:PREVIEW_LENGTH] + "..."
            if len(statement) > PREVIEW_LENGTH
            else statement,
            score=1.0,
            source_type=ChunkSource.PROBLEM_STATEMENT,
            problem_id=problem.id,
            reference_doi=None,
        )
    )

    # Include notes if present and within limit.
    if problem.notes and len(sources) < limit:
        notes = problem.notes
        sources.append(
            SearchResult(
                chunk_id=f"problem_{problem.id}_notes",
                text=notes,
                snippet=notes[:PREVIEW_LENGTH] + "..."
                if len(notes) > PREVIEW_LENGTH
                else notes,
                score=0.5,
                source_type=ChunkSource.PROBLEM_NOTES,
                problem_id=problem.id,
                reference_doi=None,
            )
        )

    return sources[: max(limit, 0)]


def execute_llm(llm_command: str, prompt: str) -> tuple[str, int]:
    """
    Execute an external LLM command with the prompt.

    Args:
        llm_command: Shell command to execute (will be parsed with shlex.split)
        prompt: The prompt to pass via stdin

    Returns:
        Tuple of (answer, exit_code)

    Raises:
        OSError: If the command executable doesn't exist or can't be invoked
    """
    # Parse command with shlex.split for shell-free execution
    cmd_args = shlex.split(llm_command)

    # Execute with shell=False for security
    result = subprocess.run(  # noqa: S603
        cmd_args,
        input=prompt,
        capture_output=True,
        text=True,
        check=False,  # We handle exit codes manually
    )

    return result.stdout, result.returncode


def _ensure_index_ready(
    *,
    loader: ProblemRepository,
    index: SearchIndexProtocol,
    build_index_flag: bool,
) -> SearchIndexProtocol | CLIOutput:
    """
    Ensure search index is ready (build if requested, then open).

    Args:
        loader: Problem loader for building index
        build_index_flag: Whether to rebuild the index

    Returns:
        SearchIndexProtocol if successful, or CLIOutput error
    """
    # Build/rebuild index if requested
    if build_index_flag:
        try:
            build_index(loader=loader, index=index, rebuild=True)
        except Exception as e:
            return CLIOutput.err(
                command="erdos ask",
                error_type="ERROR",
                message=f"Failed to build index: {e}",
                code=ExitCode.ERROR,
            )
    return index


def _retrieve_sources(
    *,
    index: SearchIndexProtocol,
    problem: ProblemRecord,
    question: str,
    limit: int,
) -> tuple[list[SearchResult], bool]:
    """
    Retrieve sources for a question, with fallback.

    Args:
        index: Search index
        problem: Problem record
        question: User's question
        limit: Maximum sources to retrieve

    Returns:
        Tuple of (sources, used_fts) where used_fts indicates if FTS was used
    """
    # If index is empty, use fallback sources
    if index.chunk_count() == 0:
        sources = _fallback_sources(problem, limit=limit)
        return sources, False

    # Otherwise, combine fallback (statement/notes) with retrieved chunks
    baseline = _fallback_sources(problem, limit=limit)
    retrieved = perform_retrieval(
        index=index,
        problem=problem,
        question=question,
        limit=limit,
    )

    # Deduplicate by chunk_id, preferring baseline order first
    combined: list[SearchResult] = []
    seen_ids: set[str] = set()
    for source in [*baseline, *retrieved]:
        if source.chunk_id in seen_ids:
            continue
        seen_ids.add(source.chunk_id)
        combined.append(source)
        if len(combined) >= limit:
            break

    return combined, True


def _load_problem(
    problem_id: int, *, repo: ProblemRepository
) -> ProblemRecord | CLIOutput:
    """
    Load problem, handling errors.

    Returns:
        ProblemRecord if successful, or CLIOutput error
    """
    try:
        problem = repo.get_by_id(problem_id)
    except ProblemLoaderError as e:
        return CLIOutput.err(
            command="erdos ask",
            error_type="LoaderError",
            message=str(e),
            code=ExitCode.ERROR,
        )
    except Exception as e:
        return CLIOutput.err(
            command="erdos ask",
            error_type="LoaderError",
            message=str(e),
            code=ExitCode.ERROR,
        )

    if problem is None:
        return CLIOutput.err(
            command="erdos ask",
            error_type="NotFound",
            message=f"Problem {problem_id} not found",
            code=ExitCode.NOT_FOUND,
        )

    return problem


def _execute_llm_if_enabled(
    *,
    prompt: str,
    enable_llm: bool,
    llm_command: str | None,
) -> dict[str, str | int | bool | None] | CLIOutput:
    """
    Execute LLM if enabled and command is available.

    Args:
        prompt: The prompt to pass to LLM
        enable_llm: Whether LLM should be executed
        llm_command: LLM command to execute

    Returns:
        Dict with llm metadata if successful, or CLIOutput error
    """
    # Build result dict
    result: dict[str, str | int | bool | None] = {
        "answer": None,
        "llm_exit_code": None,
        "llm_enabled": False,
        "llm_command": None,
    }

    # Skip if LLM disabled or no command available
    if not enable_llm or not llm_command:
        return result

    # Execute LLM
    result["llm_enabled"] = True
    result["llm_command"] = llm_command

    try:
        answer, exit_code = execute_llm(llm_command=llm_command, prompt=prompt)
    except FileNotFoundError:
        return CLIOutput.err(
            command="erdos ask",
            error_type="CONFIG_ERROR",
            message=f"LLM command not found: {llm_command}",
            code=ExitCode.CONFIG_ERROR,
        )
    except OSError as e:
        return CLIOutput.err(
            command="erdos ask",
            error_type="CONFIG_ERROR",
            message=f"LLM command error: {e}",
            code=ExitCode.CONFIG_ERROR,
        )
    except Exception as e:
        return CLIOutput.err(
            command="erdos ask",
            error_type="ERROR",
            message=f"LLM execution failed: {e}",
            code=ExitCode.ERROR,
        )

    # Check exit code
    if exit_code != 0:
        return CLIOutput.err(
            command="erdos ask",
            error_type="ERROR",
            message=f"LLM command exited with code {exit_code}",
            code=ExitCode.ERROR,
        )

    result["answer"] = answer
    result["llm_exit_code"] = exit_code
    return result


def _build_response_data(
    *,
    problem_id: int,
    question: str,
    prompt: str,
    sources: list[SearchResult],
    query: str,
    limit: int,
    used_fts: bool,
    llm_result: dict[str, str | int | bool | None],
) -> dict[str, Any]:
    """Build the response data dictionary."""
    return {
        "problem_id": problem_id,
        "question": question,
        "prompt": prompt,
        "answer": llm_result["answer"],
        "sources": [
            {
                "chunk_id": source.chunk_id,
                "rank": idx + 1,
                "source_type": source.source_type.value,
                "problem_id": source.problem_id,
                "reference_doi": source.reference_doi,
                "text": source.text,
            }
            for idx, source in enumerate(sources)
        ],
        "retrieval": {
            "query": query,
            "limit": limit,
            "count": len(sources),
            "used_fts": used_fts,
        },
        "llm": {
            "enabled": llm_result["llm_enabled"],
            "command": llm_result["llm_command"],
            "exit_code": llm_result["llm_exit_code"],
        },
    }


def ask_question(
    problem_id: int,
    question: str,
    *,
    repo: ProblemRepository,
    index: SearchIndexProtocol,
    limit: int = 5,
    build_index_flag: bool = False,
    no_llm: bool = False,
    llm_command: str | None = None,
) -> CLIOutput:
    """
    Ask a question about an Erdős problem using RAG.

    Args:
        problem_id: The problem ID
        question: The user's question
        limit: Maximum retrieved chunks
        build_index_flag: Whether to rebuild the index before retrieval
        no_llm: If True, skip LLM execution (prompt-only mode)
        llm_command: Override LLM command (default: from ERDOS_LLM_COMMAND env)

    Returns:
        CLIOutput with ask results
    """
    # Load problem
    problem_or_error = _load_problem(problem_id, repo=repo)
    if isinstance(problem_or_error, CLIOutput):
        return problem_or_error
    problem = problem_or_error

    # Ensure index is ready
    index_or_error = _ensure_index_ready(
        loader=repo,
        index=index,
        build_index_flag=build_index_flag,
    )
    if isinstance(index_or_error, CLIOutput):
        return index_or_error

    # Retrieve sources
    sources, used_fts = _retrieve_sources(
        index=index_or_error, problem=problem, question=question, limit=limit
    )

    # Build prompt
    prompt = build_prompt(problem=problem, sources=sources, question=question)

    # Determine LLM command
    enable_llm = not no_llm
    effective_llm_cmd = (
        llm_command if llm_command else os.environ.get("ERDOS_LLM_COMMAND", "")
    )

    # Execute LLM if enabled
    llm_result = _execute_llm_if_enabled(
        prompt=prompt, enable_llm=enable_llm, llm_command=effective_llm_cmd
    )
    if isinstance(llm_result, CLIOutput):
        return llm_result

    # Build response
    data = _build_response_data(
        problem_id=problem_id,
        question=question,
        prompt=prompt,
        sources=sources,
        query=f"Problem {problem.id}: {problem.title}. Question: {question}",
        limit=limit,
        used_fts=used_fts,
        llm_result=llm_result,
    )
    return CLIOutput.ok(command="erdos ask", data=data)
