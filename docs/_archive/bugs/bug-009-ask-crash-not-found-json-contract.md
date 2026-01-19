# Bug 009: `erdos ask` Crashes on Unknown Problem ID + Breaks `--json` Contract

**Priority:** P0 (Critical)
**Status:** Fixed
**Found:** 2026-01-19
**Fixed:** 2026-01-19
**Commit:** 0310d62

## Description

`erdos ask` had multiple contract-breaking behaviors:

1. **Unknown problem ID crashed** due to `assert problem is not None` in `src/erdos/core/ask.py`. Since `ProblemLoader.get_by_id()` returns `None` for unknown IDs, this raised `AssertionError`, produced a traceback (even in `--json` mode), and exited with code `1` instead of `ExitCode.NOT_FOUND (3)`.
2. **Empty stdin question** (`QUESTION="-"` with empty/whitespace input) printed a human error message and exited with code `64`, bypassing `CLIOutput` and violating Spec 011 (must be `ExitCode.USAGE_ERROR (2)` and still emit JSON in `--json` mode).
3. **Empty-index fallback missing**: Spec 011 requires `used_fts=false` and statement/notes sources when the FTS index has zero chunks; the implementation always returned `used_fts=true` with empty sources.

## Steps to Reproduce

```bash
tmp=$(mktemp -d)
mkdir -p "$tmp/data" "$tmp/index"
cp tests/fixtures/sample_problems.yaml "$tmp/data/problems.yaml"

# 1) Unknown problem ID crashes (should be NOT_FOUND + JSON in --json mode)
ERDOS_DATA_PATH="$tmp/data" ERDOS_INDEX_PATH="$tmp/index/erdos.sqlite" \
  uv run erdos ask 9999 test --json --no-llm

# 2) Empty stdin question exits 64 and emits no JSON (should be USAGE_ERROR + JSON)
ERDOS_DATA_PATH="$tmp/data" ERDOS_INDEX_PATH="$tmp/index/erdos.sqlite" \
  bash -c 'echo -n "" | uv run erdos ask 6 - --json --no-llm'

rm -rf "$tmp"
```

## Root Cause

- `src/erdos/core/ask.py` used an `assert` to narrow `problem` to `ProblemRecord`, but `ProblemLoader.get_by_id()` returns `None` when a problem isn’t present.
- `src/erdos/commands/ask.py` used a direct `typer.Exit(64)` for empty stdin input, bypassing the shared presenter/`CLIOutput` error model.
- Retrieval always marked `used_fts=true` without checking whether the index contained any chunks.

## Fix

- `src/erdos/core/ask.py`
  - Handle `problem is None` explicitly and return `CLIOutput.err(..., code=ExitCode.NOT_FOUND)`.
  - Implement empty-index fallback to statement/notes sources and set `retrieval.used_fts=false`.
- `src/erdos/commands/ask.py`
  - Replace `typer.Exit(64)` with a structured `CLIOutput.err(..., code=ExitCode.USAGE_ERROR)` routed through `exit_with_result`.
- `tests/integration/test_cli_ask.py`
  - Strengthen tests to assert correct exit codes and JSON error payloads (prevents regressions/traceback output in `--json` mode).

## Related

- Spec 011: `docs/specs/spec-011-ask-command.md`
- Exit codes: `src/erdos/core/exit_codes.py`
