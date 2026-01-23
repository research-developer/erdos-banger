"""Time helpers for research workspace (Spec 023/024)."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now_iso_z(now: datetime | None = None) -> str:
    """Return a UTC timestamp in ISO 8601 format with Z suffix (no microseconds)."""
    dt = now if now is not None else datetime.now(UTC)
    dt = dt.replace(microsecond=0)
    # datetime.isoformat() uses "+00:00" for UTC; normalize to "Z"
    return dt.isoformat().replace("+00:00", "Z")
