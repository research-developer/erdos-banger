"""Dashboard UI state machine (SPEC-034).

Pure state machine for dashboard keyboard navigation.
This module contains no I/O and is fully unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable


class DashboardView(str, Enum):
    """Dashboard view states."""

    OVERVIEW = "overview"
    PROBLEM_DETAIL = "problem_detail"
    ATTEMPT_DETAIL = "attempt_detail"
    AWAITING_PROBLEM_ID = "awaiting_problem_id"
    AWAITING_ATTEMPT_ID = "awaiting_attempt_id"


@dataclass(frozen=True)
class DashboardState:
    """Immutable dashboard UI state.

    Attributes:
        view: Current view being displayed.
        selected_problem_id: Problem ID when viewing problem detail.
        selected_attempt_id: Attempt ID when viewing attempt detail.
        should_quit: True if user requested quit.
        should_refresh: True if data refresh is needed.
    """

    view: DashboardView = DashboardView.OVERVIEW
    selected_problem_id: int | None = None
    selected_attempt_id: str | None = None
    should_quit: bool = False
    should_refresh: bool = False


def initial_state(*, problem_id: int | None = None) -> DashboardState:
    """Create the initial dashboard state.

    Args:
        problem_id: If provided, start in problem detail view.

    Returns:
        Initial DashboardState.
    """
    if problem_id is not None:
        return DashboardState(
            view=DashboardView.PROBLEM_DETAIL,
            selected_problem_id=problem_id,
        )
    return DashboardState()


_VIEW_HANDLERS: dict[
    DashboardView,
    Callable[[DashboardState, str], DashboardState],
] = {}  # Populated after handler definitions


def apply_key(state: DashboardState, key: str) -> DashboardState:
    """Apply a key press to the state machine (pure transition function).

    This is a pure function with no I/O. It computes the next state
    based on the current state and the pressed key.

    Args:
        state: Current dashboard state.
        key: Key that was pressed (e.g., "q", "r", "p", "b", "42", "escape").

    Returns:
        New DashboardState after applying the transition.
    """
    # Clear transient flags from previous state
    state = replace(state, should_refresh=False)

    # Handle global keys
    if key == "q":
        return replace(state, should_quit=True)
    if key == "r":
        return replace(state, should_refresh=True)

    # Dispatch to view-specific handler
    handler = _VIEW_HANDLERS.get(state.view)
    if handler is not None:
        return handler(state, key)
    return state


def _handle_overview(state: DashboardState, key: str) -> DashboardState:
    """Handle key press in overview view."""
    if key == "p":
        return replace(state, view=DashboardView.AWAITING_PROBLEM_ID)
    return state


def _handle_problem_detail(state: DashboardState, key: str) -> DashboardState:
    """Handle key press in problem detail view."""
    if key == "b":
        return replace(
            state,
            view=DashboardView.OVERVIEW,
            selected_problem_id=None,
            selected_attempt_id=None,
        )
    if key == "a":
        return replace(state, view=DashboardView.AWAITING_ATTEMPT_ID)
    return state


def _handle_attempt_detail(state: DashboardState, key: str) -> DashboardState:
    """Handle key press in attempt detail view."""
    if key == "b":
        return replace(
            state,
            view=DashboardView.PROBLEM_DETAIL,
            selected_attempt_id=None,
        )
    return state


def _handle_awaiting_problem_id(state: DashboardState, key: str) -> DashboardState:
    """Handle input while awaiting problem ID."""
    if key == "escape":
        return replace(state, view=DashboardView.OVERVIEW)

    # Try to parse as problem ID
    try:
        problem_id = int(key)
        return replace(
            state,
            view=DashboardView.PROBLEM_DETAIL,
            selected_problem_id=problem_id,
        )
    except ValueError:
        # Invalid input, stay in input mode
        return state


def _handle_awaiting_attempt_id(state: DashboardState, key: str) -> DashboardState:
    """Handle input while awaiting attempt ID."""
    if key == "escape":
        return replace(state, view=DashboardView.PROBLEM_DETAIL)

    # Accept any non-empty string as attempt ID
    if key and not key.isspace():
        return replace(
            state,
            view=DashboardView.ATTEMPT_DETAIL,
            selected_attempt_id=key,
        )
    return state


# Populate handler dict now that all handlers are defined
_VIEW_HANDLERS.update(
    {
        DashboardView.OVERVIEW: _handle_overview,
        DashboardView.PROBLEM_DETAIL: _handle_problem_detail,
        DashboardView.ATTEMPT_DETAIL: _handle_attempt_detail,
        DashboardView.AWAITING_PROBLEM_ID: _handle_awaiting_problem_id,
        DashboardView.AWAITING_ATTEMPT_ID: _handle_awaiting_attempt_id,
    }
)
