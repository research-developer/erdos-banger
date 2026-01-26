# BUG-046: `erdos lean` Command Crashes with AttributeError

**Date:** 2026-01-26
**Severity:** P2 (Medium - has workaround)
**Status:** Open
**Component:** `erdos lean`, `src/erdos/commands/lean/`

## Summary

The `erdos lean` subcommand group crashes immediately with an AttributeError before any command can execute. This affects all `erdos lean *` commands (check, formalize, init, etc.).

## Reproduction

```bash
$ uv run erdos lean --help
# Crashes with:
AttributeError: 'NoneType' object has no attribute 'isidentifier'

$ uv run erdos lean check formal/lean/Erdos/Problem848.lean
# Same crash
```

## Stack Trace

```
/site-packages/typer/main.py:567 in get_params_convertors_ctx_param_name_from_function
/site-packages/typer/main.py:913 in get_click_param
/site-packages/typer/core.py:454 in __init__
/site-packages/click/core.py:2733 in __init__
/site-packages/click/core.py:2152 in __init__
/site-packages/click/core.py:2900 in _parse_decls

AttributeError: 'NoneType' object has no attribute 'isidentifier'
```

## Root Cause (Suspected)

The error occurs in Typer/Click's parameter parsing. This typically happens when:
1. A command function has a parameter with `None` as the type annotation
2. A parameter name is missing or malformed
3. An `Option()` or `Argument()` decorator has incorrect configuration

The crash happens during app initialization (before any command runs), so it's likely in one of the command definitions in `src/erdos/commands/lean/`.

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

## Impact

- Cannot use `erdos lean check` to verify Lean files
- Cannot use `erdos lean formalize` to generate skeletons
- Must use `lake` directly (requires knowing elan setup)
- Breaks the documented workflow in CLAUDE.md

## Proposed Fix

1. Inspect all command functions in `src/erdos/commands/lean/`:
   - `check.py`
   - `formalize.py`
   - `init.py`
   - Any other subcommands

2. Look for:
   - Parameters with `None` type annotations
   - Missing type annotations on Typer parameters
   - Malformed `Option()` or `Argument()` declarations
   - Parameters with empty string names

3. Add test coverage for `erdos lean --help` to catch regressions

## Acceptance Criteria

- [ ] `uv run erdos lean --help` displays help without crashing
- [ ] `uv run erdos lean check <file>` works
- [ ] `uv run erdos lean formalize <id>` works
- [ ] Test added: `test_lean_help_does_not_crash`

## Test Plan

```python
def test_lean_subcommand_help(strip_ansi):
    """Verify erdos lean --help doesn't crash."""
    result = runner.invoke(app, ["lean", "--help"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "check" in output or "formalize" in output

def test_lean_check_help(strip_ansi):
    """Verify erdos lean check --help works."""
    result = runner.invoke(app, ["lean", "check", "--help"])
    assert result.exit_code == 0
```

## Related

- CLAUDE.md: Documents the workaround
- AGENTS.md: Documents the workaround
- `src/erdos/commands/lean/`: Command implementations
