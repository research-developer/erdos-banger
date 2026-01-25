"""Unit tests for show command logic."""

from erdos.commands.show import get_problem
from erdos.core.models import CLIOutput, ProblemStatus


class TestGetProblem:
    def test_found_problem(self, mock_loader_with_problem) -> None:
        """Returns CLIOutput with problem data when found."""
        result: CLIOutput = get_problem(6, mock_loader_with_problem)

        assert result.success
        assert isinstance(result.data, dict)
        assert result.data["id"] == 6
        assert result.data["status"] == ProblemStatus.OPEN.value
        assert result.command == "erdos show"

    def test_not_found(self, mock_loader_empty) -> None:
        """Returns error CLIOutput when problem not found."""
        result: CLIOutput = get_problem(9999, mock_loader_empty)

        assert not result.success
        assert isinstance(result.error, dict)
        assert result.error["type"] == "NotFoundError"
        assert result.error["code"] == 3
