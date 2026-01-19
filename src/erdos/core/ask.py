"""Ask command: retrieval-augmented Q&A for Erdős problems."""

import os
import shlex
import subprocess

from erdos.core.exit_codes import ExitCode
from erdos.core.index_builder import build_index
from erdos.core.models import CLIOutput, ProblemRecord
from erdos.core.problem_loader import ProblemLoader
from erdos.core.search_index import SearchIndex, SearchResult


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
    index: SearchIndex,
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
    # Construct query that includes problem context
    # Escape quotes in the question to avoid FTS5 syntax errors
    escaped_question = question.replace('"', '""')
    query = f'"{escaped_question}"'

    # Search with problem_id filter to bias towards this problem
    results = index.search(
        query,
        limit=limit,
        problem_id=problem.id,
    )

    return results


def execute_llm(llm_command: str, prompt: str) -> tuple[str, int]:
    """
    Execute an external LLM command with the prompt.

    Args:
        llm_command: Shell command to execute (will be parsed with shlex.split)
        prompt: The prompt to pass via stdin

    Returns:
        Tuple of (answer, exit_code)

    Raises:
        FileNotFoundError: If the command executable doesn't exist
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


def ask_question(  # noqa: PLR0911
    problem_id: int,
    question: str,
    *,
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
    try:
        loader = ProblemLoader.from_default()
        problem = loader.get_by_id(problem_id)
    except ValueError:
        return CLIOutput.err(
            command="erdos ask",
            error_type="NOT_FOUND",
            message=f"Problem {problem_id} not found",
            code=4,
        )
    except Exception as e:
        return CLIOutput.err(
            command="erdos ask",
            error_type="ERROR",
            message=f"Failed to load problem: {e}",
            code=1,
        )

    # Type narrowing: problem is ProblemRecord after successful load
    assert problem is not None  # noqa: S101

    # Build/rebuild index if requested
    if build_index_flag:
        try:
            build_index(loader=loader, rebuild=True)
        except Exception as e:
            return CLIOutput.err(
                command="erdos ask",
                error_type="ERROR",
                message=f"Failed to build index: {e}",
                code=1,
            )

    # Get search index
    try:
        index = SearchIndex.from_default()
    except Exception as e:
        return CLIOutput.err(
            command="erdos ask",
            error_type="ERROR",
            message=f"Failed to open search index: {e}",
            code=1,
        )

    # Perform retrieval
    sources = perform_retrieval(
        index=index,
        problem=problem,
        question=question,
        limit=limit,
    )

    # Build query string for metadata
    query = f"Problem {problem.id}: {problem.title}. Question: {question}"

    # Build prompt
    prompt = build_prompt(problem=problem, sources=sources, question=question)

    # Determine if LLM should run
    run_llm = not no_llm
    if run_llm and llm_command is None:
        llm_command = os.environ.get("ERDOS_LLM_COMMAND", "")

    # Execute LLM if requested and command is available
    answer = None
    llm_exit_code = None
    llm_enabled = False

    if run_llm and llm_command:
        llm_enabled = True
        try:
            answer, llm_exit_code = execute_llm(llm_command=llm_command, prompt=prompt)
        except FileNotFoundError:
            return CLIOutput.err(
                command="erdos ask",
                error_type="CONFIG_ERROR",
                message=f"LLM command not found: {llm_command}",
                code=ExitCode.CONFIG_ERROR,
            )
        except Exception as e:
            return CLIOutput.err(
                command="erdos ask",
                error_type="ERROR",
                message=f"LLM execution failed: {e}",
                code=1,
            )

        # Check exit code
        if llm_exit_code != 0:
            return CLIOutput.err(
                command="erdos ask",
                error_type="ERROR",
                message=f"LLM command exited with code {llm_exit_code}",
                code=1,
            )

    # Build response data
    data = {
        "problem_id": problem_id,
        "question": question,
        "prompt": prompt,
        "answer": answer,
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
            "used_fts": True,
        },
        "llm": {
            "enabled": llm_enabled,
            "command": llm_command if llm_enabled else None,
            "exit_code": llm_exit_code,
        },
    }

    return CLIOutput.ok(command="erdos ask", data=data)
