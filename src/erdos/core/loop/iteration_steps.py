"""Internal steps for a single loop iteration.

This module holds small, testable helpers used by the loop iteration state
machine.

Only `apply_patch()` is intended for external use, via the stable re-export
`erdos.core.loop.apply_patch`. Everything else is internal implementation
detail and may change without notice.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from erdos.core.loop.logging import LoopLogger, file_hash
from erdos.core.loop.patch_validator import PatchStatus, validate_patch
from erdos.core.loop.prompt import build_loop_prompt
from erdos.core.loop.result import IterationRecord, LoopStatus
from erdos.core.loop.verifier import (
    LoopExitCondition,
    LoopVerification,
    count_admits,
    count_sorries,
)


if TYPE_CHECKING:
    from pathlib import Path

    from erdos.core.lean import LeanRunner
    from erdos.core.loop.config import LoopConfig
    from erdos.core.models import LeanCheckResult, ProblemRecord
    from erdos.core.ports import LLMExecute


logger = logging.getLogger(__name__)


def apply_patch(file_path: Path, search_text: str, replace_text: str) -> str:
    """Apply a patch to a file."""
    content = file_path.read_text(encoding="utf-8")
    new_content = content.replace(search_text, replace_text, 1)
    file_path.write_text(new_content, encoding="utf-8")
    return new_content


def read_file_state(file_path: Path) -> tuple[str, int, int, int]:
    """Read file content and derive loop metrics."""
    file_content = file_path.read_text(encoding="utf-8")
    sorries = count_sorries(file_content)
    admits = count_admits(file_content)
    size_bytes = len(file_content.encode("utf-8"))
    return file_content, sorries, admits, size_bytes


def run_lean_check_and_log(
    *,
    iteration: int,
    file_path: Path,
    lean_runner: LeanRunner,
    config: LoopConfig,
    loop_logger: LoopLogger,
) -> LeanCheckResult:
    """Run a Lean check and log the result for this iteration."""
    last_check = lean_runner.check(file_path, timeout=config.lean_timeout_seconds)
    loop_logger.log_event(
        "lean_check",
        iteration,
        {
            "success": last_check.success,
            "error_count": len(last_check.errors),
            "file_hash": file_hash(file_path),
        },
    )
    return last_check


def build_prompt_and_log(
    *,
    iteration: int,
    file_path: Path,
    file_content: str,
    problem: ProblemRecord,
    check_result: LeanCheckResult,
    rag_chunks: list[Any],
    config: LoopConfig,
    loop_logger: LoopLogger,
) -> str:
    """Build the loop prompt and log it."""
    prompt = build_loop_prompt(
        file_path=file_path,
        file_content=file_content,
        problem=problem,
        check_result=check_result,
        rag_chunks=rag_chunks,
        config=config,
    )
    loop_logger.log_event("llm_prompt", iteration, {"prompt": prompt})
    return prompt


def execute_llm_and_log(
    *,
    iteration: int,
    llm_command: str,
    prompt: str,
    llm_execute: LLMExecute,
    loop_logger: LoopLogger,
) -> tuple[str, int]:
    """Execute the LLM command and log response metadata."""
    response, exit_code = llm_execute(llm_command, prompt)
    loop_logger.log_event(
        "llm_response", iteration, {"response": response, "exit_code": exit_code}
    )
    return response, exit_code


def handle_llm_error(
    *,
    iteration: int,
    exit_code: int,
    sorries_before: int,
    admits_before: int,
    last_check: LeanCheckResult,
    stall_count: int,
) -> tuple[int, IterationRecord]:
    """Handle LLM execution error, return updated stall_count and record."""
    logger.warning("LLM exited with code %d", exit_code)
    record = IterationRecord(
        iteration=iteration,
        patch_applied=False,
        sorry_before=sorries_before,
        sorry_after=sorries_before,
        admit_before=admits_before,
        admit_after=admits_before,
        check_success=last_check.success,
        error_count=len(last_check.errors),
        reason="llm_error",
    )
    return stall_count + 1, record


def handle_patch_rejected(
    *,
    iteration: int,
    rejection_reason: str,
    sorries_before: int,
    admits_before: int,
    last_check: LeanCheckResult,
    stall_count: int,
) -> tuple[int, IterationRecord]:
    """Handle rejected patch, return updated stall_count and record."""
    logger.warning("Patch rejected: %s", rejection_reason)
    record = IterationRecord(
        iteration=iteration,
        patch_applied=False,
        sorry_before=sorries_before,
        sorry_after=sorries_before,
        admit_before=admits_before,
        admit_after=admits_before,
        check_success=last_check.success,
        error_count=len(last_check.errors),
        reason=rejection_reason,
    )
    return stall_count + 1, record


def _apply_and_verify_patch(
    file_path: Path,
    search_text: str,
    replace_text: str,
    sorries_before: int,
    admits_before: int,
    size_before: int,
    config: LoopConfig,
    loop_logger: LoopLogger,
    iteration: int,
) -> tuple[str, LoopVerification]:
    """Apply patch and run verification."""
    hash_before = file_hash(file_path)
    new_content = apply_patch(file_path, search_text, replace_text)
    hash_after = file_hash(file_path)

    loop_logger.log_event(
        "patch_applied",
        iteration,
        {"hash_before": hash_before, "hash_after": hash_after},
    )

    sorries_after = count_sorries(new_content)
    admits_after = count_admits(new_content)
    size_after = len(new_content.encode("utf-8"))

    verification = LoopVerification(
        compiles=True,  # Will be checked next iteration
        sorry_count_before=sorries_before,
        sorry_count_after=sorries_after,
        admit_count_before=admits_before,
        admit_count_after=admits_after,
        file_size_before=size_before,
        file_size_after=size_after,
        min_file_size_ratio=config.min_file_size_ratio,
    )

    return new_content, verification


def handle_llm_exit_code(
    *,
    iteration: int,
    exit_code: int,
    sorries_before: int,
    admits_before: int,
    last_check: LeanCheckResult,
    stall_count: int,
    config: LoopConfig,
    iterations: list[IterationRecord],
) -> tuple[LoopStatus | None, int]:
    """Handle non-zero LLM exit code."""
    new_stall, record = handle_llm_error(
        iteration=iteration,
        exit_code=exit_code,
        sorries_before=sorries_before,
        admits_before=admits_before,
        last_check=last_check,
        stall_count=stall_count,
    )
    iterations.append(record)
    if new_stall >= config.stall_threshold:
        return LoopStatus.NO_PROGRESS, new_stall
    return None, new_stall


def _handle_patch_rejected_outcome(
    *,
    iteration: int,
    rejection_reason: str,
    sorries_before: int,
    admits_before: int,
    last_check: LeanCheckResult,
    stall_count: int,
    config: LoopConfig,
    iterations: list[IterationRecord],
) -> tuple[LoopStatus | None, int]:
    """Handle rejected patch outcome (including stall threshold)."""
    new_stall, record = handle_patch_rejected(
        iteration=iteration,
        rejection_reason=rejection_reason,
        sorries_before=sorries_before,
        admits_before=admits_before,
        last_check=last_check,
        stall_count=stall_count,
    )
    iterations.append(record)
    if new_stall >= config.stall_threshold:
        return LoopStatus.NO_PROGRESS, new_stall
    return None, new_stall


def validate_patch_and_maybe_record(
    *,
    iteration: int,
    response: str,
    file_path: Path,
    config: LoopConfig,
    loop_logger: LoopLogger,
    sorries_before: int,
    admits_before: int,
    last_check: LeanCheckResult,
    stall_count: int,
    iterations: list[IterationRecord],
) -> tuple[LoopStatus | None, int, str | None, str | None]:
    """Validate a patch response and handle NO_FIX/REJECTED outcomes."""
    patch_result = validate_patch(response, file_path, config)

    if patch_result.status == PatchStatus.NO_FIX:
        loop_logger.log_event(
            "patch_rejected", iteration, {"reason": "no_fix_possible"}
        )
        return LoopStatus.NO_FIX_POSSIBLE, stall_count, None, None

    if patch_result.status == PatchStatus.REJECTED:
        loop_logger.log_event(
            "patch_rejected", iteration, {"reason": patch_result.rejection_reason}
        )
        terminal_status, new_stall = _handle_patch_rejected_outcome(
            iteration=iteration,
            rejection_reason=patch_result.rejection_reason or "unknown",
            sorries_before=sorries_before,
            admits_before=admits_before,
            last_check=last_check,
            stall_count=stall_count,
            config=config,
            iterations=iterations,
        )
        return terminal_status, new_stall, None, None

    return None, stall_count, patch_result.search_text, patch_result.replace_text


def record_no_apply_iteration(
    *,
    iteration: int,
    loop_logger: LoopLogger,
    sorries_before: int,
    admits_before: int,
    last_check: LeanCheckResult,
    iterations: list[IterationRecord],
) -> None:
    """Record a no-apply iteration (valid patch proposed but not applied)."""
    loop_logger.log_event("patch_skipped", iteration, {"reason": "no_apply"})
    iterations.append(
        IterationRecord(
            iteration=iteration,
            patch_applied=False,
            sorry_before=sorries_before,
            sorry_after=sorries_before,
            admit_before=admits_before,
            admit_after=admits_before,
            check_success=last_check.success,
            error_count=len(last_check.errors),
            reason="no_apply",
        )
    )


def apply_patch_and_record_iteration(
    *,
    iteration: int,
    file_path: Path,
    search_text: str,
    replace_text: str,
    sorries_before: int,
    admits_before: int,
    size_before: int,
    config: LoopConfig,
    loop_logger: LoopLogger,
    iterations: list[IterationRecord],
    stall_count: int,
    last_check: LeanCheckResult,
    lean_runner: LeanRunner,
) -> tuple[LoopStatus | None, LeanCheckResult, int]:
    """Apply a validated patch, record iteration, and check for terminal states."""
    new_content, verification = _apply_and_verify_patch(
        file_path,
        search_text,
        replace_text,
        sorries_before,
        admits_before,
        size_before,
        config,
        loop_logger,
        iteration,
    )

    if verification.exit_condition == LoopExitCondition.REGRESSION:
        sorries_after = count_sorries(new_content)
        admits_after = count_admits(new_content)
        iterations.append(
            IterationRecord(
                iteration=iteration,
                patch_applied=True,
                sorry_before=sorries_before,
                sorry_after=sorries_after,
                admit_before=admits_before,
                admit_after=admits_after,
                check_success=last_check.success,
                error_count=len(last_check.errors),
                reason="regression",
            )
        )
        return LoopStatus.REGRESSION, last_check, stall_count

    sorries_after = count_sorries(new_content)
    admits_after = count_admits(new_content)
    iterations.append(
        IterationRecord(
            iteration=iteration,
            patch_applied=True,
            sorry_before=sorries_before,
            sorry_after=sorries_after,
            admit_before=admits_before,
            admit_after=admits_after,
            check_success=True,
            error_count=0,
        )
    )

    new_stall = 0 if verification.is_progress else stall_count + 1

    if sorries_after == 0 and admits_after == 0:
        final_check = lean_runner.check(file_path, timeout=config.lean_timeout_seconds)
        if final_check.success:
            return LoopStatus.SUCCESS, final_check, new_stall

    return None, last_check, new_stall
