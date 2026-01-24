"""LLM routing and execution for task-appropriate model selection.

This module provides task-level routing for LLM calls while preserving the
vendor-neutral external command integration pattern. Models are selected
by choosing the appropriate command/script per task type.

Example:
    >>> from erdos.core.llm import TaskType, resolve_llm_command
    >>> cmd = resolve_llm_command(TaskType.ask_question)
    >>> # cmd is resolved from ERDOS_LLM_COMMAND_MATH -> ERDOS_LLM_COMMAND
"""

from erdos.core.llm.router import (
    LLMRouterError,
    resolve_llm_command,
)
from erdos.core.llm.tasks import (
    TaskType,
    get_env_var_chain,
)


__all__ = [
    "LLMRouterError",
    "TaskType",
    "get_env_var_chain",
    "resolve_llm_command",
]
