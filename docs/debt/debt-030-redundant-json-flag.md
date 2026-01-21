# Technical Debt 030: Redundant Dual --json Flag Definition

**Date:** 2026-01-21
**Status:** Open
**Priority:** P3 (DRY violation, user confusion)
**Impact:** Confusing API; maintenance burden when changing flag behavior

## Summary

The `--json` flag is defined both globally in `cli.py` AND locally in every command module. Both `erdos --json show 6` and `erdos show 6 --json` work, but this duplication:

1. Violates DRY principle
2. Confuses users about which form is "correct"
3. Requires updating multiple files if flag behavior changes

## Evidence

### Global Definition (`src/erdos/cli.py`)

```python
json_output: Annotated[
    bool,
    typer.Option(
        "--json",
        help="Output as JSON for machine consumption.",
    ),
] = False,
```

### Command-Level Definitions

| File | Lines |
|------|-------|
| `src/erdos/commands/list_cmd.py` | 165-171 |
| `src/erdos/commands/show.py` | 106-112 |
| `src/erdos/commands/refs.py` | 90-96 |
| `src/erdos/commands/search.py` | 323-326 |
| `src/erdos/commands/ask.py` | 150 |
| `src/erdos/commands/ingest.py` | 162 |
| `src/erdos/commands/lean.py` | 194-200, 237-243, 289-295 |

Each command calls `set_json_mode(ctx, json_output)`, which sets `ctx.obj["json"] = True` when `--json` is passed.

## Behavior Notes

```bash
erdos --json show 6         # Works (global sets it)
erdos show 6 --json         # Works (command sets it)
erdos --json show 6 --json  # Works (redundant, same output)
```

Note: `set_json_mode()` is additive (it only sets JSON mode when `--json` is passed). There is no `--no-json` flag in the current CLI.

## Acceptance Criteria

Choose one approach:

### Option A: Global Only (Recommended)

1. Remove `--json` parameter from all command functions
2. Commands read from `ctx.obj["json"]` directly (already do via presenter)
3. Remove `set_json_mode()` calls
4. Update help text to clarify global flag usage

### Option B: Command Only

1. Remove global `--json` parameter from `cli.py`
2. Keep command-level parameters
3. More typing for users but clearer semantics

## Related

- DRY principle
- Typer global options pattern
