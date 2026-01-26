# BUG-042: Exa API Returns Empty Titles

**Date:** 2026-01-26
**Severity:** P2 (Medium - degraded UX)
**Status:** Fixed
**Commit:** 8ba6e32
**Component:** `erdos.core.clients.exa`

## Summary

Exa frequently returns results with empty `title` fields (especially for PDFs), making it hard to identify papers in CLI output and downstream workflows.

## Reproduction

```python
from erdos.core.config import initialize_environment
initialize_environment()
from erdos.core.clients.exa import ExaClient

client = ExaClient()
result = client.search('Erdős squarefree products', max_results=5)

for src in result.sources:
    print(f"Title: '{src.title}'")  # Often empty
    print(f"URL: {src.url}")
```

Output:
```
Title: ''
URL: https://arxiv.org/pdf/1612.05438

Title: ''
URL: https://www.math.columbia.edu/~msawhney/Problem_848.pdf
```

## Root Cause

Either:
1. Exa API doesn't return titles for certain content types (PDFs)
2. Our parsing in `ExaSource.from_api_response()` isn't handling the response correctly
3. We need to request additional fields in the API call

## Impact

- Cannot identify papers without clicking through to URLs
- Poor UX when displaying search results
- Makes programmatic filtering difficult

## Fix

The Exa API behavior remains (titles may be empty), but our client now provides a stable, non-empty fallback:

- `ExaSource.display_title` returns the first available of: `title`, `DOI …`, `arXiv …`, `url`, `"Untitled"`.
- `ExaSource.to_dict()` includes `display_title`, and the `erdos research exa search` human output uses it.
