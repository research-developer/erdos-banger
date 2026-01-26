# BUG-045: literature/papers/ Not Gitignored

**Date:** 2026-01-26
**Severity:** P3 (Low - repo hygiene)
**Status:** Fixed
**Component:** `.gitignore`

## Summary

Downloaded papers in `literature/papers/` are not gitignored, risking accidental commits of large binary PDFs.

## Evidence

```bash
$ grep literature .gitignore
literature/cache/
literature/extracts/
# Note: literature/papers/ is MISSING
```

But we have:
```
literature/papers/0848/sawhney_problem_848.pdf (351KB)
```

## Expected

Add to `.gitignore`:
```
literature/papers/
```

## Impact

- Large PDFs could be accidentally committed
- Repo bloat
- Potential copyright issues if papers are committed
