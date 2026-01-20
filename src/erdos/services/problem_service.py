"""Problem-focused services and value objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from erdos.core.models import ProblemRecord, ProblemStatus
    from erdos.core.ports import ProblemRepository


@dataclass(frozen=True)
class ProblemFilter:
    """Value object for filtering problems."""

    status: ProblemStatus | None = None
    prize_min: int | None = None
    prize_max: int | None = None
    tags: list[str] | None = None
    formalized: bool | None = None

    def matches(self, problem: ProblemRecord) -> bool:
        """Return True if the problem satisfies all configured criteria."""
        if self.status is not None and problem.status != self.status:
            return False

        if self.prize_min is not None and problem.prize < self.prize_min:
            return False
        if self.prize_max is not None and problem.prize > self.prize_max:
            return False

        if self.tags:
            tag_set = {t.lower() for t in self.tags}
            problem_tags = {t.lower() for t in problem.tags}
            if not tag_set.intersection(problem_tags):
                return False

        if self.formalized is not None:
            return problem.formalized == self.formalized

        return True


class ProblemService:
    """Use-cases for reading and filtering problems."""

    def __init__(self, repo: ProblemRepository) -> None:
        self._repo = repo

    def get(self, problem_id: int) -> ProblemRecord | None:
        """Return a problem by ID (or None)."""
        return self._repo.get_by_id(problem_id)

    def list(
        self, *, criteria: ProblemFilter, limit: int | None = None
    ) -> list[ProblemRecord]:
        """Return problems matching criteria, sorted by ID."""
        problems = [p for p in self._repo.load_all() if criteria.matches(p)]
        problems.sort(key=lambda p: p.id)
        if limit is None:
            return problems
        return problems[: max(limit, 0)]
