"""Tests for application constants module."""

from erdos.core.constants import (
    API_RATE_LIMIT_DELAY,
    DEFAULT_HTTP_TIMEOUT,
    DEFAULT_RAG_LIMIT,
    DEFAULT_SEARCH_LIMIT,
    LAKE_UPDATE_TIMEOUT,
    LEAN_COMPILE_TIMEOUT,
    LEAN_TOOLCHAIN_VERSION,
    LEAN_VERSION_TIMEOUT,
    LLM_COMMAND_TIMEOUT,
    MAX_QUERY_TERMS,
    MAX_TEX_FILE_SIZE,
    MESSAGE_TRUNCATION,
    PREVIEW_LENGTH,
    RETRY_BASE_DELAY,
    RETRY_MAX_ATTEMPTS,
    RETRY_MAX_DELAY,
    RETRYABLE_STATUS_CODES,
    TEXT_PREVIEW_LENGTH,
    TITLE_TRUNCATION,
)


def test_preview_and_truncation_lengths_are_positive_integers():
    """Preview and truncation lengths should be positive integers."""
    assert isinstance(PREVIEW_LENGTH, int)
    assert PREVIEW_LENGTH > 0
    assert TITLE_TRUNCATION > 0
    assert TEXT_PREVIEW_LENGTH > 0
    assert MESSAGE_TRUNCATION > 0


def test_timeouts_are_positive_numbers():
    """All timeouts should be positive numbers."""
    assert isinstance(DEFAULT_HTTP_TIMEOUT, (int, float))
    assert DEFAULT_HTTP_TIMEOUT > 0

    assert isinstance(LEAN_COMPILE_TIMEOUT, int)
    assert LEAN_COMPILE_TIMEOUT > 0

    assert isinstance(LEAN_VERSION_TIMEOUT, int)
    assert LEAN_VERSION_TIMEOUT > 0

    assert isinstance(LAKE_UPDATE_TIMEOUT, int)
    assert LAKE_UPDATE_TIMEOUT > 0

    assert isinstance(LLM_COMMAND_TIMEOUT, int)
    assert LLM_COMMAND_TIMEOUT > 0


def test_rate_limit_delay_is_positive():
    """Rate limit delay should be a positive number."""
    assert isinstance(API_RATE_LIMIT_DELAY, (int, float))
    assert API_RATE_LIMIT_DELAY > 0


def test_size_limits_are_positive():
    """Size limits should be positive integers."""
    assert isinstance(MAX_TEX_FILE_SIZE, int)
    assert MAX_TEX_FILE_SIZE > 0


def test_retry_constants_are_sane():
    """Retry constants should be positive and consistent."""
    assert isinstance(RETRY_MAX_ATTEMPTS, int)
    assert RETRY_MAX_ATTEMPTS > 0
    assert RETRY_BASE_DELAY > 0
    assert RETRY_MAX_DELAY >= RETRY_BASE_DELAY
    assert all(isinstance(code, int) for code in RETRYABLE_STATUS_CODES)


def test_lean_toolchain_version_is_non_empty():
    """Lean toolchain version should be a non-empty string."""
    assert isinstance(LEAN_TOOLCHAIN_VERSION, str)
    assert LEAN_TOOLCHAIN_VERSION.strip()


def test_search_defaults_are_positive_integers():
    """Search defaults should be positive integers."""
    assert DEFAULT_SEARCH_LIMIT > 0
    assert DEFAULT_RAG_LIMIT > 0
    assert MAX_QUERY_TERMS > 0
