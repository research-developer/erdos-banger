"""Unit tests for ProblemService and ProblemFilter."""

from __future__ import annotations

from erdos.core.models import ProblemRecord, ProblemStatus
from erdos.core.repositories import InMemoryProblemRepository
from erdos.services.problem_service import ProblemFilter, ProblemService


def _problem(
    *,
    problem_id: int,
    status: ProblemStatus = ProblemStatus.OPEN,
    prize: int = 0,
    tags: list[str] | None = None,
    formalized: bool = False,
) -> ProblemRecord:
    return ProblemRecord(
        id=problem_id,
        title=f"Problem {problem_id}",
        statement="Statement",
        status=status,
        prize=prize,
        tags=tags or [],
        references=[],
        formalized=formalized,
    )


def test_problem_filter_matches_all_criteria() -> None:
    problem = _problem(problem_id=1, prize=100, tags=["Primes"], formalized=True)
    criteria = ProblemFilter(
        status=ProblemStatus.OPEN,
        prize_min=50,
        prize_max=200,
        tags=["primes"],
        formalized=True,
    )
    assert criteria.matches(problem) is True


def test_problem_filter_tags_empty_is_no_filter() -> None:
    problem = _problem(problem_id=1, tags=["graph theory"])
    assert ProblemFilter(tags=[]).matches(problem) is True


def test_problem_service_list_sorts_and_limits() -> None:
    repo = InMemoryProblemRepository([_problem(problem_id=3), _problem(problem_id=1)])
    service = ProblemService(repo)
    results = service.list(criteria=ProblemFilter(), limit=1)
    assert [p.id for p in results] == [1]


def test_problem_service_list_filters_by_status() -> None:
    repo = InMemoryProblemRepository(
        [
            _problem(problem_id=1, status=ProblemStatus.OPEN),
            _problem(problem_id=2, status=ProblemStatus.PROVED),
        ]
    )
    service = ProblemService(repo)
    results = service.list(criteria=ProblemFilter(status=ProblemStatus.PROVED))
    assert [p.id for p in results] == [2]
