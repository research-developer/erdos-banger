# Bug: Hardcoded `logs/loop` path breaks outside repo root

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-26
**Fixed:** 2026-01-26
**Commit:** (in-tree)
**GitHub Issue:** [#36](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/issues/36)

## Description

During architectural audit for SPEC-036/037, found that `loop/runner.py` uses a hardcoded relative path `"logs/loop"` which breaks when the CLI is run from a directory other than the repository root.

## Affected Files

### `src/erdos/core/loop/runner.py`

```python
# Before fix
log_path = Path("logs/loop") / f"{generate_run_id()}.jsonl"
```

## Steps to Reproduce

1. `cd /tmp`
2. Run the loop against a real repo/project while setting `ERDOS_REPO_ROOT`:

   ```bash
   ERDOS_REPO_ROOT=/path/to/repo \
     uv run erdos loop run 6 --no-apply --path /path/to/repo/formal/lean --max-iter 1
   ```

3. Before fix: log written to `/tmp/logs/loop/` (relative to cwd) instead of `/path/to/repo/logs/loop/`.

Or:

1. Run tests that invoke loop from test directory
2. Observe logs written to wrong location

## Expected Behavior

When `repo_root` is configured (via `ERDOS_REPO_ROOT`), logs should be written to `<repo_root>/logs/loop/` regardless of current working directory.

## Actual Behavior

Before fix: logs were written relative to `cwd`, even when `repo_root` was configured.

## Root Cause

Hardcoded relative path instead of using `AppConfig.repo_root`.

## Fix

Use `AppConfig.repo_root` to construct absolute path:

```python
from erdos.core.config import AppConfig

# Option 1: From AppConfig
config = AppConfig.from_env()
log_path = config.repo_root / "logs" / "loop" / f"{generate_run_id()}.jsonl"

# Option 2: Accept from caller (already has AppContext)
def run_loop(
    ...,
    log_dir: Path | None = None,
) -> LoopResult:
    if log_dir is None:
        log_dir = Path("logs/loop")  # fallback, but caller should provide
```

## Implementation Notes

- Added `log_dir` parameter to `run_loop(...)` and threaded it through the service layer.
- The CLI passes `repo_root` (from `ERDOS_REPO_ROOT`) so logs land under `<repo_root>/logs/loop/` in typical usage.
- Added regression coverage:
  - `tests/unit/loop/test_runner.py`

## Impact

- **Normal CLI usage:** Works (usually run from repo root)
- **Tests:** May write logs to wrong location
- **CI/CD:** May fail or write logs to unexpected location
- **Embedded usage:** Breaks if host app has different cwd

## Related

- Architecture audit: SPEC-036/037 prep
- Pattern to follow: `src/erdos/core/config.py` (AppConfig.repo_root)
