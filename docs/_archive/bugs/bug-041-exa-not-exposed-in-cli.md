# BUG-041: INVALIDATED - Exa IS Exposed in CLI

**Date:** 2026-01-26
**Severity:** N/A (False positive)
**Status:** Invalidated
**Commit:** f5557d7
**Component:** CLI

## Summary

~~The Exa client exists but is not exposed in CLI.~~

**WRONG.** Exa IS exposed via:
```bash
erdos research exa search <problem_id> "query" [--save-leads]
```

## What Works

```bash
$ uv run erdos research exa search 848 "Sawhney squarefree" --save-leads
Query: 'Sawhney squarefree'

Sources (5):
  1. [2025] ''
     - URL: https://www.math.columbia.edu/~msawhney/Problem_848.pdf
     - Relevance: ON A ⊆ [N] SUCH THAT ab + 1 IS NEVER SQUAREFREE...

Created 5 lead(s): ['lead_20260126T182322Z_dd76cf', ...]
```

## Real Issue (Minor)

The Exa feature is hard to discover - it's nested under `erdos research exa` rather than being a top-level search option. Consider adding:
- `erdos search --source exa` for consistency with ingest
- Or better docs/examples in help text

## Lesson Learned

Always run `--help` on subcommands before filing bugs.
