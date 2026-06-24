"""Integration tests for submodule sync (requires network access).

These tests make live git calls to the teorth/erdosproblems submodule
to verify the sync functionality works correctly with real data.
Use `pytest -m requires_network` to run these tests.
"""

from __future__ import annotations

import pytest

from erdos.core.sync.submodule import (
    check_submodule_staleness,
    get_submodule_commit,
    get_submodule_path,
    load_submodule_problems,
)


MIN_EXPECTED_PROBLEMS = 1000


# =============================================================================
# Tests that work with local submodule (no network required)
# =============================================================================


class TestSubmoduleLocal:
    """Tests that work with local submodule state (no network)."""

    def test_default_path_exists(self) -> None:
        """Default submodule path should exist in the repo."""
        path = get_submodule_path()
        # Path should exist since the repo has the submodule initialized
        assert path.exists(), "Submodule directory not found"

    def test_load_problems_from_real_submodule(self) -> None:
        """Load problems from the actual teorth/erdosproblems submodule."""
        path = get_submodule_path()
        if not path.exists():
            pytest.skip("Submodule not initialized")

        problems = load_submodule_problems(path)

        # The real submodule should have many problems
        assert len(problems) > MIN_EXPECTED_PROBLEMS, (
            f"Expected {MIN_EXPECTED_PROBLEMS}+ problems, got {len(problems)}"
        )

        # Spot check some known problems
        assert 1 in problems
        assert 6 in problems

        # Check data integrity
        p1 = problems[1]
        assert p1.problem_id == 1
        assert p1.status in ("open", "proved", "disproved", "partially resolved")

    def test_get_commit_from_real_submodule(self) -> None:
        """Get commit hash from the actual submodule."""
        path = get_submodule_path()
        if not path.exists():
            pytest.skip("Submodule not initialized")

        commit = get_submodule_commit(path)

        # Should be a valid git commit hash (40 hex chars)
        assert len(commit) == 40
        assert all(c in "0123456789abcdef" for c in commit)


# =============================================================================
# Tests that require network access
# =============================================================================


@pytest.mark.requires_network
class TestSubmoduleNetwork:
    """Tests that require network access to the remote."""

    def test_check_staleness_real_submodule(self) -> None:
        """Check staleness of the real submodule (requires network)."""
        path = get_submodule_path()
        if not path.exists():
            pytest.skip("Submodule not initialized")

        # This will fetch from remote to check staleness
        is_stale = check_submodule_staleness(path)

        # We don't assert a specific value since it depends on local state
        # Just verify it returns a boolean without error
        assert isinstance(is_stale, bool)

    def test_full_sync_workflow(self) -> None:
        """Full sync workflow test (requires network).

        Note: This test doesn't actually update the submodule to avoid
        modifying the repo state during tests. It just verifies the
        check functionality works.
        """
        from erdos.commands.sync.submodule_cmd import sync_submodule

        path = get_submodule_path()
        if not path.exists():
            pytest.skip("Submodule not initialized")

        # Run check-only mode (no actual update)
        result = sync_submodule(check_only=True, submodule_path=path)

        assert result.success is True
        assert result.data is not None
        assert result.data["checked"] is True
        assert isinstance(result.data["stale"], bool)
        assert result.data["current_commit"] is not None
        assert result.data["problems_count"] > MIN_EXPECTED_PROBLEMS
