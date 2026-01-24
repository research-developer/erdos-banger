"""Dashboard bounded context (SPEC-034)."""

from erdos.core.dashboard.data import (
    DashboardData,
    ProblemStats,
    aggregate_dashboard_data,
)
from erdos.core.dashboard.render import (
    render_aggregate_stats,
    render_attempt_timeline,
    render_dashboard,
    render_empty_state,
    render_help_bar,
    render_problem_detail,
    render_problem_overview,
)
from erdos.core.dashboard.state import (
    DashboardState,
    DashboardView,
    apply_key,
    initial_state,
)


__all__ = [
    "DashboardData",
    "DashboardState",
    "DashboardView",
    "ProblemStats",
    "aggregate_dashboard_data",
    "apply_key",
    "initial_state",
    "render_aggregate_stats",
    "render_attempt_timeline",
    "render_dashboard",
    "render_empty_state",
    "render_help_bar",
    "render_problem_detail",
    "render_problem_overview",
]
