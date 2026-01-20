"""Concrete repository implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterator

    from erdos.core.models import ProblemRecord


class InMemoryProblemRepository:
    """In-memory ProblemRepository implementation (primarily for tests)."""

    def __init__(self, problems: list[ProblemRecord]) -> None:
        self._problems = {p.id: p for p in problems}

    def get_by_id(self, problem_id: int) -> ProblemRecord | None:
        return self._problems.get(problem_id)

    def load_all(self, *, use_cache: bool = True) -> list[ProblemRecord]:
        _ = use_cache
        return sorted(self._problems.values(), key=lambda p: p.id)

    def iter_problems(self) -> Iterator[ProblemRecord]:
        yield from self.load_all()
