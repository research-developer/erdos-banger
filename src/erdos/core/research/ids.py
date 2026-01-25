"""Record identity helpers (Spec 024)."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime


def utc_now_id_timestamp(now: datetime | None = None) -> str:
    """Generate a UTC timestamp string for record IDs.

    Args:
        now: Optional datetime to use instead of the current UTC time. Must be
            timezone-aware.

    Returns:
        Timestamp formatted as `YYYYMMDDTHHMMSSZ` (UTC, no microseconds).

    Raises:
        ValueError: If `now` is provided but is timezone-naive.
    """
    dt = now if now is not None else datetime.now(UTC)
    if dt.tzinfo is None:
        raise ValueError("now must be timezone-aware (UTC)")
    dt = dt.astimezone(UTC)
    dt = dt.replace(microsecond=0)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def generate_record_id(kind: str, *, now: datetime | None = None) -> str:
    """Generate a stable, filename-safe record id."""
    ts = utc_now_id_timestamp(now)
    rand6 = secrets.token_hex(3)  # 3 bytes -> 6 hex chars
    return f"{kind}_{ts}_{rand6}"
