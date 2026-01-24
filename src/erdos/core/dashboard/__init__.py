"""Dashboard bounded context (SPEC-034)."""

from erdos.core.dashboard.data import (
    DashboardData,
    ProblemStats,
    aggregate_dashboard_data,
)


__all__ = [
    "DashboardData",
    "ProblemStats",
    "aggregate_dashboard_data",
]
