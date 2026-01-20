"""Application-wide constants for erdos-banger CLI toolkit."""

# --- Preview and truncation lengths (characters) ---

PREVIEW_LENGTH = 200
"""Default length for text previews and snippets."""

MESSAGE_TRUNCATION = 500
"""Maximum length for error messages and debug output."""

TITLE_TRUNCATION = 50
"""Maximum length for title displays."""

TEXT_PREVIEW_LENGTH = 100
"""Length for short text previews in ask command."""

# --- Timeouts (seconds) ---

DEFAULT_HTTP_TIMEOUT = 30.0
"""Default timeout for HTTP requests to arXiv and Crossref APIs."""

LEAN_COMPILE_TIMEOUT = 120
"""Timeout for Lean compilation operations."""

LAKE_UPDATE_TIMEOUT = 600
"""Timeout for lake update operations."""

LLM_COMMAND_TIMEOUT = 300
"""Timeout for external LLM command execution (5 minutes)."""

# --- Rate limiting ---

API_RATE_LIMIT_DELAY = 3.0
"""Delay between API requests to avoid rate limiting."""

# --- Search defaults ---

DEFAULT_SEARCH_LIMIT = 10
"""Default number of search results to return."""

DEFAULT_RAG_LIMIT = 5
"""Default number of RAG context chunks to retrieve."""

MAX_QUERY_TERMS = 25
"""Maximum number of query terms to extract from user questions."""

# --- Size limits ---

MAX_TEX_FILE_SIZE = 2 * 1024 * 1024
"""Maximum LaTeX file size to process (2 MiB)."""
