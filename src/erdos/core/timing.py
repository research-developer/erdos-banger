"""Timing utilities for CLI commands."""

import time
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def measure_time_ms() -> Iterator[list[int]]:
    """Context manager that measures elapsed time in milliseconds.

    Yields a single-element list containing the duration in milliseconds.
    The duration is computed when the context exits.

    Example:
        >>> with measure_time_ms() as duration:
        ...     # do work
        ...     pass
        >>> print(f"Took {duration[0]}ms")

    Yields:
        A single-element list [0] that will be updated with duration_ms on exit.
    """
    result = [0]  # Mutable container to return duration
    start_time = time.perf_counter()
    try:
        yield result
    finally:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        result[0] = duration_ms
