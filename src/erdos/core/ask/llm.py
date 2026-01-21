"""LLM execution for RAG Q&A."""

import logging
import shlex
import subprocess
import time

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


def execute_llm_if_enabled(  # noqa: PLR0911
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
    except subprocess.TimeoutExpired:
        return CLIOutput.err(
            command="erdos ask",
            error_type="TIMEOUT",
            message=f"LLM command timed out after {LLM_COMMAND_TIMEOUT}s: {llm_command}",
            code=ExitCode.ERROR,
        )
    except OSError as e:
        return CLIOutput.err(
            command="erdos ask",
            error_type="CONFIG_ERROR",
            message=f"LLM command error: {e}",
            code=ExitCode.CONFIG_ERROR,
        )
    except ValueError as e:
        # shlex.split can raise ValueError for malformed command strings
        return CLIOutput.err(
            command="erdos ask",
            error_type="CONFIG_ERROR",
            message=f"Invalid LLM command syntax: {e}",
            code=ExitCode.CONFIG_ERROR,
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
