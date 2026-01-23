"""Loop → research integration (Spec 027)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from erdos.core.loop.result import LoopResult, LoopStatus
from erdos.core.research.models import AttemptKind, AttemptResult
from erdos.core.research.store_fs import FSResearchStore


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pathlib import Path


def _map_result(status: LoopStatus) -> AttemptResult:
    if status == LoopStatus.SUCCESS:
        return AttemptResult.SUCCESS
    if status == LoopStatus.MAX_ITERATIONS:
        return AttemptResult.PARTIAL
    return AttemptResult.FAILED


def _summarize(loop_result: LoopResult) -> str:
    last = loop_result.iterations[-1] if loop_result.iterations else None
    if last is None:
        patch_stats = "no iterations"
    else:
        patch_stats = (
            f"sorry {last.sorry_before}→{last.sorry_after}, "
            f"admit {last.admit_before}→{last.admit_after}"
        )
        if last.reason:
            patch_stats += f", reason={last.reason}"
    return (
        f"status={loop_result.status.value}; "
        f"iterations={loop_result.iterations_completed}/{loop_result.iterations_max}; "
        f"{patch_stats}"
    )


@dataclass(frozen=True)
class LoopAttemptWriteResult:
    attempt_path: Path


def write_attempt_from_loop_result(
    problem_id: int,
    loop_result: LoopResult,
    *,
    repo_root: Path | None,
) -> LoopAttemptWriteResult:
    """Write a structured attempt record under `research/problems/{id}/attempts/`."""
    store = FSResearchStore(repo_root=repo_root)

    record, path = store.attempt_log(
        problem_id,
        kind=AttemptKind.LEAN_LOOP,
        result=_map_result(loop_result.status),
        summary=_summarize(loop_result),
        lean_file=str(loop_result.file),
        loop_log=str(loop_result.run_log_path) if loop_result.run_log_path else None,
    )
    logger.debug("Wrote loop attempt record %s", record.id)
    return LoopAttemptWriteResult(attempt_path=path)
