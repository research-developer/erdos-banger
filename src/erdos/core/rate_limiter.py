"""Rate limiter for external API calls (SPEC-015).

Provides a simple synchronous rate limiter with configurable delay
between calls to avoid overwhelming external APIs.
"""

from __future__ import annotations

import time

from erdos.core.constants import API_RATE_LIMIT_DELAY


class RateLimiter:
    """Simple rate limiter with configurable delay between calls.

    Usage:
        limiter = RateLimiter(delay_seconds=3.0)
        for item in items:
            limiter.sleep_if_needed()
            process(item)
    """

    def __init__(self, delay_seconds: float = API_RATE_LIMIT_DELAY) -> None:
        """Initialize rate limiter.

        Args:
            delay_seconds: Minimum seconds between calls. Defaults to
                API_RATE_LIMIT_DELAY (3.0s).

        Raises:
            ValueError: If delay_seconds is negative.
        """
        if delay_seconds < 0:
            raise ValueError(f"delay_seconds must be non-negative, got {delay_seconds}")
        self._delay_seconds = delay_seconds
        self._last_call_time: float | None = None

    @property
    def delay_seconds(self) -> float:
        """Return the configured delay between calls."""
        return self._delay_seconds

    @property
    def last_call_time(self) -> float | None:
        """Return the timestamp of the last call (monotonic)."""
        return self._last_call_time

    def time_until_next_call(self) -> float:
        """Return seconds until the next call is allowed.

        Returns:
            0.0 if a call can be made immediately, otherwise the remaining
            seconds to wait.
        """
        if self._last_call_time is None:
            return 0.0
        elapsed = time.monotonic() - self._last_call_time
        remaining = self._delay_seconds - elapsed
        return max(0.0, remaining)

    def sleep_if_needed(self) -> None:
        """Sleep if needed to respect rate limit, then mark call time.

        The first call never sleeps. Subsequent calls sleep for the remaining
        time until the delay has passed since the previous call.
        """
        if self._last_call_time is not None:
            remaining = self.time_until_next_call()
            if remaining > 0:
                time.sleep(remaining)
        self._last_call_time = time.monotonic()

    def reset(self) -> None:
        """Reset the rate limiter, allowing the next call immediately."""
        self._last_call_time = None
