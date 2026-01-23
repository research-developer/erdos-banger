# DEBT-077: CLI Helper Duplication Across Commands (DRY Violation)

**Priority:** P3 (Minor; clean up when touching nearby code)

**Status:** Open

## Problem

Multiple command modules implement nearly identical private helper functions for:
1. Human-readable output formatting (`_print_human()`)
2. Progress message display (`_show_progress_message()`)
3. Input validation patterns

This violates the **DRY (Don't Repeat Yourself)** principle from Clean Code.

## Evidence

### 1. Duplicated `_print_human()` Implementations

| File | Line | Function |
|------|------|----------|
| `commands/ingest.py` | 42 | `_print_human()` |
| `commands/search.py` | 43 | `_print_human()` |
| `commands/ask.py` | 102 | `_print_human()` |
| `commands/loop.py` | 21 | `_print_human_result()` |
| `commands/show.py` | 33 | `_print_human()` |
| `commands/logs.py` | 43, 76 | `_print_entries_human()`, `_print_summary_human()` |
| `commands/refs.py` | 33 | `_print_human()` |

**Pattern:** Each implements Rich console output with similar structure:
```python
def _print_human(result: SomeData) -> None:
    console.print(Panel(...))
    for item in result.items:
        console.print(f"...")
```

### 2. Duplicated `_show_progress_message()` Implementations

| File | Line | Function |
|------|------|----------|
| `commands/ingest.py` | 140 | `_show_progress_message()` |
| `commands/ask.py` | 72 | `_show_progress_message()` |

**Pattern:** Both check `json_output` flag before printing:
```python
def _show_progress_message(problem_id: int | None, json_output: bool) -> None:
    if not json_output:
        err_console.print(f"[dim]Processing problem #{problem_id}...[/dim]")
```

### 3. Duplicated Validation Helpers

| File | Line | Function |
|------|------|----------|
| `commands/search.py` | 100 | `_validate_mode_flags()` |
| `commands/search.py` | 125 | `_get_search_mode()` |
| `commands/convert.py` | 80 | `_validate_pdf_path()` |
| `commands/ask.py` | 56 | `_validate_question_input()` |

### 4. Contrast with Good Patterns

The codebase already has centralized helpers:
- `commands/presenter.py` → `exit_with_result()`, logging setup
- `commands/lean/common.py` → Shared Lean output formatters
- `commands/research/_common.py` → Shared research error handling

Root commands lack this consolidation.

## Proposed Fix

Create `commands/cli_helpers.py` to consolidate:

```python
# src/erdos/commands/cli_helpers.py
"""Shared CLI helper functions for command modules."""

from rich.console import Console
from rich.panel import Panel

console = Console()
err_console = Console(stderr=True)


def show_progress_message(
    message: str,
    json_output: bool,
    *,
    style: str = "dim",
) -> None:
    """Show progress message (only in human mode)."""
    if not json_output:
        err_console.print(f"[{style}]{message}[/{style}]")


def print_panel(
    title: str,
    content: str,
    *,
    border_style: str = "blue",
) -> None:
    """Print a Rich panel with title and content."""
    console.print(Panel(content, title=title, border_style=border_style))


def validate_required_input(
    value: str | None,
    field_name: str,
) -> str:
    """Validate that a required input is provided."""
    if not value or not value.strip():
        raise typer.BadParameter(f"{field_name} is required")
    return value.strip()
```

### Migration Steps

1. Create `commands/cli_helpers.py` with common patterns
2. Refactor one command at a time (start with `ask.py`)
3. Replace private `_print_human()` with parameterized helper or registry
4. Run `make ci` after each command refactored

## Acceptance Criteria

- [ ] `commands/cli_helpers.py` created with `show_progress_message()`
- [ ] At least 2 commands refactored to use shared helpers
- [ ] No functional changes to CLI behavior
- [ ] `make ci` passes

## Impact

- **Risk:** Low (internal refactoring, no API changes)
- **Effort:** ~150-200 LOC refactoring across 8 files
- **Benefit:** Reduced duplication, easier maintenance, consistent behavior

## References

- Clean Code, Chapter 10: "DRY — Don't Repeat Yourself"
- Existing patterns: `commands/presenter.py`, `commands/lean/common.py`
