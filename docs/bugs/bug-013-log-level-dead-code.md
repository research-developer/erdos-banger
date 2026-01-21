# Bug: `--log-level` flag is defined but never used (Dead Code)

**Priority:** P2
**Status:** Open
**Found:** 2026-01-21
**Fixed:** (pending)
**Commit:** (pending)

## Description

The global `--log-level` flag is defined in `cli.py` and stored in the Typer context, but no command ever reads this value after the initial `_configure_logging()` call at startup. The flag gives users the illusion of log level control but provides no runtime capability for commands to adjust their verbosity.

## Steps to Reproduce

1. Run `erdos --log-level DEBUG show 6`
2. Observe that no debug output appears
3. Search codebase for any command reading `ctx.obj["log_level"]`: 0 matches

## Expected Behavior

Either:
- Log level should affect command output verbosity, OR
- The flag should be removed if not needed

## Actual Behavior

- Flag is defined at `cli.py:69-75`
- Value is stored at `cli.py:90`: `ctx.obj["log_level"] = log_level`
- `_configure_logging()` is called once at startup (line 83)
- No command ever reads `ctx.obj["log_level"]`
- The stored value is never used

## Root Cause

The logging configuration happens at CLI startup, but no commands emit logs. The flag was likely added for future extensibility but never wired through.

## Fix Options

1. **Remove the flag** - If dynamic logging isn't needed, remove the dead code
2. **Wire it through** - Add actual logging calls to key operations (API calls, index building, file operations)

## Related

- DEBT-026: No logging framework usage in codebase
- BUG-005: Dead global flags (previously fixed `--config`, `--no-network`)
