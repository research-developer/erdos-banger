"""FastAPI server implementing Lean Copilot external model API (SPEC-033).

This module provides:
- `/generate` endpoint for tactic suggestions (via SPEC-032 LLM routing)
- `/encode` endpoint for premise retrieval embeddings (via SPEC-014)

Requires the 'copilot' optional dependency:
    uv sync --extra copilot

For `/encode`, also requires the 'embeddings' optional dependency:
    uv sync --extra embeddings

If embeddings are not installed, `/encode` returns HTTP 503 (degraded mode).
"""

from __future__ import annotations

import asyncio
import logging
import shlex
import subprocess
from typing import TYPE_CHECKING, NoReturn

from pydantic import BaseModel, Field

from erdos.core.constants import LLM_COMMAND_TIMEOUT
from erdos.core.llm.router import LLMRouterError, resolve_llm_command
from erdos.core.llm.tasks import TaskType
from erdos.lean_copilot import CopilotNotAvailableError, is_copilot_available


if TYPE_CHECKING:
    from fastapi import FastAPI


logger = logging.getLogger(__name__)


# =============================================================================
# Request/Response Models
# =============================================================================


class GenerateRequest(BaseModel):
    """Request body for /generate endpoint."""

    prompt: str = Field(..., description="Proof state and context")
    num_samples: int = Field(default=5, ge=1, le=20, description="Number of tactics")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="Sampling temp")


class GenerateResponse(BaseModel):
    """Response body for /generate endpoint."""

    tactics: list[str] = Field(default_factory=list, description="Suggested tactics")


class ErrorResponse(BaseModel):
    """Error response body."""

    error: str
    detail: str | None = None


class EncodeRequest(BaseModel):
    """Request body for /encode endpoint."""

    texts: list[str] = Field(..., description="Texts to embed")


class EncodeResponse(BaseModel):
    """Response body for /encode endpoint."""

    embeddings: list[list[float]] = Field(
        default_factory=list, description="Embedding vectors"
    )


# =============================================================================
# Tactic Parsing
# =============================================================================


def parse_tactics(response: str) -> list[str]:
    """Parse tactic suggestions from LLM response.

    Cleans up common formatting artifacts:
    - Bullet points (-, •, ·)
    - Trailing punctuation
    - Comments (-- or #)
    - Empty lines

    Args:
        response: Raw LLM response text.

    Returns:
        List of cleaned tactic strings, deduplicated and preserving order.
    """
    tactics: list[str] = []
    seen: set[str] = set()

    for raw_line in response.strip().split("\n"):
        # Strip whitespace
        cleaned = raw_line.strip()

        # Skip empty lines and comments (before stripping bullet prefixes)
        if not cleaned or cleaned.startswith("--") or cleaned.startswith("#"):
            continue

        # Strip common bullet prefixes (single char only to avoid eating --)
        if cleaned[0] in "-•·*" and (len(cleaned) < 2 or cleaned[1] != "-"):
            cleaned = cleaned[1:].strip()

        # Skip lines that look like explanations (contain certain phrases)
        lower = cleaned.lower()
        if any(
            phrase in lower
            for phrase in [
                "this tactic",
                "this will",
                "we can",
                "you can",
                "try using",
                "explanation:",
                "note:",
            ]
        ):
            continue

        # Remove trailing punctuation
        cleaned = cleaned.rstrip(".,;:")

        # Remove markdown code backticks
        if cleaned.startswith("`") and cleaned.endswith("`"):
            cleaned = cleaned[1:-1]

        if cleaned and cleaned not in seen:
            tactics.append(cleaned)
            seen.add(cleaned)

    return tactics


# =============================================================================
# LLM Execution (Sync for Server Use)
# =============================================================================


# Default prompt template for tactic generation
TACTIC_PROMPT_TEMPLATE = """You are a Lean 4 theorem prover assistant specializing in combinatorics and number theory.

Given the following proof state, suggest tactics that could make progress toward the goal.

Guidelines:
1. Prefer simple tactics (rfl, simp, exact) when applicable
2. For induction, suggest the correct induction principle
3. For combinatorics, consider: Finset, Nat.card, Fintype
4. For number theory, consider: Nat.Prime, Nat.gcd, Nat.mod

Return only tactic names/applications, one per line.
Do not include explanations or comments.

Proof state:
{prompt}"""


def execute_llm_sync(
    llm_command: str,
    prompt: str,
    *,
    timeout: int = LLM_COMMAND_TIMEOUT,
) -> tuple[str, str, int]:
    """Execute LLM command synchronously.

    Args:
        llm_command: Shell command to execute (parsed with shlex.split).
        prompt: The prompt to pass via stdin.
        timeout: Maximum seconds to wait.

    Returns:
        Tuple of (stdout, stderr, exit_code).

    Raises:
        ValueError: If command syntax is invalid.
        FileNotFoundError: If command executable not found.
        subprocess.TimeoutExpired: If command times out.
        OSError: For other execution errors.
    """
    cmd_args = shlex.split(llm_command)
    logger.debug("Executing LLM command: %s", llm_command)

    result = subprocess.run(  # noqa: S603
        cmd_args,
        input=prompt,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )

    logger.debug(
        "LLM response: %d chars (exit code %d)",
        len(result.stdout),
        result.returncode,
    )

    return result.stdout, result.stderr, result.returncode


class LLMExecutionError(RuntimeError):
    """Raised when an LLM command exits non-zero."""


def _truncate_output(stdout: str, stderr: str, *, max_chars: int = 4000) -> str:
    """Truncate stdout/stderr for inclusion in exception messages."""
    combined = f"=== STDOUT ===\n{stdout}\n\n=== STDERR ===\n{stderr}"
    if len(combined) <= max_chars:
        return combined
    return combined[:max_chars] + "\n... (truncated)"


def generate_tactics(
    prompt: str,
    *,
    num_samples: int = 5,
    llm_command: str | None = None,
    timeout: int = LLM_COMMAND_TIMEOUT,
) -> list[str]:
    """Generate tactic suggestions using the LLM router.

    Args:
        prompt: Proof state from Lean Copilot.
        num_samples: Maximum number of tactics to return.
        llm_command: Optional override for LLM command.
        timeout: Timeout for LLM execution.

    Returns:
        List of tactic suggestions (up to num_samples).

    Raises:
        LLMRouterError: If no LLM command is configured.
        ValueError: If command syntax is invalid.
        FileNotFoundError: If command executable not found.
        subprocess.TimeoutExpired: If command times out.
        OSError: For other execution errors.
    """
    # Resolve command via SPEC-032 router
    command = resolve_llm_command(TaskType.tactic_generation, override=llm_command)

    # Build full prompt
    full_prompt = TACTIC_PROMPT_TEMPLATE.format(prompt=prompt)

    # Execute LLM
    stdout, stderr, exit_code = execute_llm_sync(command, full_prompt, timeout=timeout)

    if exit_code != 0:
        details = _truncate_output(stdout, stderr)
        raise LLMExecutionError(
            f"LLM command failed (exit code {exit_code}).\n\n{details}"
        )

    # Parse and return tactics
    tactics = parse_tactics(stdout)
    return tactics[:num_samples]


# =============================================================================
# FastAPI Application Factory
# =============================================================================


def _raise_generate_http_exception(exc: Exception) -> NoReturn:
    from fastapi import HTTPException  # noqa: PLC0415

    if isinstance(exc, LLMRouterError):
        logger.error("LLM router error: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if isinstance(exc, LLMExecutionError):
        logger.error("LLM command failed: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if isinstance(exc, FileNotFoundError):
        logger.error("LLM command not found: %s", exc)
        raise HTTPException(
            status_code=503, detail=f"LLM command not found: {exc}"
        ) from exc
    if isinstance(exc, subprocess.TimeoutExpired):
        logger.error("LLM command timed out: %s", exc)
        raise HTTPException(
            status_code=504,
            detail=f"LLM command timed out after {exc.timeout}s",
        ) from exc
    if isinstance(exc, (ValueError, OSError)):
        logger.error("LLM execution error: %s", exc)
        raise HTTPException(
            status_code=500, detail=f"LLM execution error: {exc}"
        ) from exc

    logger.error("Unexpected generate error: %s", exc)
    raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


def _raise_encode_http_exception(exc: Exception) -> NoReturn:
    from fastapi import HTTPException  # noqa: PLC0415

    from erdos.lean_copilot.embeddings import (  # noqa: PLC0415
        EmbeddingsNotAvailableError,
    )

    if isinstance(exc, EmbeddingsNotAvailableError):
        logger.warning("Embeddings unavailable (degraded mode): %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        logger.error("Embedding error: %s", exc)
        raise HTTPException(status_code=400, detail=f"Invalid request: {exc}") from exc

    logger.error("Unexpected embedding error: %s", exc)
    raise HTTPException(status_code=500, detail=f"Embedding error: {exc}") from exc


def create_app(*, llm_command_override: str | None = None) -> FastAPI:
    """Create FastAPI application for Lean Copilot API.

    Args:
        llm_command_override: Optional override for LLM command (from --llm-cmd).

    Returns:
        Configured FastAPI application.

    Raises:
        CopilotNotAvailableError: If FastAPI/uvicorn not installed.
    """
    if not is_copilot_available():
        raise CopilotNotAvailableError()

    # Import here to avoid ImportError when copilot extra not installed
    from fastapi import FastAPI  # noqa: PLC0415

    app = FastAPI(
        title="Erdos Lean Copilot API",
        description="External model API for Lean Copilot tactic suggestions",
        version="1.0.0",
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    @app.post("/generate", response_model=GenerateResponse)
    async def generate(request: GenerateRequest) -> GenerateResponse:
        """Generate tactic suggestions via SPEC-032 LLM routing."""
        try:
            tactics = await asyncio.to_thread(
                generate_tactics,
                request.prompt,
                num_samples=request.num_samples,
                llm_command=llm_command_override,
            )
            return GenerateResponse(tactics=tactics)
        except Exception as e:  # convert execution errors to HTTP responses
            _raise_generate_http_exception(e)

    @app.post("/encode", response_model=EncodeResponse)
    async def encode(request: EncodeRequest) -> EncodeResponse:
        """Generate embeddings for premise retrieval (SPEC-014 wrapper).

        Returns HTTP 503 if the 'embeddings' extra is not installed (degraded mode).
        """
        try:
            from erdos.lean_copilot.embeddings import encode_texts  # noqa: PLC0415

            embeddings = await asyncio.to_thread(encode_texts, request.texts)
            return EncodeResponse(embeddings=embeddings)
        except Exception as e:  # convert execution errors to HTTP responses
            _raise_encode_http_exception(e)

    return app
