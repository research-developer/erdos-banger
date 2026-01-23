"""Tests for timing utilities."""

import time

import pytest

from erdos.core.timing import measure_time_ms


def test_measure_time_ms_basic():
    """Test that measure_time_ms returns a duration in milliseconds."""
    with measure_time_ms() as duration:
        time.sleep(0.01)  # Sleep for 10ms

    # Duration should be at least 10ms (allowing for timing imprecision)
    assert duration[0] >= 8  # Allow 2ms tolerance


def test_measure_time_ms_zero_time():
    """Test that measure_time_ms works with near-zero elapsed time."""
    with measure_time_ms() as duration:
        pass  # No-op

    # Should be a small non-negative number
    assert isinstance(duration[0], int)
    assert duration[0] >= 0
    assert duration[0] < 500  # Avoid flakiness on busy CI


def test_measure_time_ms_longer_duration():
    """Test that measure_time_ms handles longer durations correctly."""
    with measure_time_ms() as duration:
        time.sleep(0.05)  # Sleep for 50ms

    # Duration should be at least 48ms (allowing for timing imprecision)
    assert duration[0] >= 48


def test_measure_time_ms_mutable_container():
    """Test that the duration list is initially zero and updated on exit."""
    with measure_time_ms() as duration:
        # Initially zero
        assert duration == [0]
        time.sleep(0.01)
        # Still zero during execution
        assert duration == [0]

    # Updated after context exit
    assert duration[0] > 0


def test_measure_time_ms_with_exception():
    """Test that timing still works when an exception is raised."""
    with pytest.raises(ValueError), measure_time_ms() as duration:
        time.sleep(0.01)
        raise ValueError("test error")

    # Duration should still be recorded despite the exception
    assert duration[0] >= 8


def test_measure_time_ms_type():
    """Test that duration is returned as an integer."""
    with measure_time_ms() as duration:
        time.sleep(0.01)

    assert isinstance(duration[0], int)
    # Should not be a float
    assert not isinstance(duration[0], float) or duration[0] == int(duration[0])
