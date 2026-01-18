# Spec 009: Architecture Cleanup (Presentation Utilities)

> Removes duplicated CLI presentation code and standardizes JSON/human output behavior across commands **without changing** the user-facing CLI surface.

**Status:** Complete
**Target:** v1.1
**Depends on:** Archived Specs 001–008 (especially 002, 003, 004)
**Non-dependencies:** Does not introduce a new `domain/` / `application/` / `infrastructure/` package tree.

---

## 0) Goals and Non-Goals

### Goals

1. Eliminate duplicated `_output()` helpers across `src/erdos/commands/*.py`
2. Keep `--json` behavior consistent:
   - In `--json` mode, `CLIOutput` JSON goes to **stdout only**
   - In `--json` mode, any progress/human text goes to **stderr**
   - In human mode, command output goes to stdout and errors go to stderr
3. Standardize exit behavior:
   - a single helper maps `CLIOutput` failure → `typer.Exit(code=...)`
4. Preserve the existing package structure (`src/erdos/core`, `src/erdos/commands`)

### Non-Goals (explicitly out of scope)

- Splitting `src/erdos/core/models.py` into multiple files
- Moving `CLIOutput` out of `erdos.core.models`
- Adding new user-facing CLI flags
- Refactoring into full Clean Architecture layers (that would be a separate spec)

---

## 1) Current State (Verified)

The current implementation (v1.0) has:

- Five command modules (`list/show/refs/search/lean`) each defining a local `_output()`
- Each local `_output()` repeats the same control flow:
  - inspect `ctx.obj["json"]`
  - `console.print_json(...)` for JSON mode
  - pretty human output for success
  - stderr error formatting for failure

This duplication is high-risk because subtle drift reintroduces regressions like “JSON stdout contamination”.

**How to verify locally:**

```bash
rg -n "def _output\\(" src/erdos/commands
```

---

## 2) Change Summary

### New Module

Create:

- `src/erdos/commands/presenter.py`

It becomes the SSOT for:

- “JSON vs human” output routing
- failure → exit code handling

### Command Refactor

Update all existing commands to:

1. Delete their local `_output()` helper
2. Call the shared presenter helper from the Typer command function

---

## 3) Implementation Details

### 3.1 `presenter.py` API (SSOT)

```python
# src/erdos/commands/presenter.py
from collections.abc import Callable
from typing import Any

import typer
from rich.console import Console

from erdos.core.models import CLIOutput


console = Console()
err_console = Console(stderr=True)

HumanPrinter = Callable[[Any], None]


def _error_details(result: CLIOutput) -> tuple[str, int]:
    error = result.error
    if isinstance(error, dict):
        message = error.get("message", error)
        raw_code = error.get("code", 1)
        try:
            code = int(raw_code)
        except (TypeError, ValueError):
            code = 1
        return str(message), code
    return str(error), 1


def output_result(
    ctx: typer.Context,
    result: CLIOutput,
    *,
    print_human: HumanPrinter | None = None,
) -> None:
    """Render a CLIOutput according to global output settings."""
    json_mode = bool((ctx.obj or {}).get("json", False))

    if json_mode:
        console.print_json(result.model_dump_json())
        return

    if result.success:
        if print_human is None:
            console.print(result.data)
        else:
            print_human(result.data)
        return

    message, _ = _error_details(result)
    err_console.print(f"[red]Error:[/red] {message}")


def exit_with_result(
    ctx: typer.Context,
    result: CLIOutput,
    *,
    print_human: HumanPrinter | None = None,
) -> None:
    """Render output and exit non-zero on failure."""
    output_result(ctx, result, print_human=print_human)

    if not result.success:
        _, code = _error_details(result)
        raise typer.Exit(code=code)
```

**Notes**

- This spec intentionally does **not** change `CLIOutput` (it remains in `erdos.core.models`; see archived Spec 003).
- `CLIOutput` invariants already ensure that on failures `error` is set and contains `{"type","message","code"}`.

### 3.2 Command migration pattern

Each command module keeps its “core logic” function(s) and human printer (as already implemented), but removes `_output()`.

Example pattern (applies to `list_cmd.py`, `show.py`, `refs.py`, `search.py`, `lean.py`):

```python
from erdos.commands.presenter import exit_with_result


@app.command()
def show(ctx: typer.Context, problem_id: int) -> None:
    result = get_problem(problem_id=problem_id, loader=loader)
    exit_with_result(ctx, result, print_human=_print_human)
```

### 3.3 Exit code source of truth

- Keep using `ExitCode` from `src/erdos/core/exit_codes.py` (archived Spec 004 SSOT).
- Do not introduce a second `ExitCode` enum in `commands/`.

---

## 4) Verification: This Spec is Testable

### Unit tests

Create `tests/unit/test_presenter.py`:

- `test_output_result_json_writes_only_to_console`
- `test_output_result_error_writes_only_to_err_console`
- `test_exit_with_result_raises_typer_exit_on_failure`

**Recommended test technique**

- Use `Console(record=True)` to capture output.
- `monkeypatch` `erdos.commands.presenter.console` and `erdos.commands.presenter.err_console`.
- Construct a minimal `typer.Context` and set `ctx.obj = {"json": True/False}`.

### Meta-test: no duplicate `_output()`

Add/extend a meta-test that fails if any command module defines `_output()`:

```python
from pathlib import Path


def test_no_duplicate_output_helpers() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    commands = repo_root / "src" / "erdos" / "commands"
    offenders: list[str] = []
    for py_file in commands.glob("*.py"):
        if py_file.name in {"presenter.py", "__init__.py"}:
            continue
        if "def _output(" in py_file.read_text():
            offenders.append(py_file.name)
    assert not offenders, f"_output() should be removed from: {sorted(offenders)}"
```

### Acceptance criteria

```bash
uv run ruff check src/erdos/commands
uv run mypy src/erdos/commands
uv run pytest -m "not requires_lean and not requires_network"
```

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.2.0 | 2026-01-18 | Rewrite: narrowed scope to presenter extraction and duplicate removal |
