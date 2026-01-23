"""Loop service - application-level orchestration for proof loop.

Provides the execute_proof_loop() entrypoint that coordinates:
- Problem lookup
- Lean project initialization
- Skeleton generation
- Loop execution
- Result mapping to CLIOutput

This separates application orchestration from the CLI layer (SRP).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from erdos.core.exit_codes import ExitCode
from erdos.core.formalizer import generate_skeleton
from erdos.core.lean_runner import LeanRunner, LeanRunnerError
from erdos.core.loop.result import LoopResult, LoopStatus
from erdos.core.loop.runner import run_loop
from erdos.core.models import CLIOutput
from erdos.core.research.loop_integration import write_attempt_from_loop_result
from erdos.core.research.paths import get_problem_dir


if TYPE_CHECKING:
    from pathlib import Path

    from erdos.core.loop.config import LoopConfig
    from erdos.core.ports import ProblemRepository


logger = logging.getLogger(__name__)


def execute_proof_loop(
    problem_id: int,
    *,
    repo: ProblemRepository,
    project_path: Path,
    config: LoopConfig,
    llm_command: str | None,
    no_apply: bool,
    repo_root: Path | None = None,
) -> CLIOutput:
    """Execute the proof loop for a problem.

    Orchestrates the full loop workflow:
    1. Problem lookup from repository
    2. Lean project initialization (if needed)
    3. Skeleton generation (if needed)
    4. Loop execution via run_loop()
    5. Result mapping to CLIOutput

    Args:
        problem_id: Problem ID to work on
        repo: Problem repository for lookups
        project_path: Path to Lean project
        config: Loop configuration
        llm_command: LLM command (or None)
        no_apply: If True, don't write changes to disk

    Returns:
        CLIOutput with result data or error
    """
    # Get problem
    problem = repo.get_by_id(problem_id)
    if problem is None:
        return CLIOutput.err(
            command="erdos loop",
            error_type="NotFound",
            message=f"Problem {problem_id} not found",
            code=ExitCode.NOT_FOUND,
        )

    # Ensure Lean project exists
    if not project_path.exists():
        try:
            runner = LeanRunner(project_path)
            runner.init(fetch_mathlib=True)
        except LeanRunnerError as e:
            return CLIOutput.err(
                command="erdos loop",
                error_type="InitError",
                message=f"Failed to initialize Lean project: {e}",
                code=ExitCode.ERROR,
            )

    # Ensure Lean file exists
    file_path = project_path / "Erdos" / f"Problem{problem_id:03d}.lean"
    if not file_path.exists():
        try:
            generate_skeleton(problem, project_path, overwrite=False)
        except Exception as e:
            return CLIOutput.err(
                command="erdos loop",
                error_type="FormalizerError",
                message=f"Failed to generate skeleton: {e}",
                code=ExitCode.ERROR,
            )

    # Create Lean runner
    try:
        lean_runner = LeanRunner(project_path)
    except LeanRunnerError as e:
        return CLIOutput.err(
            command="erdos loop",
            error_type="LeanRunnerError",
            message=str(e),
            code=ExitCode.ERROR,
        )

    # Build RAG context: always include per-problem synthesis when present.
    rag_chunks: list[dict[str, str]] = []
    synthesis_path = get_problem_dir(repo_root, problem_id) / "SYNTHESIS.md"
    if synthesis_path.exists():
        try:
            text = synthesis_path.read_text(encoding="utf-8")
        except OSError:
            text = ""
        if text.strip():
            rag_chunks.append(
                {
                    "chunk_id": f"research_{problem_id}_synthesis",
                    "source_type": "research_synthesis",
                    "text": text,
                }
            )
    rag_chunks = rag_chunks[: max(config.rag_limit, 0)]

    # Run the loop
    try:
        result = run_loop(
            problem=problem,
            file_path=file_path,
            config=config,
            lean_runner=lean_runner,
            llm_command=llm_command,
            no_apply=no_apply,
            rag_chunks=rag_chunks,
        )
    except Exception as e:
        logger.exception("Loop execution failed")
        return CLIOutput.err(
            command="erdos loop",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )

    # Write a structured attempt record (best-effort; never block loop result).
    try:
        write_attempt_from_loop_result(problem_id, result, repo_root=repo_root)
    except Exception as e:
        logger.warning("Failed to write research attempt record: %s", e)

    return _map_loop_result_to_cli_output(result)


def _map_loop_result_to_cli_output(result: LoopResult) -> CLIOutput:
    """Map LoopResult to CLIOutput.

    Per spec-012: success=true ONLY when proof is complete (zero sorry/admit, compiles).
    All other statuses return success=false with loop data in error object.
    """
    result_dict = result.to_dict()

    if result.status == LoopStatus.SUCCESS:
        return CLIOutput.ok(
            command="erdos loop",
            data=result_dict,
        )

    # Map status to error type and exit code
    status_map: dict[LoopStatus, tuple[str, str, ExitCode]] = {
        LoopStatus.MAX_ITERATIONS: (
            "MaxIterations",
            f"Reached maximum iterations ({result.iterations_max})",
            ExitCode.ERROR,
        ),
        LoopStatus.NO_PROGRESS: (
            "NoProgress",
            "No progress after multiple iterations",
            ExitCode.ERROR,
        ),
        LoopStatus.NO_FIX_POSSIBLE: (
            "NoFixPossible",
            "LLM indicated no fix is possible",
            ExitCode.ERROR,
        ),
        LoopStatus.REGRESSION: (
            "Regression",
            "File size shrank unexpectedly (possible deletion attack)",
            ExitCode.ERROR,
        ),
        LoopStatus.LLM_REQUIRED: (
            "LLMRequired",
            "LLM required but not configured (set ERDOS_LLM_COMMAND)",
            ExitCode.CONFIG_ERROR,
        ),
        LoopStatus.ERROR: (
            "Error",
            "Loop execution failed",
            ExitCode.ERROR,
        ),
    }

    error_type, message, exit_code = status_map.get(
        result.status, ("Error", f"Unknown status: {result.status}", ExitCode.ERROR)
    )

    # Include loop result data in error object per spec-012
    # (extra summary keys allowed by CLIOutput invariants)
    error_obj = {
        "type": error_type,
        "message": message,
        "code": int(exit_code),
        **result_dict,  # Include full loop result data
    }

    return CLIOutput(
        command="erdos loop",
        success=False,
        data=None,
        error=error_obj,
    )


__all__ = ["execute_proof_loop"]
