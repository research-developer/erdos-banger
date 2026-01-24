"""Loop orchestration for iterative Lean proof attempts.

Per spec-012-loop-command.md and spec-012-design.md.

This package provides the loop functionality split into modules:
- config.py: LoopConfig (configuration dataclass)
- verifier.py: LoopVerification, LoopExitCondition, count_sorries, count_admits
- patch_validator.py: validate_patch, PatchStatus, PatchResult, MatchStatus
- result.py: LoopStatus, IterationRecord, LoopResult
- logging.py: LoopLogger, generate_run_id, file_hash
- prompt.py: build_loop_prompt, budget_context
- iteration_steps.py: apply_patch (public helper)
- runner.py: run_loop
- service.py: execute_proof_loop (application-level orchestration)
"""

# Public API re-exports
from erdos.core.loop.config import LoopConfig
from erdos.core.loop.iteration_steps import apply_patch
from erdos.core.loop.logging import LoopLogger, file_hash, generate_run_id
from erdos.core.loop.patch_validator import (
    MatchResult,
    MatchStatus,
    PatchResult,
    PatchStatus,
    find_match,
    parse_search_replace,
    validate_patch,
)
from erdos.core.loop.prompt import budget_context, build_loop_prompt
from erdos.core.loop.result import IterationRecord, LoopResult, LoopStatus
from erdos.core.loop.runner import run_loop
from erdos.core.loop.service import execute_proof_loop
from erdos.core.loop.verifier import (
    LoopExitCondition,
    LoopVerification,
    count_admits,
    count_sorries,
)


__all__ = [
    "IterationRecord",
    "LoopConfig",
    "LoopExitCondition",
    "LoopLogger",
    "LoopResult",
    "LoopStatus",
    "LoopVerification",
    "MatchResult",
    "MatchStatus",
    "PatchResult",
    "PatchStatus",
    "apply_patch",
    "budget_context",
    "build_loop_prompt",
    "count_admits",
    "count_sorries",
    "execute_proof_loop",
    "file_hash",
    "find_match",
    "generate_run_id",
    "parse_search_replace",
    "run_loop",
    "validate_patch",
]
