# Technical Debt 029: No Logging Framework Usage

**Date:** 2026-01-21
**Status:** Open
**Priority:** P1 (No observability in production)
**Impact:** Debugging production issues is impossible; no audit trail for operations

## Summary

Despite having a `--log-level` flag and `_configure_logging()` function in `cli.py`, no code in the codebase actually emits log messages. This means:

1. The `--log-level` flag is dead code (see BUG-013)
2. Errors are either raised or silently swallowed (see BUG-014)
3. There's no middle ground for informational or debug output
4. Operators have no visibility into what the CLI is doing

## Evidence

Search for logging usage in src/erdos/:

```bash
grep -r "logger\." src/erdos/  # 0 matches
grep -r "logging\." src/erdos/ # Only import in cli.py
```

The only logging-related code is:

```python
# cli.py:83
def _configure_logging(level: str) -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
```

This configures the root logger but nothing ever logs to it.

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
4. Add WARNING logs for handled exceptions (currently `pass` statements)
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

- BUG-013: `--log-level` flag is dead code
- BUG-014: Silent exception swallowing masks errors
- BUG-016: Manifest corruption silently returns None
