# BUG-046: INVALIDATED - `erdos lean` Does Not Crash

**Date:** 2026-01-26
**Severity:** N/A (False positive)
**Status:** Invalidated
**Commit:** 1ed768b
**Component:** `erdos lean`, `src/erdos/commands/lean/`

## Summary

Unable to reproduce: `erdos lean --help` renders normally, and `erdos lean check` fails gracefully when `lake` is not available on `PATH`.

## Evidence

```bash
uv run erdos lean --help  # renders help (no crash)
uv run erdos --json lean check formal/lean/Erdos/Problem848.lean  # LeanRunnerError: lake not found on PATH
```

## Workaround

Use `lake` directly instead of the CLI wrapper:

```bash
# Source elan environment and use lake directly
source ~/.elan/env && lake build Erdos.Problem848

# Or use full path
~/.elan/bin/lake build Erdos.Problem848

# From formal/lean directory
cd formal/lean && source ~/.elan/env && lake build
```

This workaround is documented in CLAUDE.md and AGENTS.md.

## Real Issue (DX)

When Lean is installed via elan, `lake` may not be on `PATH` unless you source `~/.elan/env`. This is now documented.

## Related

- `AGENTS.md` / `CLAUDE.md`: elan `lake` PATH notes
