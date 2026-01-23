"""Application-wide constants for erdos-banger CLI toolkit."""

# --- Preview lengths (characters) ---

PREVIEW_LENGTH = 200
"""Default length for text previews and snippets."""

# --- Timeouts (seconds) ---

DEFAULT_HTTP_TIMEOUT = 30.0
"""Default timeout for HTTP requests to arXiv and Crossref APIs."""

LEAN_TOOLCHAIN_VERSION = "v4.12.0"
"""Pinned Lean toolchain / mathlib version tag (keep in sync with formal/lean/lean-toolchain)."""

LLM_COMMAND_TIMEOUT = 300
"""Timeout for external LLM command execution (5 minutes)."""

# --- Rate limiting ---

API_RATE_LIMIT_DELAY = 3.0
"""Delay (seconds) between processing references during ingestion.

Applied per-reference, not per-request. Each reference may make 1-3 requests
(DOI lookup, arXiv metadata, arXiv source download). This delay satisfies
typical API rate limits (Crossref, arXiv recommend ~3s between requests).
"""

# --- Search defaults ---

# --- Size limits ---

MAX_TEX_FILE_SIZE = 2 * 1024 * 1024
"""Maximum LaTeX file size to process (2 MiB)."""

# --- Retry configuration ---

RETRY_MAX_ATTEMPTS = 3
"""Maximum number of attempts for transient network errors."""

RETRY_BASE_DELAY = 2.0
"""Base delay (seconds) between retry attempts. Exponential backoff uses 2^attempt."""

RETRY_MAX_DELAY = 30.0
"""Maximum delay (seconds) between retry attempts."""

RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
"""HTTP status codes that warrant a retry (rate limit + server errors)."""
