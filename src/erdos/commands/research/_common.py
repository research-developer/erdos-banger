"""Shared helpers for `erdos research` commands."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.problem_loader import ProblemLoaderError
from erdos.core.research.errors import (
    ResearchRecordInvalidError,
    ResearchRecordNotFoundError,
)


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository


def read_text_arg(text_arg: str) -> str:
    """Read a CLI argument that may be '-' to indicate stdin."""
    if text_arg != "-":
        return text_arg
    text = sys.stdin.read()
    if text.endswith("\n"):
        text = text[:-1]
    return text


def load_problem_or_error(
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
            error_type="NotFoundError",
            message=f"Problem {problem_id} not found",
            code=ExitCode.NOT_FOUND,
        )
    return None


def handle_store_error(command: str, exc: Exception) -> CLIOutput:
    if isinstance(exc, ResearchRecordNotFoundError):
        return CLIOutput.err(
            command=command,
            error_type="NotFoundError",
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
