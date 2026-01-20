"""LLM execution for RAG Q&A."""

import shlex
import subprocess

from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput


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


def execute_llm_if_enabled(
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
