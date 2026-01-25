"""Integration tests for show command."""

from pathlib import Path

from erdos.commands.show import get_problem
from erdos.core.problem_loader import ProblemLoader


def test_show_real_problem(sample_problems_yaml: Path) -> None:
    """show returns real problem from YAML file."""
    loader = ProblemLoader(sample_problems_yaml)
    result = get_problem(6, loader)

    assert result.success
    assert isinstance(result.data, dict)
    assert result.data["id"] == 6
    assert "title" in result.data


def test_show_missing_problem(sample_problems_yaml: Path) -> None:
    """show returns NotFound for non-existent problem."""
    loader = ProblemLoader(sample_problems_yaml)
    result = get_problem(99999, loader)

    assert not result.success
    assert isinstance(result.error, dict)
    assert result.error["type"] == "NotFoundError"
