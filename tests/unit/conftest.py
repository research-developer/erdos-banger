"""Fixtures for unit tests - no I/O, no subprocesses."""

from __future__ import annotations

import pytest

from erdos.core.models import ProblemRecord, ProblemStatus


@pytest.fixture
def lean_error_output() -> str:
    """Captured Lean error output for parsing tests."""
    return """
Erdos/Problem006.lean:12:5: error: unknown identifier 'Nat.prime'
Erdos/Problem006.lean:15:10: error: type mismatch
  has type
    Nat
  but is expected to have type
    Prop
"""


class _MockLoader:
    def __init__(self, problem: ProblemRecord | None) -> None:
        self._problem = problem

    def get_by_id(self, problem_id: int) -> ProblemRecord | None:
        if self._problem is None:
            return None
        if self._problem.id != problem_id:
            return None
        return self._problem


@pytest.fixture
def mock_loader_with_problem() -> _MockLoader:
    problem = ProblemRecord(
        id=6,
        title="Small primes",
        statement="Prove that...",
        status=ProblemStatus.OPEN,
        prize=100,
        tags=["primes"],
    )
    return _MockLoader(problem)


@pytest.fixture
def mock_loader_empty() -> _MockLoader:
    return _MockLoader(None)
