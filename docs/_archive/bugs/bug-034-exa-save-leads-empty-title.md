# Bug: Exa to leads conversion crashes on empty title

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-26
**Fixed:** 2026-01-26
**Commit:** 6f9b423

## Description

When using `erdos research exa search --save-leads`, the conversion crashes if an Exa result has an empty title. Pydantic validation fails because `LeadRecord.title` has a minimum length constraint of 1 character.

## Steps to Reproduce

```bash
export EXA_API_KEY="your-key"
uv run erdos research exa search 848 "Erdos Sarkozy squarefree ab+1" --max-results 10 --save-leads
```

## Expected Behavior

Either:
1. Use a fallback title (e.g., "Untitled" or extract from URL/relevance text)
2. Skip leads with empty titles and log a warning
3. Use the first N characters of the relevance text as the title

## Actual Behavior

Crashes with:
```
ValidationError: 1 validation error for LeadRecord
title
  String should have at least 1 character [type=string_too_short, input_value='', input_type=str]
```

## Root Cause

In `src/erdos/commands/research/exa.py:_exa_to_leads()`, the title is taken directly from `ExaSource.title` without checking if it's empty. Many academic PDFs don't have proper title metadata.

## Fix

Implemented a defensive fallback title in `src/erdos/commands/research/exa.py:_exa_to_leads()`:

- Prefer the original title when present.
- Otherwise fall back to (in order): DOI, arXiv ID, URL, a short relevance snippet, or `"Untitled"`.

## Workaround

Run Exa search without `--save-leads` flag:
```bash
uv run erdos research exa search 848 "query" --max-results 10
# Then manually add relevant leads
```

## Related

- Exa API returns empty titles for many PDF sources
- `erdos/core/research/models.py` - LeadRecord validation
