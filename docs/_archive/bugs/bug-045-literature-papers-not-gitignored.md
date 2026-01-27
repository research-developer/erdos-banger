# BUG-045: literature/papers/ Not Gitignored

**Date:** 2026-01-26
**Severity:** P3 (Low - repo hygiene)
**Status:** Fixed
**Commit:** f5557d7
**Component:** `.gitignore`

## Summary

Downloaded papers in `literature/papers/` are not gitignored, risking accidental commits of large binary PDFs.

## Evidence

```bash
$ grep literature .gitignore
literature/cache/
literature/extracts/
literature/papers/
```

This prevents accidentally committing downloaded papers/PDFs.

## Expected

Add to `.gitignore`:
```
literature/papers/
```

## Impact

- Large PDFs could be accidentally committed
- Repo bloat
- Potential copyright issues if papers are committed
