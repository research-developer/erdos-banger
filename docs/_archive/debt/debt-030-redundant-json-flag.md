# Technical Debt 030: Redundant Dual --json Flag Definition

**Date:** 2026-01-21
**Status:** Fixed
**Fixed In:** ed2c2c8
**Priority:** P3 (DRY violation, user confusion)
**Impact:** Confusing API; maintenance burden when changing flag behavior

## Summary

The `--json` flag was defined both globally in `cli.py` AND locally in every command module. Both `erdos --json show 6` and `erdos show 6 --json` worked, but this duplication:

1. Violated DRY principle
2. Confused users about which form is "correct"
3. Required updating multiple files if flag behavior changes

## Resolution

Implemented **Option A: Global Only** - removed command-level `--json` parameters and `set_json_mode()` calls. Now the `--json` flag must be placed before the command:

```bash
erdos --json show 6         # Works (correct form)
erdos show 6 --json         # No longer works (flag removed)
```

### Changes Made

1. Removed `json_output` parameter from all command functions:
   - `src/erdos/commands/list_cmd.py`
   - `src/erdos/commands/show.py`
   - `src/erdos/commands/refs.py`
   - `src/erdos/commands/search.py`
   - `src/erdos/commands/ask.py`
   - `src/erdos/commands/ingest.py`
   - `src/erdos/commands/lean.py` (3 subcommands: init, check, formalize)

2. Removed `set_json_mode()` calls from all commands

3. Removed `set_json_mode()` function from `src/erdos/commands/presenter.py`

4. Removed `json_output` field from `IngestOptions` dataclass

5. Commands now read JSON mode directly from context: `bool((ctx.obj or {}).get("json"))`

6. Updated all tests to use the global flag form (e.g., `["--json", "show", "6"]`)

## Evidence (Original)

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

### Command-Level Definitions (Removed)

| File | Lines (were) |
|------|-------|
| `src/erdos/commands/list_cmd.py` | 165-171 |
| `src/erdos/commands/show.py` | 106-112 |
| `src/erdos/commands/refs.py` | 90-96 |
| `src/erdos/commands/search.py` | 323-326 |
| `src/erdos/commands/ask.py` | 150 |
| `src/erdos/commands/ingest.py` | 162 |
| `src/erdos/commands/lean.py` | 194-200, 237-243, 289-295 |

## Related

- DRY principle
- Typer global options pattern
