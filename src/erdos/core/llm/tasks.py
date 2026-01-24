"""LLM task types and environment variable mapping rules.

This module defines the task types for LLM calls and their corresponding
environment variable resolution chains. Each task type maps to a sequence
of environment variable names that are checked in order until a non-empty
value is found.

Per SPEC-032, the mapping is:
- ask_question: ERDOS_LLM_COMMAND_MATH -> ERDOS_LLM_COMMAND
- loop_patch: ERDOS_LLM_COMMAND_CODE -> ERDOS_LLM_COMMAND
- tactic_generation: ERDOS_LLM_COMMAND_COPILOT -> ERDOS_LLM_COMMAND_MATH -> ERDOS_LLM_COMMAND
"""

from enum import Enum


# Global fallback env var (always the last in any chain)
GLOBAL_LLM_ENV_VAR = "ERDOS_LLM_COMMAND"


class TaskType(str, Enum):
    """LLM task types for routing to appropriate backends.

    Each task type represents a distinct use case that may benefit from
    different model characteristics (reasoning vs code generation, etc.).
    """

    ask_question = "ask_question"
    """RAG Q&A: answering math questions about Erdős problems."""

    loop_patch = "loop_patch"
    """Proof loop: generating Lean 4 code patches."""

    tactic_generation = "tactic_generation"
    """Lean Copilot: generating tactic suggestions."""


# Environment variable resolution chains per task type.
# Order matters: first match wins.
_ENV_VAR_CHAINS: dict[TaskType, list[str]] = {
    TaskType.ask_question: [
        "ERDOS_LLM_COMMAND_MATH",
        GLOBAL_LLM_ENV_VAR,
    ],
    TaskType.loop_patch: [
        "ERDOS_LLM_COMMAND_CODE",
        GLOBAL_LLM_ENV_VAR,
    ],
    TaskType.tactic_generation: [
        "ERDOS_LLM_COMMAND_COPILOT",
        "ERDOS_LLM_COMMAND_MATH",
        GLOBAL_LLM_ENV_VAR,
    ],
}


def get_env_var_chain(task: TaskType) -> list[str]:
    """Return the environment variable resolution chain for a task type.

    The chain is ordered by precedence: first match wins. All chains
    end with ERDOS_LLM_COMMAND as the global fallback.

    Args:
        task: The task type to get the chain for.

    Returns:
        List of environment variable names in resolution order.
    """
    return list(_ENV_VAR_CHAINS[task])
