"""Tests for application constants module."""

from erdos.core.constants import (
    API_RATE_LIMIT_DELAY,
    DEFAULT_HTTP_TIMEOUT,
    DEFAULT_RAG_LIMIT,
    DEFAULT_SEARCH_LIMIT,
    LAKE_UPDATE_TIMEOUT,
    LEAN_COMPILE_TIMEOUT,
    MAX_QUERY_TERMS,
    MAX_TEX_FILE_SIZE,
    MESSAGE_TRUNCATION,
    PREVIEW_LENGTH,
    TEXT_PREVIEW_LENGTH,
    TITLE_TRUNCATION,
)


def test_preview_lengths_are_positive_integers():
    """All preview and truncation lengths should be positive integers."""
    assert isinstance(PREVIEW_LENGTH, int)
    assert PREVIEW_LENGTH > 0

    assert isinstance(MESSAGE_TRUNCATION, int)
    assert MESSAGE_TRUNCATION > 0

    assert isinstance(TITLE_TRUNCATION, int)
    assert TITLE_TRUNCATION > 0

    assert isinstance(TEXT_PREVIEW_LENGTH, int)
    assert TEXT_PREVIEW_LENGTH > 0


def test_timeouts_are_positive_numbers():
    """All timeouts should be positive numbers."""
    assert isinstance(DEFAULT_HTTP_TIMEOUT, (int, float))
    assert DEFAULT_HTTP_TIMEOUT > 0

    assert isinstance(LEAN_COMPILE_TIMEOUT, int)
    assert LEAN_COMPILE_TIMEOUT > 0

    assert isinstance(LAKE_UPDATE_TIMEOUT, int)
    assert LAKE_UPDATE_TIMEOUT > 0


def test_rate_limit_delay_is_positive():
    """Rate limit delay should be a positive number."""
    assert isinstance(API_RATE_LIMIT_DELAY, (int, float))
    assert API_RATE_LIMIT_DELAY > 0


def test_search_limits_are_positive():
    """Search and RAG limits should be positive integers."""
    assert isinstance(DEFAULT_SEARCH_LIMIT, int)
    assert DEFAULT_SEARCH_LIMIT > 0

    assert isinstance(DEFAULT_RAG_LIMIT, int)
    assert DEFAULT_RAG_LIMIT > 0

    assert isinstance(MAX_QUERY_TERMS, int)
    assert MAX_QUERY_TERMS > 0


def test_size_limits_are_positive():
    """Size limits should be positive integers."""
    assert isinstance(MAX_TEX_FILE_SIZE, int)
    assert MAX_TEX_FILE_SIZE > 0


def test_preview_length_relationships():
    """Verify reasonable relationships between lengths."""
    # Title should be shorter than general preview
    assert TITLE_TRUNCATION < PREVIEW_LENGTH

    # Text preview for ask command is shorter than general preview
    assert TEXT_PREVIEW_LENGTH < PREVIEW_LENGTH

    # Message truncation should be longer than preview
    assert MESSAGE_TRUNCATION > PREVIEW_LENGTH


def test_timeout_relationships():
    """Verify reasonable relationships between timeouts."""
    # Lake update takes longer than compilation
    assert LAKE_UPDATE_TIMEOUT > LEAN_COMPILE_TIMEOUT

    # Compile timeout should be longer than HTTP timeout
    assert LEAN_COMPILE_TIMEOUT > DEFAULT_HTTP_TIMEOUT
