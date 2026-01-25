"""LLM execution for RAG Q&A."""

import logging
import shlex
import subprocess
import time
from dataclasses import dataclass

from erdos.core.constants import LLM_COMMAND_TIMEOUT
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput


logger = logging.getLogger(__name__)


def execute_llm(
    llm_command: str, prompt: str, *, timeout: int | None = LLM_COMMAND_TIMEOUT
) -> tuple[str, int]:
    """
    Execute an external LLM command with the prompt.

    Args:
        llm_command: Shell command to execute (will be parsed with shlex.split)
        prompt: The prompt to pass via stdin
        timeout: Maximum seconds to wait (default: LLM_COMMAND_TIMEOUT, None for no timeout)

    Returns:
        Tuple of (answer, exit_code)

    Raises:
        OSError: If the command executable doesn't exist or can't be invoked
        subprocess.TimeoutExpired: If the command times out
    """
    # Parse command with shlex.split for shell-free execution
    cmd_args = shlex.split(llm_command)

    logger.debug("Executing LLM command: %s", llm_command)
    logger.debug("LLM prompt length: %d chars", len(prompt))
    start_time = time.monotonic()

    # Execute with shell=False for security
    result = subprocess.run(  # noqa: S603
        cmd_args,
        input=prompt,
        capture_output=True,
        text=True,
        check=False,  # We handle exit codes manually
        timeout=timeout,
    )

    elapsed = time.monotonic() - start_time
    logger.debug(
        "LLM response: %d chars in %.2fs (exit code %d)",
        len(result.stdout),
        elapsed,
        result.returncode,
    )

    return result.stdout, result.returncode


@dataclass(frozen=True)
class LLMExecutionResult:
    """Result for optional LLM execution (success, skip, or error)."""

    answer: str | None = None
    llm_exit_code: int | None = None
    llm_enabled: bool = False
    llm_command: str | None = None
    error: CLIOutput | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def _handle_llm_exception(
    *, exc: Exception, command: str, llm_command: str
) -> CLIOutput:
    """Map execution exceptions to user-facing CLIOutput errors."""
    if isinstance(exc, FileNotFoundError):
        return CLIOutput.err(
            command=command,
            error_type="ConfigError",
            message=f"LLM command not found: {llm_command}",
            code=ExitCode.CONFIG_ERROR,
        )
    if isinstance(exc, subprocess.TimeoutExpired):
        return CLIOutput.err(
            command=command,
            error_type="TimeoutError",
            message=f"LLM command timed out after {LLM_COMMAND_TIMEOUT}s: {llm_command}",
            code=ExitCode.ERROR,
        )
    if isinstance(exc, ValueError):
        # shlex.split can raise ValueError for malformed command strings
        return CLIOutput.err(
            command=command,
            error_type="ConfigError",
            message=f"Invalid LLM command syntax: {exc}",
            code=ExitCode.CONFIG_ERROR,
        )
    if isinstance(exc, OSError):
        return CLIOutput.err(
            command=command,
            error_type="ConfigError",
            message=f"LLM command error: {exc}",
            code=ExitCode.CONFIG_ERROR,
        )
    return CLIOutput.err(
        command=command,
        error_type="LLMError",
        message=f"LLM command failed: {exc}",
        code=ExitCode.ERROR,
    )


def execute_llm_if_enabled(
    *,
    prompt: str,
    enable_llm: bool,
    llm_command: str | None,
    command: str,
) -> LLMExecutionResult:
    """
    Execute LLM if enabled and command is available.

    Args:
        prompt: The prompt to pass to LLM
        enable_llm: Whether LLM should be executed
        llm_command: LLM command to execute

    Returns:
        LLMExecutionResult with llm metadata and optional error
    """
    # Skip if LLM disabled or no command available
    if not enable_llm or not llm_command:
        return LLMExecutionResult()

    # Execute LLM
    try:
        answer, exit_code = execute_llm(llm_command=llm_command, prompt=prompt)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError, ValueError) as e:
        return LLMExecutionResult(
            llm_enabled=True,
            llm_command=llm_command,
            error=_handle_llm_exception(
                exc=e, command=command, llm_command=llm_command
            ),
        )

    # Check exit code
    if exit_code != 0:
        return LLMExecutionResult(
            llm_enabled=True,
            llm_command=llm_command,
            llm_exit_code=exit_code,
            error=CLIOutput.err(
                command=command,
                error_type="LLMError",
                message=f"LLM command exited with code {exit_code}",
                code=ExitCode.ERROR,
            ),
        )

    return LLMExecutionResult(
        answer=answer,
        llm_exit_code=exit_code,
        llm_enabled=True,
        llm_command=llm_command,
    )
