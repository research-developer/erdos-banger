# Spec 012: Loop Command (Deferred to v1.2+)

> Defines the `erdos loop` command for iterative LLM-assisted Lean proof attempts.

**Status:** Deferred - This spec documents the design for future implementation.

---

## Overview

The loop command orchestrates an automated prove-check-fix cycle for Lean formalization. It combines the Lean runner (Spec 007) with LLM capabilities to iteratively attempt proofs, process errors, and refine solutions.

### Why Deferred?

This command is deferred to v1.2+ because:

1. **Foundation required** - Needs stable Lean integration (Spec 007), search index (Spec 006), and ask command (Spec 011) first
2. **Safety concerns** - Automated code generation requires careful guardrails
3. **Complexity** - Multi-step agent loop with state management is non-trivial
4. **Evaluation** - Need metrics to measure proof attempt quality

### Core Workflow

```
erdos loop <problem_id>
       │
       ▼
┌────────────────────────┐
│ Initialize              │
│  - Load problem         │
│  - Check/create Lean file│
│  - Verify Lean env      │
└───────────┬────────────┘
            │
┌───────────▼───────────┐
│   Main Loop (N iter)   │◄────────────────┐
│                        │                  │
│  1. Check for sorry    │                  │
│  2. If none: SUCCESS   ├──► Exit          │
│  3. Retrieve context   │                  │
│  4. LLM: propose fix   │                  │
│  5. Apply changes      │                  │
│  6. lean check         │                  │
│  7. Parse errors       │                  │
│  8. If errors: loop    ├──────────────────┘
│  9. Log iteration      │
└───────────┬────────────┘
            │ max iterations reached
            ▼
┌────────────────────────┐
│ Finalize               │
│  - Save progress       │
│  - Generate report     │
│  - Return summary      │
└────────────────────────┘
```

### Guiding Principles

1. **Safety first** - Limit iterations, require confirmation, sandbox code changes
2. **Transparency** - Log every step, show what LLM proposed
3. **Recoverable** - Can resume from any iteration
4. **Measurable** - Track metrics (sorry count, error count, etc.)

---

## 1) CLI Interface

### Command Signature

```
erdos loop <problem_id> [OPTIONS]

Arguments:
  problem_id    Problem ID to work on (required)

Options:
  --max-iter, -n INT      Max iterations [default: 10]
  --yes, -y               Auto-confirm all prompts
  --no-apply              Propose only, don't modify files
  --from-iteration INT    Resume from specific iteration
  --model MODEL           LLM model to use
  --timeout INT           Lean check timeout in seconds [default: 120]
  --json                  Output as JSON for machine consumption
```

### Examples

```bash
# Basic usage: run proof loop with default settings
erdos loop 6

# Run with auto-confirmation (non-interactive)
erdos loop 6 --yes --max-iter 5

# Propose changes without applying
erdos loop 6 --no-apply

# Resume from previous run
erdos loop 6 --from-iteration 3

# JSON output for automation
erdos loop 6 --json
```

### Output (Human Mode - Interactive)

```
Starting proof loop for Problem 6: Small primes in AP

Iteration 1/10
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Analyzing Erdos/Problem006.lean...
  Found 1 sorry at line 42

Retrieving context for: "small primes arithmetic progression Lean proof"
  Retrieved 3 relevant chunks

LLM proposing fix...

Proposed change:
┌─────────────────────────────────────────────────────────┐
│ -- Line 42                                               │
│ - theorem problem_6 : True := by sorry                   │
│ + theorem problem_6 : True := by                         │
│ +   trivial                                              │
└─────────────────────────────────────────────────────────┘

Apply this change? [y/N/s(kip)/q(uit)]: y

Applying change...
Running lean check...

✓ Erdos/Problem006.lean compiled successfully (iteration 1)

No remaining sorry - proof complete!

Summary:
  Iterations: 1
  Sorries resolved: 1
  Final status: SUCCESS
  Log: logs/loop_6_20260117_143000.yaml
```

### Output (JSON Mode)

```json
{
  "schema_version": 1,
  "command": "erdos loop",
  "success": true,
  "data": {
    "problem_id": 6,
    "status": "success",
    "iterations_completed": 1,
    "iterations_max": 10,
    "sorries_initial": 1,
    "sorries_final": 0,
    "errors_initial": 0,
    "errors_final": 0,
    "log_path": "logs/loop_6_20260117_143000.yaml",
    "iterations": [
      {
        "number": 1,
        "sorries_before": 1,
        "sorries_after": 0,
        "errors_before": 0,
        "errors_after": 0,
        "change_applied": true,
        "lean_success": true,
        "duration_ms": 2341
      }
    ],
    "final_file": "formal/lean/Erdos/Problem006.lean"
  },
  "timestamp": "2026-01-17T14:30:00Z",
  "duration_ms": 5432
}
```

---

## 2) Domain Models

```python
# src/erdos/domain/loop.py
"""Loop command domain models."""

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import Field

from erdos.domain.base import ErdosBaseModel
from erdos.domain.lean import LeanError


class LoopStatus(str, Enum):
    """Status of the loop execution."""

    SUCCESS = "success"           # All sorries resolved
    PARTIAL = "partial"           # Some sorries resolved
    NO_PROGRESS = "no_progress"   # No sorries resolved
    MAX_ITER = "max_iterations"   # Hit iteration limit
    USER_ABORT = "user_abort"     # User cancelled
    ERROR = "error"               # Fatal error


class ProposedChange(ErdosBaseModel):
    """A change proposed by the LLM."""

    file: Annotated[str, Field(description="File to modify")]
    line_start: Annotated[int, Field(ge=1)]
    line_end: Annotated[int, Field(ge=1)]
    old_content: Annotated[str, Field(description="Content being replaced")]
    new_content: Annotated[str, Field(description="Proposed replacement")]
    rationale: Annotated[str | None, Field(default=None)] = None


class IterationResult(ErdosBaseModel):
    """Result of a single loop iteration."""

    number: Annotated[int, Field(ge=1)]

    # State before
    sorries_before: Annotated[int, Field(ge=0)]
    errors_before: Annotated[list[LeanError], Field(default_factory=list)]

    # LLM interaction
    prompt_tokens: Annotated[int | None, Field(default=None)] = None
    completion_tokens: Annotated[int | None, Field(default=None)] = None
    proposed_change: Annotated[ProposedChange | None, Field(default=None)] = None

    # User interaction
    change_applied: Annotated[bool, Field(default=False)] = False
    user_skipped: Annotated[bool, Field(default=False)] = False

    # State after
    sorries_after: Annotated[int, Field(ge=0)]
    errors_after: Annotated[list[LeanError], Field(default_factory=list)]
    lean_success: Annotated[bool, Field(default=False)] = False

    # Timing
    started_at: Annotated[datetime, Field()]
    completed_at: Annotated[datetime, Field()]

    @property
    def duration_ms(self) -> int:
        return int((self.completed_at - self.started_at).total_seconds() * 1000)

    @property
    def made_progress(self) -> bool:
        return self.sorries_after < self.sorries_before


class LoopResult(ErdosBaseModel):
    """Result of a complete loop execution."""

    problem_id: Annotated[int, Field(ge=1)]
    status: LoopStatus

    # Iteration info
    iterations_completed: Annotated[int, Field(ge=0)]
    iterations_max: Annotated[int, Field(ge=1)]
    iterations: Annotated[list[IterationResult], Field(default_factory=list)]

    # Progress summary
    sorries_initial: Annotated[int, Field(ge=0)]
    sorries_final: Annotated[int, Field(ge=0)]
    errors_initial: Annotated[int, Field(ge=0)]
    errors_final: Annotated[int, Field(ge=0)]

    # Output
    log_path: Annotated[str | None, Field(default=None)] = None
    final_file: Annotated[str | None, Field(default=None)] = None

    # Timing
    started_at: Annotated[datetime, Field()]
    completed_at: Annotated[datetime, Field()]

    @property
    def duration_ms(self) -> int:
        return int((self.completed_at - self.started_at).total_seconds() * 1000)

    @property
    def sorries_resolved(self) -> int:
        return max(0, self.sorries_initial - self.sorries_final)
```

---

## 3) Loop Service

```python
# src/erdos/application/loop_service.py
"""Loop service orchestrating proof attempts."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from erdos.application.retrieval_service import RetrievalService
from erdos.domain.lean import LeanCheckResult
from erdos.domain.loop import (
    IterationResult,
    LoopResult,
    LoopStatus,
    ProposedChange,
)
from erdos.domain.problem import ProblemRecord
from erdos.infrastructure.lean.runner import LeanRunner
from erdos.infrastructure.llm.claude import ClaudeClient
from erdos.ports.problem_repository import ProblemRepository
from erdos.ports.searcher import Searcher


class LoopService:
    """
    Orchestrates iterative proof attempts.

    Coordinates:
    - Lean file analysis (sorry detection)
    - Context retrieval
    - LLM-based fix proposals
    - Change application
    - Lean compilation
    - Logging
    """

    SYSTEM_PROMPT = """You are a Lean 4 proof assistant helping to formalize Erdős problems.

Your task is to fill in `sorry` placeholders with actual proofs or definitions.

Guidelines:
1. Only propose changes that compile in Lean 4
2. Use mathlib tactics when appropriate
3. If a proof is too complex, break it into lemmas
4. Prefer simple, readable proofs over clever ones
5. If unsure, use `sorry` with a comment explaining what's needed

Output format:
1. First, explain your reasoning briefly
2. Then provide the exact code to replace the sorry
3. Mark the replacement clearly with ```lean blocks"""

    def __init__(
        self,
        repository: ProblemRepository,
        searcher: Searcher,
        lean_runner: LeanRunner,
        llm_client: ClaudeClient,
        *,
        log_dir: Path | None = None,
    ) -> None:
        self._repository = repository
        self._retrieval = RetrievalService(searcher)
        self._lean = lean_runner
        self._llm = llm_client
        self._log_dir = log_dir or Path("logs")

    def run_loop(
        self,
        problem_id: int,
        *,
        max_iterations: int = 10,
        auto_apply: bool = False,
        confirm_callback: Callable[[ProposedChange], bool] | None = None,
        timeout: int = 120,
    ) -> LoopResult:
        """
        Run the proof loop for a problem.

        Args:
            problem_id: Problem to work on
            max_iterations: Maximum iterations to run
            auto_apply: If True, apply changes without confirmation
            confirm_callback: Function to confirm changes (for interactive mode)
            timeout: Lean check timeout in seconds

        Returns:
            LoopResult with full execution details
        """
        started_at = datetime.now(UTC)

        # Load problem
        problem = self._repository.get_by_id(problem_id)
        if problem is None:
            raise ValueError(f"Problem {problem_id} not found")

        # Find Lean file
        lean_file = self._find_lean_file(problem_id)
        if not lean_file.exists():
            raise ValueError(f"Lean file not found: {lean_file}")

        # Initial analysis
        initial_check = self._lean.check(lean_file, timeout=timeout)
        sorries_initial = self._count_sorries(lean_file)

        iterations: list[IterationResult] = []

        for i in range(1, max_iterations + 1):
            iter_result = self._run_iteration(
                problem=problem,
                lean_file=lean_file,
                iteration=i,
                auto_apply=auto_apply,
                confirm_callback=confirm_callback,
                timeout=timeout,
            )
            iterations.append(iter_result)

            # Check termination conditions
            if iter_result.lean_success and iter_result.sorries_after == 0:
                # All sorries resolved!
                break

            if iter_result.user_skipped and not auto_apply:
                # User wants to stop
                break

            if not iter_result.made_progress and i > 2:
                # No progress in recent iterations
                no_progress_streak = sum(
                    1 for r in iterations[-3:] if not r.made_progress
                )
                if no_progress_streak >= 3:
                    break

        # Final state
        final_sorries = self._count_sorries(lean_file)
        final_check = self._lean.check(lean_file, timeout=timeout)

        # Determine status
        if final_sorries == 0 and final_check.success:
            status = LoopStatus.SUCCESS
        elif final_sorries < sorries_initial:
            status = LoopStatus.PARTIAL
        elif len(iterations) >= max_iterations:
            status = LoopStatus.MAX_ITER
        else:
            status = LoopStatus.NO_PROGRESS

        completed_at = datetime.now(UTC)

        # Save log
        log_path = self._save_log(problem_id, iterations, started_at)

        return LoopResult(
            problem_id=problem_id,
            status=status,
            iterations_completed=len(iterations),
            iterations_max=max_iterations,
            iterations=iterations,
            sorries_initial=sorries_initial,
            sorries_final=final_sorries,
            errors_initial=len(initial_check.errors),
            errors_final=len(final_check.errors),
            log_path=str(log_path) if log_path else None,
            final_file=str(lean_file),
            started_at=started_at,
            completed_at=completed_at,
        )

    def _run_iteration(
        self,
        problem: ProblemRecord,
        lean_file: Path,
        iteration: int,
        *,
        auto_apply: bool,
        confirm_callback: Callable[[ProposedChange], bool] | None,
        timeout: int,
    ) -> IterationResult:
        """Run a single iteration of the loop."""
        started_at = datetime.now(UTC)

        # Analyze current state
        check_before = self._lean.check(lean_file, timeout=timeout)
        sorries_before = self._count_sorries(lean_file)

        # Read file content
        content = lean_file.read_text(encoding="utf-8")

        # Find first sorry location
        sorry_info = self._find_sorry(content)
        if sorry_info is None:
            # No sorry found - done!
            return IterationResult(
                number=iteration,
                sorries_before=sorries_before,
                errors_before=check_before.errors,
                sorries_after=0,
                errors_after=check_before.errors,
                lean_success=check_before.success,
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )

        # Retrieve context
        chunks = self._retrieval.retrieve(problem, "Lean proof tactics", limit=5)

        # Build prompt
        prompt = self._build_prompt(problem, content, sorry_info, chunks, check_before)

        # Get LLM proposal
        response, usage = self._llm.generate(
            prompt,
            system=self.SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=2048,
        )

        # Parse proposed change
        proposed = self._parse_proposal(response, lean_file, sorry_info)

        # Decide whether to apply
        should_apply = auto_apply
        user_skipped = False

        if not auto_apply and confirm_callback and proposed:
            should_apply = confirm_callback(proposed)
            user_skipped = not should_apply

        # Apply change if approved
        change_applied = False
        if should_apply and proposed:
            self._apply_change(lean_file, proposed)
            change_applied = True

        # Check result
        check_after = self._lean.check(lean_file, timeout=timeout)
        sorries_after = self._count_sorries(lean_file)

        return IterationResult(
            number=iteration,
            sorries_before=sorries_before,
            errors_before=check_before.errors,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            proposed_change=proposed,
            change_applied=change_applied,
            user_skipped=user_skipped,
            sorries_after=sorries_after,
            errors_after=check_after.errors,
            lean_success=check_after.success,
            started_at=started_at,
            completed_at=datetime.now(UTC),
        )

    def _find_lean_file(self, problem_id: int) -> Path:
        """Find Lean file for problem."""
        return self._lean.project_path / "Erdos" / f"Problem{problem_id:03d}.lean"

    def _count_sorries(self, lean_file: Path) -> int:
        """Count sorry occurrences in file."""
        content = lean_file.read_text(encoding="utf-8")
        return content.count("sorry")

    def _find_sorry(self, content: str) -> dict | None:
        """Find first sorry in content with context."""
        import re

        match = re.search(r"\bsorry\b", content)
        if not match:
            return None

        # Find line number
        line_num = content[:match.start()].count("\n") + 1

        # Get surrounding context (5 lines before/after)
        lines = content.split("\n")
        start = max(0, line_num - 6)
        end = min(len(lines), line_num + 5)

        return {
            "line": line_num,
            "column": match.start() - content.rfind("\n", 0, match.start()),
            "context_lines": lines[start:end],
            "context_start": start + 1,
        }

    def _build_prompt(
        self,
        problem: ProblemRecord,
        content: str,
        sorry_info: dict,
        chunks: list,
        check_result: LeanCheckResult,
    ) -> str:
        """Build prompt for LLM."""
        parts = [
            f"# Problem {problem.id}: {problem.title}",
            f"\nStatement: {problem.statement}",
            "\n\n# Current Lean File (excerpt around sorry)",
            "```lean",
        ]

        for i, line in enumerate(sorry_info["context_lines"]):
            line_num = sorry_info["context_start"] + i
            marker = " >>> " if line_num == sorry_info["line"] else "     "
            parts.append(f"{marker}{line_num}: {line}")

        parts.append("```")

        if check_result.errors:
            parts.append("\n\n# Current Errors")
            for err in check_result.errors[:5]:
                parts.append(f"- Line {err.line}: {err.message}")

        if chunks:
            parts.append("\n\n# Relevant Context")
            for i, chunk in enumerate(chunks[:3], 1):
                parts.append(f"\n[{i}] {chunk.text[:500]}...")

        parts.append("\n\n# Task")
        parts.append(f"Replace the sorry at line {sorry_info['line']} with a valid proof or definition.")
        parts.append("Provide the exact replacement code in a ```lean block.")

        return "\n".join(parts)

    def _parse_proposal(
        self, response: str, lean_file: Path, sorry_info: dict
    ) -> ProposedChange | None:
        """Parse LLM response into a ProposedChange."""
        import re

        # Find lean code block
        match = re.search(r"```lean\n(.*?)```", response, re.DOTALL)
        if not match:
            return None

        new_content = match.group(1).strip()

        # Read current line
        lines = lean_file.read_text(encoding="utf-8").split("\n")
        old_content = lines[sorry_info["line"] - 1] if sorry_info["line"] <= len(lines) else ""

        return ProposedChange(
            file=str(lean_file),
            line_start=sorry_info["line"],
            line_end=sorry_info["line"],
            old_content=old_content,
            new_content=new_content,
        )

    def _apply_change(self, lean_file: Path, change: ProposedChange) -> None:
        """Apply a proposed change to the file."""
        lines = lean_file.read_text(encoding="utf-8").split("\n")

        # Replace the line(s)
        new_lines = (
            lines[:change.line_start - 1]
            + change.new_content.split("\n")
            + lines[change.line_end:]
        )

        lean_file.write_text("\n".join(new_lines), encoding="utf-8")

    def _save_log(
        self, problem_id: int, iterations: list[IterationResult], started_at: datetime
    ) -> Path | None:
        """Save execution log."""
        import yaml

        self._log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = started_at.strftime("%Y%m%d_%H%M%S")
        log_path = self._log_dir / f"loop_{problem_id}_{timestamp}.yaml"

        log_data = {
            "problem_id": problem_id,
            "started_at": started_at.isoformat(),
            "iterations": [
                {
                    "number": it.number,
                    "sorries_before": it.sorries_before,
                    "sorries_after": it.sorries_after,
                    "change_applied": it.change_applied,
                    "lean_success": it.lean_success,
                    "duration_ms": it.duration_ms,
                }
                for it in iterations
            ],
        }

        log_path.write_text(yaml.dump(log_data), encoding="utf-8")
        return log_path
```

---

## 4) Safety Considerations

### Guardrails

| Guardrail | Implementation |
|-----------|----------------|
| Iteration limit | `--max-iter` caps total iterations |
| Confirmation | Interactive confirmation before each change |
| Preview mode | `--no-apply` shows proposals without modifying files |
| Sandboxing | Changes only to files in `formal/lean/Erdos/` |
| Backup | Create `.bak` before first modification |
| Rollback | Store original content, allow `--from-iteration` resume |

### What's Blocked

- Modifications outside Lean project directory
- System command execution in proposed changes
- Network access from within Lean code
- Deletion of files

### Logging

Every iteration logs:

```yaml
# logs/loop_6_20260117_143000.yaml
problem_id: 6
started_at: "2026-01-17T14:30:00Z"
model: "claude-sonnet-4-20250514"
iterations:
  - number: 1
    started_at: "2026-01-17T14:30:00Z"
    sorries_before: 1
    prompt_tokens: 1250
    completion_tokens: 342
    proposed_change:
      file: "formal/lean/Erdos/Problem006.lean"
      line_start: 42
      old_content: "theorem problem_6 : True := by sorry"
      new_content: "theorem problem_6 : True := by trivial"
    change_applied: true
    lean_result:
      success: true
      errors: []
    sorries_after: 0
    duration_ms: 2341
```

---

## 5) Verification: This Spec is Testable

### Unit Tests

```python
# tests/unit/test_loop.py
"""Unit tests for loop functionality."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from erdos.application.loop_service import LoopService
from erdos.domain.lean import LeanCheckResult
from erdos.domain.loop import LoopStatus
from erdos.domain.problem import ProblemRecord, ProblemStatus


@pytest.fixture
def sample_problem() -> ProblemRecord:
    return ProblemRecord(
        id=6,
        title="Test Problem",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )


@pytest.fixture
def mock_lean_file(tmp_path: Path) -> Path:
    lean_dir = tmp_path / "formal" / "lean" / "Erdos"
    lean_dir.mkdir(parents=True)
    lean_file = lean_dir / "Problem006.lean"
    lean_file.write_text("theorem test : True := by sorry\n")
    return lean_file


class TestLoopService:
    def test_detects_no_sorry(self, tmp_path: Path) -> None:
        """Loop completes immediately when no sorry in file."""
        lean_dir = tmp_path / "formal" / "lean" / "Erdos"
        lean_dir.mkdir(parents=True)
        lean_file = lean_dir / "Problem006.lean"
        lean_file.write_text("theorem test : True := by trivial\n")

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = ProblemRecord(
            id=6, title="Test", statement="Test", status=ProblemStatus.OPEN
        )

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = []

        mock_lean = MagicMock()
        mock_lean.project_path = tmp_path / "formal" / "lean"
        mock_lean.check.return_value = LeanCheckResult(
            file="Erdos/Problem006.lean",
            success=True,
            errors=[],
        )

        mock_llm = MagicMock()

        service = LoopService(
            mock_repo, mock_searcher, mock_lean, mock_llm, log_dir=tmp_path / "logs"
        )

        result = service.run_loop(6, max_iterations=5, auto_apply=True)

        assert result.status == LoopStatus.SUCCESS
        assert result.sorries_initial == 0

    def test_respects_max_iterations(
        self, tmp_path: Path, mock_lean_file: Path
    ) -> None:
        """Loop stops at max iterations."""
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = ProblemRecord(
            id=6, title="Test", statement="Test", status=ProblemStatus.OPEN
        )

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = []

        mock_lean = MagicMock()
        mock_lean.project_path = mock_lean_file.parent.parent.parent
        mock_lean.check.return_value = LeanCheckResult(
            file="Erdos/Problem006.lean",
            success=False,
            errors=[],
        )

        mock_llm = MagicMock()
        mock_llm.generate.return_value = ("```lean\nsorry\n```", MagicMock())

        service = LoopService(
            mock_repo, mock_searcher, mock_lean, mock_llm, log_dir=tmp_path / "logs"
        )

        result = service.run_loop(6, max_iterations=3, auto_apply=True)

        assert result.iterations_completed == 3
        assert result.status == LoopStatus.MAX_ITER
```

### Acceptance Criteria

```bash
# Prerequisites
uv run erdos lean init
uv run erdos lean formalize 6

# 1. Basic loop execution
uv run erdos loop 6 --max-iter 3 --yes

# 2. Preview mode (no changes)
uv run erdos loop 6 --no-apply

# 3. JSON output
uv run erdos loop 6 --json --max-iter 1

# 4. Log file created
ls logs/loop_6_*.yaml

# 5. Tests pass
uv run pytest tests/unit/test_loop.py -v
```

---

## 6) Future Extensions

### Resume Support

```bash
# Resume from specific iteration
erdos loop 6 --from-iteration 3
```

### Batch Mode

```bash
# Run loop on multiple problems
erdos loop --all --status open --max-iter 5
```

### LeanDojo Integration

Use LeanDojo for better proof state extraction and tactic suggestions.

### Evaluation Metrics

Track and report:
- Success rate (problems with all sorries resolved)
- Average iterations to success
- Token usage per proof
- Common error patterns

---

## References

- [Spec 007: Lean Integration](spec-007-lean-integration.md)
- [LeanDojo](https://leandojo.org/)
- [Mathlib4 Tactics](https://leanprover-community.github.io/mathlib4_docs/)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-17 | Initial spec (deferred) |
