"""Ask package: RAG Q&A for Erdős problems.

This package provides:
- prompt: Prompt construction
- retrieval: Source retrieval logic
- llm: LLM execution
- service: Orchestration (ask_question)

All public APIs are re-exported for backward compatibility.
"""

# Re-export public APIs for backward compatibility
from erdos.core.ask.llm import execute_llm, execute_llm_if_enabled
from erdos.core.ask.prompt import build_prompt
from erdos.core.ask.retrieval import (
    fallback_sources,
    perform_retrieval,
    retrieve_sources,
)
from erdos.core.ask.service import (
    _build_response_data,
    _ensure_index_ready,
    _load_problem,
    ask_question,
)


# Private name aliases for backward compatibility with test imports
_fallback_sources = fallback_sources
_retrieve_sources = retrieve_sources
_execute_llm_if_enabled = execute_llm_if_enabled

__all__ = [
    "_build_response_data",
    # Internal (for tests)
    "_ensure_index_ready",
    "_execute_llm_if_enabled",  # Backward compat alias
    "_fallback_sources",  # Backward compat alias
    "_load_problem",
    "_retrieve_sources",  # Backward compat alias
    # Service
    "ask_question",
    # Prompt
    "build_prompt",
    # LLM
    "execute_llm",
    "execute_llm_if_enabled",
    "fallback_sources",
    # Retrieval
    "perform_retrieval",
    "retrieve_sources",
]
