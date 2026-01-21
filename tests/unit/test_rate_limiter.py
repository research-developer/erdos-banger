"""Unit tests for rate limiter module (SPEC-015)."""

from __future__ import annotations

import time

import pytest

from erdos.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_init_default_delay(self) -> None:
        """Test initialization with default delay."""
        limiter = RateLimiter()
        assert limiter.delay_seconds == 3.0

    def test_init_custom_delay(self) -> None:
        """Test initialization with custom delay."""
        limiter = RateLimiter(delay_seconds=1.5)
        assert limiter.delay_seconds == 1.5

    def test_init_zero_delay(self) -> None:
        """Test initialization with zero delay."""
        limiter = RateLimiter(delay_seconds=0.0)
        assert limiter.delay_seconds == 0.0

    def test_init_negative_delay_raises(self) -> None:
        """Test that negative delay raises ValueError."""
        with pytest.raises(ValueError, match="must be non-negative"):
            RateLimiter(delay_seconds=-1.0)

    def test_first_call_no_delay(self) -> None:
        """Test that first call doesn't delay."""
        limiter = RateLimiter(delay_seconds=1.0)
        start = time.monotonic()
        limiter.sleep_if_needed()
        elapsed = time.monotonic() - start
        # First call should be nearly instant
        assert elapsed < 0.1

    def test_subsequent_call_delays(self) -> None:
        """Test that subsequent calls delay appropriately."""
        limiter = RateLimiter(delay_seconds=0.2)  # 200ms for faster test
        limiter.sleep_if_needed()  # First call

        start = time.monotonic()
        limiter.sleep_if_needed()  # Second call
        elapsed = time.monotonic() - start

        # Should delay for at least 200ms (minus time already passed)
        assert elapsed >= 0.15  # Allow some margin

    def test_zero_delay_no_sleep(self) -> None:
        """Test that zero delay doesn't sleep."""
        limiter = RateLimiter(delay_seconds=0.0)
        limiter.sleep_if_needed()

        start = time.monotonic()
        limiter.sleep_if_needed()
        elapsed = time.monotonic() - start

        # Should be nearly instant
        assert elapsed < 0.05

    def test_delay_respects_elapsed_time(self) -> None:
        """Test that delay accounts for time already passed."""
        limiter = RateLimiter(delay_seconds=0.2)
        limiter.sleep_if_needed()

        # Wait longer than delay
        time.sleep(0.25)

        start = time.monotonic()
        limiter.sleep_if_needed()
        elapsed = time.monotonic() - start

        # Should not delay since enough time passed
        assert elapsed < 0.1

    def test_reset_clears_last_call_time(self) -> None:
        """Test that reset clears the last call time."""
        limiter = RateLimiter(delay_seconds=0.2)
        limiter.sleep_if_needed()  # First call

        limiter.reset()

        # After reset, next call should not delay
        start = time.monotonic()
        limiter.sleep_if_needed()
        elapsed = time.monotonic() - start

        assert elapsed < 0.1

    def test_last_call_time_property(self) -> None:
        """Test that last_call_time is updated on sleep_if_needed."""
        limiter = RateLimiter(delay_seconds=0.0)
        assert limiter.last_call_time is None

        limiter.sleep_if_needed()
        assert limiter.last_call_time is not None
        assert limiter.last_call_time > 0

    def test_time_until_next_call(self) -> None:
        """Test time_until_next_call returns correct value."""
        limiter = RateLimiter(delay_seconds=1.0)

        # Before first call, should return 0
        assert limiter.time_until_next_call() == 0.0

        limiter.sleep_if_needed()

        # Immediately after first call, should return ~1.0
        remaining = limiter.time_until_next_call()
        assert 0.9 < remaining <= 1.0

    def test_time_until_next_call_after_wait(self) -> None:
        """Test time_until_next_call decreases over time."""
        limiter = RateLimiter(delay_seconds=0.5)
        limiter.sleep_if_needed()

        time.sleep(0.2)

        remaining = limiter.time_until_next_call()
        assert 0.2 < remaining <= 0.3

    def test_time_until_next_call_expired(self) -> None:
        """Test time_until_next_call returns 0 when delay expired."""
        limiter = RateLimiter(delay_seconds=0.1)
        limiter.sleep_if_needed()

        time.sleep(0.15)

        remaining = limiter.time_until_next_call()
        assert remaining == 0.0
