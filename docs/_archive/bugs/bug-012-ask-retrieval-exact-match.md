# Bug 012: Ask Command Retrieval Uses Exact Phrase Match

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-19
**Fixed:** 2026-01-19
**Commit:** 89a66c2

## Description

The `erdos ask` command wraps the user's question in quotes for FTS5 search, requiring an exact phrase match. This means questions like "What partial results are known?" return zero results even though the index contains relevant content.

## Steps to Reproduce

```bash
# Build the index
uv run erdos search prime --build-index

# Ask a question - returns zero sources
uv run erdos ask 6 "What partial results are known?" --no-llm --json
```

## Expected Behavior

The ask command should return relevant sources (problem statements, notes, ingested content) that match keywords from the question.

## Actual Behavior

```json
{
  "retrieval": {
    "query": "Problem 6: Small primes... Question: What partial results are known?",
    "limit": 5,
    "count": 0,  // <-- Zero sources!
    "used_fts": true
  }
}
```

Meanwhile, a direct search for "primes" works fine:

```bash
uv run erdos search primes  # Returns results
```

## Root Cause

In `src/erdos/core/ask.py:103-106`:

```python
def perform_retrieval(...):
    escaped_question = question.replace('"', '""')
    query = f'"{escaped_question}"'  # <-- Wraps in quotes for exact phrase match
```

This FTS5 query `"What partial results are known?"` requires that exact phrase to exist verbatim in the indexed content.

Additionally, when `SearchIndex.chunk_count() > 0`, the code did not include the problem statement/notes as baseline sources, so a zero-result FTS query produced an empty “Sources” section.

## Impact

- RAG retrieval is effectively broken for real questions
- The prompt always shows "(no sources retrieved)"
- LLM has no context to answer questions intelligently
- Only fallback mode (when index is empty) provides any sources

## Related

- Spec 011: Ask Command
- `src/erdos/core/ask.py:85-116` (perform_retrieval function)
- `src/erdos/core/search_index.py` (SearchIndex.search method)

## Fix

1. Build a safe FTS5 query from tokens of `problem.title + question` and OR together quoted terms (avoids phrase-match brittleness).
2. Always include the problem statement (and notes, if present) as baseline sources, then add retrieved chunks (deduped).
3. Added a regression test asserting that a multi-word question returns at least one source.
