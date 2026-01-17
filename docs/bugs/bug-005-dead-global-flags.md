# Bug: Dead Global Flags (`--config`, `--no-network`)

**Priority:** P2
**Status:** Open
**Found:** 2026-01-17

## Description

The CLI accepts global flags that do not currently affect behavior:
- `--config` / `-c` (config file path)
- `--no-network` (disable network)

This is user-visible drift from Spec 004 (and Spec 005 config section), and it creates misleading UX.

## Steps to Reproduce

1. Run any command with the flags, e.g.:
   - `uv run erdos --config ./erdos.yaml list`
   - `uv run erdos --no-network search prime`
2. Observe behavior is unchanged.

## Expected Behavior

Either:
- The flags are implemented and enforced, or
- The flags are removed from the CLI (and specs) until implemented.

## Actual Behavior

Flags are parsed and stored but not used by core components.

## Root Cause

`src/erdos/cli.py` stores these values in `ctx.obj`, but no code consumes them yet. Spec 005 also defines a YAML config structure that is not implemented.

## Fix

Pick one:
1. **Implement config + enforcement (v1):**
   - Parse `erdos.yaml` and wire config into `ProblemLoader.from_default()` and `SearchIndex.from_default()`.
   - Ensure `--no-network` is checked by any command that can hit the network (future specs).
2. **Defer cleanly (v1):**
   - Remove flags from CLI and specs until a network/config feature ships.

## Related

- `src/erdos/cli.py`
- `docs/specs/spec-004-cli-architecture.md`
- `docs/specs/spec-005-problem-loader.md`

