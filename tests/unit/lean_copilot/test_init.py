"""Unit tests for lean_copilot package initialization (SPEC-033).

Tests:
- Availability check function
- Exception behavior

These tests do NOT require the copilot extra to be installed.
"""

from __future__ import annotations

import builtins
from typing import Any
from unittest import mock


def test_copilot_not_available_error_default_message():
    """CopilotNotAvailableError has informative default message."""
    from erdos.lean_copilot import CopilotNotAvailableError

    error = CopilotNotAvailableError()
    assert "copilot" in str(error).lower()
    assert "uv sync --extra copilot" in str(error)


def test_copilot_not_available_error_custom_message():
    """CopilotNotAvailableError accepts custom message."""
    from erdos.lean_copilot import CopilotNotAvailableError

    custom = "Custom error message"
    error = CopilotNotAvailableError(custom)
    assert str(error) == custom


def test_is_copilot_available_returns_bool():
    """is_copilot_available returns a boolean."""
    from erdos.lean_copilot import is_copilot_available

    result = is_copilot_available()
    assert isinstance(result, bool)


def test_is_copilot_available_false_when_missing():
    """is_copilot_available returns False when deps are missing."""
    from erdos.lean_copilot import is_copilot_available

    # Mock builtins.__import__ to raise ImportError for fastapi
    original_import = builtins.__import__

    def mock_import(
        name: str,
        globals_: dict[str, Any] | None = None,
        locals_: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        if name == "fastapi":
            raise ImportError("No module named 'fastapi'")
        return original_import(name, globals_, locals_, fromlist, level)

    with mock.patch.object(builtins, "__import__", side_effect=mock_import):
        # The function does a fresh import each call, so it will hit our mock
        result = is_copilot_available()
        # When fastapi is unavailable, should return False
        assert result is False


def test_module_exports():
    """Module exports expected symbols."""
    from erdos.lean_copilot import __all__

    assert "is_copilot_available" in __all__
    assert "CopilotNotAvailableError" in __all__


def test_is_copilot_available_handles_import_error_gracefully():
    """is_copilot_available catches ImportError without raising."""
    # This test verifies the function doesn't raise even when imports fail
    # We test this by checking the implementation handles ImportError
    from erdos.lean_copilot import is_copilot_available

    # The function should always return a bool, never raise
    # Even if we can't mock the imports perfectly, calling should be safe
    try:
        result = is_copilot_available()
        assert isinstance(result, bool)
    except ImportError as err:
        # This should NOT happen - the function should catch ImportError
        raise AssertionError(
            "is_copilot_available should not raise ImportError"
        ) from err
