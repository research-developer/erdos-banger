"""Ask package: RAG Q&A for Erdős problems.

This package provides:
- prompt: Prompt construction
- retrieval: Source retrieval logic
- llm: LLM execution
- service: Orchestration (ask_question)

Public APIs are re-exported at the package level to provide a stable import surface.
"""

# Public API re-exports
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
