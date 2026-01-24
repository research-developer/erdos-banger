"""Unit tests for dashboard state machine (SPEC-034)."""

from __future__ import annotations

from erdos.core.dashboard.state import (
    DashboardState,
    DashboardView,
    apply_key,
    initial_state,
)


class TestDashboardState:
    """Tests for DashboardState dataclass."""

    def test_initial_state(self) -> None:
        """Initial state shows overview with no selection."""
        state = initial_state()
        assert state.view == DashboardView.OVERVIEW
        assert state.selected_problem_id is None
        assert state.selected_attempt_id is None
        assert state.should_quit is False
        assert state.should_refresh is False

    def test_initial_state_with_problem(self) -> None:
        """Initial state can start on a specific problem detail view."""
        state = initial_state(problem_id=42)
        assert state.view == DashboardView.PROBLEM_DETAIL
        assert state.selected_problem_id == 42
        assert state.selected_attempt_id is None


class TestApplyKey:
    """Tests for apply_key state transition function."""

    def test_quit_from_overview(self) -> None:
        """'q' key from overview sets should_quit."""
        state = initial_state()
        new_state = apply_key(state, "q")
        assert new_state.should_quit is True
        # Original state unchanged (immutable)
        assert state.should_quit is False

    def test_refresh_from_overview(self) -> None:
        """'r' key triggers refresh."""
        state = initial_state()
        new_state = apply_key(state, "r")
        assert new_state.should_refresh is True
        assert new_state.view == DashboardView.OVERVIEW

    def test_problem_detail_navigation(self) -> None:
        """'p' key from overview enters problem ID input mode."""
        state = initial_state()
        new_state = apply_key(state, "p")
        assert new_state.view == DashboardView.AWAITING_PROBLEM_ID
        assert new_state.selected_problem_id is None

    def test_enter_problem_id(self) -> None:
        """After 'p', entering a number sets problem_id and shows detail."""
        state = initial_state()
        state = apply_key(state, "p")
        new_state = apply_key(state, "42")
        assert new_state.view == DashboardView.PROBLEM_DETAIL
        assert new_state.selected_problem_id == 42

    def test_back_from_problem_detail(self) -> None:
        """'b' key from problem detail returns to overview."""
        state = initial_state(problem_id=42)
        new_state = apply_key(state, "b")
        assert new_state.view == DashboardView.OVERVIEW
        assert new_state.selected_problem_id is None

    def test_quit_from_problem_detail(self) -> None:
        """'q' key from problem detail quits."""
        state = initial_state(problem_id=42)
        new_state = apply_key(state, "q")
        assert new_state.should_quit is True

    def test_refresh_from_problem_detail(self) -> None:
        """'r' key from problem detail refreshes."""
        state = initial_state(problem_id=42)
        new_state = apply_key(state, "r")
        assert new_state.should_refresh is True
        assert new_state.view == DashboardView.PROBLEM_DETAIL

    def test_attempt_navigation(self) -> None:
        """'a' key from problem detail enters attempt ID input mode."""
        state = initial_state(problem_id=42)
        new_state = apply_key(state, "a")
        assert new_state.view == DashboardView.AWAITING_ATTEMPT_ID
        assert new_state.selected_problem_id == 42

    def test_enter_attempt_id(self) -> None:
        """After 'a', entering an ID shows attempt detail."""
        state = initial_state(problem_id=42)
        state = apply_key(state, "a")
        new_state = apply_key(state, "att_12345")
        assert new_state.view == DashboardView.ATTEMPT_DETAIL
        assert new_state.selected_attempt_id == "att_12345"

    def test_back_from_attempt_detail(self) -> None:
        """'b' key from attempt detail returns to problem detail."""
        state = DashboardState(
            view=DashboardView.ATTEMPT_DETAIL,
            selected_problem_id=42,
            selected_attempt_id="att_12345",
        )
        new_state = apply_key(state, "b")
        assert new_state.view == DashboardView.PROBLEM_DETAIL
        assert new_state.selected_problem_id == 42
        assert new_state.selected_attempt_id is None

    def test_unknown_key_is_ignored(self) -> None:
        """Unknown keys do not change state."""
        state = initial_state()
        new_state = apply_key(state, "x")
        assert new_state == state

    def test_escape_cancels_input_mode(self) -> None:
        """Escape key cancels input mode and returns to previous view."""
        state = initial_state()
        state = apply_key(state, "p")  # Enter problem input mode
        new_state = apply_key(state, "escape")
        assert new_state.view == DashboardView.OVERVIEW

    def test_invalid_problem_id_stays_in_input_mode(self) -> None:
        """Non-numeric input for problem ID stays in input mode."""
        state = initial_state()
        state = apply_key(state, "p")
        new_state = apply_key(state, "abc")
        assert new_state.view == DashboardView.AWAITING_PROBLEM_ID

    def test_refresh_clears_after_transition(self) -> None:
        """should_refresh is cleared after next transition."""
        state = initial_state()
        state = apply_key(state, "r")
        assert state.should_refresh is True
        state = apply_key(state, "q")
        assert state.should_refresh is False
