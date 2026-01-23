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
from erdos.core.ask.service import ask_question


__all__ = [
    # Service
    "ask_question",
    # Prompt
    "build_prompt",
    # LLM
    "execute_llm",
    "execute_llm_if_enabled",
    # Retrieval
    "fallback_sources",
    "perform_retrieval",
    "retrieve_sources",
]
