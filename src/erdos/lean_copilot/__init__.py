"""Lean Copilot API server package.

This module provides an external API server implementing the Lean Copilot
protocol (SPEC-033). It enables LLM-backed tactic suggestions in Lean 4.

Requires the 'copilot' optional dependency:

    uv sync --extra copilot

The module gracefully handles missing dependencies, allowing imports without
requiring FastAPI/uvicorn to be installed.
"""

from __future__ import annotations

import logging


logger = logging.getLogger(__name__)


# =============================================================================
# Availability Check
# =============================================================================


def is_copilot_available() -> bool:
    """Check if copilot server dependencies (FastAPI/uvicorn) are available."""
    try:
        import fastapi  # noqa: F401, PLC0415
        import uvicorn  # noqa: F401, PLC0415

        return True
    except ImportError:
        logger.debug("Copilot unavailable: FastAPI/uvicorn not installed")
        return False


# =============================================================================
# Exceptions
# =============================================================================


class CopilotNotAvailableError(Exception):
    """Raised when copilot functionality is requested but deps not installed."""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            message
            or (
                "Copilot server requires the 'copilot' extra. "
                "Install with: uv sync --extra copilot"
            )
        )


__all__ = ["CopilotNotAvailableError", "is_copilot_available"]
