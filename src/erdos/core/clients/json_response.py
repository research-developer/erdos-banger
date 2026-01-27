"""Shared JSON parsing helpers for HTTP clients.

Centralizes the common pattern:
- call `response.json()`
- on JSON decode failure, log a short body snippet for debugging
- re-raise the exception (callers decide how to surface errors)
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import requests

if TYPE_CHECKING:
    import logging


def response_json_or_raise(
    response: requests.Response,
    *,
    url: str,
    service: str,
    logger: logging.Logger,
    snippet_chars: int = 200,
) -> Any:
    """Parse JSON from a requests response with consistent logging on failure."""
    try:
        return response.json()
    except (json.JSONDecodeError, requests.exceptions.JSONDecodeError):
        snippet = response.text[:snippet_chars].replace("\n", "\\n")
        logger.error(
            "%s invalid JSON for %s (status %d): %s",
            service,
            url,
            response.status_code,
            snippet,
        )
        raise
