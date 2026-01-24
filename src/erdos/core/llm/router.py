"""LLM command router for task-appropriate model selection.

This module resolves task types to command strings by checking environment
variables in a defined precedence order. It supports explicit overrides
(e.g., --llm-cmd) that bypass routing entirely.
"""

from __future__ import annotations

import os

from erdos.core.llm.tasks import TaskType, get_env_var_chain


class LLMRouterError(Exception):
    """Raised when no LLM command can be resolved for a task."""

    pass


def resolve_llm_command(
    task: TaskType,
    *,
    override: str | None = None,
    env: dict[str, str] | None = None,
) -> str:
    """Resolve the LLM command for a given task type.

    Resolution order:
    1. If override is provided and non-empty, use it directly.
    2. Otherwise, check environment variables in the task's chain order.
    3. If no command is found, raise LLMRouterError.

    Args:
        task: The task type to resolve a command for.
        override: Explicit command override (e.g., from --llm-cmd). Bypasses
            all environment variable lookups if provided and non-empty.
        env: Optional environment dict to use instead of os.environ.
            Useful for testing or isolated execution contexts.

    Returns:
        The resolved LLM command string.

    Raises:
        LLMRouterError: If no command is configured for the task.
    """
    # Override bypasses routing entirely
    if override and override.strip():
        return override.strip()

    # Use provided env dict or fall back to os.environ
    environ = env if env is not None else dict(os.environ)

    # Check environment variables in chain order
    chain = get_env_var_chain(task)
    for var_name in chain:
        value = environ.get(var_name, "").strip()
        if value:
            return value

    # No command found - raise clear error
    checked_vars = ", ".join(chain)
    raise LLMRouterError(
        f"No LLM command configured for task '{task.value}'. Set one of: {checked_vars}"
    )
