# Technical Debt 029: Logging Coverage Gaps

**Date:** 2026-01-21
**Status:** Fixed
**Fixed In:** f806edc
**Priority:** P2 (Observability gaps)
**Impact:** Some operational failures are difficult to diagnose without an audit trail

## Summary

The codebase uses Python stdlib logging and supports `erdos --log-level …`. Multiple modules emit logs (debug/warning/exception) for best-effort fallbacks and unexpected errors.

## Evidence

Logging is configured centrally:

- `src/erdos/cli.py` calls `_configure_logging(log_level)` in the Typer callback.

Logging usage exists (not exhaustive):

- `src/erdos/commands/search.py` (`logger.debug`, `logger.exception`)
- `src/erdos/core/ingest/service.py` (`logger.warning` on manifest corruption)
- `src/erdos/core/lean_runner.py` (`logger.debug` on version probe failure)

Remaining gaps:

- Core HTTP clients don’t log request timing/URLs (e.g., `src/erdos/core/crossref_client.py`).
- Long-running operations don’t emit consistent INFO-level “start/finish” logs (useful for batch runs).

## Operations That Should Log

| Operation | Log Level | Purpose |
|-----------|-----------|---------|
| API calls (arXiv, Crossref) | DEBUG | Request/response timing, URLs |
| Index building | INFO | Progress, problem count |
| File operations | DEBUG | Path resolution, fallback chains |
| Exception handling | WARNING | Caught exceptions before fallback |
| Manifest operations | INFO | Load/save events |
| LLM calls | DEBUG | Prompts, responses, timing |

## Acceptance Criteria

1. Add `logger = logging.getLogger(__name__)` to key modules
2. Add DEBUG logs for external calls and timing
3. Add INFO logs for significant operations
4. Add WARNING logs for handled exceptions when an operator should act
5. Verify `--log-level DEBUG` produces useful output
6. CI still passes (`make ci`)

## Recommended Implementation

```python
# In each module that needs logging
import logging

logger = logging.getLogger(__name__)

# Example usage
def fetch_crossref_work(doi: str, ...) -> dict[str, Any]:
    logger.debug("Fetching Crossref metadata for DOI: %s", doi)
    try:
        response = requests.get(url, ...)
        logger.debug("Crossref response: %d bytes in %.2fs", len(response.content), elapsed)
        return response.json()
    except requests.Timeout as e:
        logger.warning("Crossref timeout for DOI %s: %s", doi, e)
        raise
```

## Related

- DEBT-031: Rate limiting ergonomics / defaults
- DEBT-032: HTTP responses not closed with context managers
- DEBT-033: No retry logic for transient network failures
