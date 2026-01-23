"""Unit tests for rate limiter module (SPEC-015)."""

from __future__ import annotations

from typing import Any, cast

import pytest

from erdos.core.rate_limiter import RateLimiter


class _FakeClock:
    """Deterministic clock for testing time-based behavior."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def fake_clock(monkeypatch: pytest.MonkeyPatch) -> _FakeClock:
    """Patch erdos.core.rate_limiter.time with a deterministic clock."""
    clock = _FakeClock()
    import erdos.core.rate_limiter as rate_limiter_module

    time_module: Any = cast("Any", rate_limiter_module).time
    monkeypatch.setattr(time_module, "monotonic", clock.monotonic)
    monkeypatch.setattr(time_module, "sleep", clock.sleep)
    return clock


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

    def test_first_call_no_delay(self, fake_clock: _FakeClock) -> None:
        """Test that first call doesn't delay."""
        limiter = RateLimiter(delay_seconds=1.0)
        limiter.sleep_if_needed()
        assert fake_clock.sleeps == []

    def test_subsequent_call_delays(self, fake_clock: _FakeClock) -> None:
        """Test that subsequent calls delay appropriately."""
        limiter = RateLimiter(delay_seconds=0.2)  # 200ms for faster test
        limiter.sleep_if_needed()  # First call

        limiter.sleep_if_needed()  # Second call

        assert len(fake_clock.sleeps) == 1
        assert fake_clock.sleeps[0] == pytest.approx(0.2)

    def test_zero_delay_no_sleep(self, fake_clock: _FakeClock) -> None:
        """Test that zero delay doesn't sleep."""
        limiter = RateLimiter(delay_seconds=0.0)
        limiter.sleep_if_needed()
        limiter.sleep_if_needed()

        assert fake_clock.sleeps == []

    def test_delay_respects_elapsed_time(self, fake_clock: _FakeClock) -> None:
        """Test that delay accounts for time already passed."""
        limiter = RateLimiter(delay_seconds=0.2)
        limiter.sleep_if_needed()

        # Wait longer than delay
        fake_clock.advance(0.25)

        limiter.sleep_if_needed()

        assert fake_clock.sleeps == []

    def test_reset_clears_last_call_time(self, fake_clock: _FakeClock) -> None:
        """Test that reset clears the last call time."""
        limiter = RateLimiter(delay_seconds=0.2)
        limiter.sleep_if_needed()  # First call

        limiter.reset()

        # After reset, next call should not delay
        limiter.sleep_if_needed()

        assert fake_clock.sleeps == []

    def test_last_call_time_property(self, fake_clock: _FakeClock) -> None:
        """Test that last_call_time is updated on sleep_if_needed."""
        limiter = RateLimiter(delay_seconds=0.0)
        assert limiter.last_call_time is None

        limiter.sleep_if_needed()
        assert limiter.last_call_time is not None
        assert limiter.last_call_time >= 0

    def test_time_until_next_call(self, fake_clock: _FakeClock) -> None:
        """Test time_until_next_call returns correct value."""
        limiter = RateLimiter(delay_seconds=1.0)

        # Before first call, should return 0
        assert limiter.time_until_next_call() == 0.0

        limiter.sleep_if_needed()

        # Immediately after first call, should return exactly 1.0 (deterministic clock)
        remaining = limiter.time_until_next_call()
        assert remaining == pytest.approx(1.0)

    def test_time_until_next_call_after_wait(self, fake_clock: _FakeClock) -> None:
        """Test time_until_next_call decreases over time."""
        limiter = RateLimiter(delay_seconds=0.5)
        limiter.sleep_if_needed()

        fake_clock.advance(0.2)

        remaining = limiter.time_until_next_call()
        assert remaining == pytest.approx(0.3)

    def test_time_until_next_call_expired(self, fake_clock: _FakeClock) -> None:
        """Test time_until_next_call returns 0 when delay expired."""
        limiter = RateLimiter(delay_seconds=0.1)
        limiter.sleep_if_needed()

        fake_clock.advance(0.15)

        remaining = limiter.time_until_next_call()
        assert remaining == 0.0
