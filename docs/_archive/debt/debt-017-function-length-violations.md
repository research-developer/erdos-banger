# Technical Debt 017: Function Length Violations

**Date:** 2026-01-19
**Status:** Fixed
**Fixed In:** 94c3788, 9e5de0a, b8d5395, 64d3293, fb85afe, aa0b92e
**Priority:** P1 (Blocks planned work or causes frequent breakage)
**Impact:** Maintainability, testability, readability, bug surface area

## Summary

Several orchestration functions were significantly over-sized (>100 lines) and required complexity suppressions. This increased cognitive load, made testing harder, and increased the surface area for bugs.

## How to Reproduce (AST-based)

Function sizes are measured as `end_lineno - lineno + 1` from the Python AST (includes decorators/docstrings).

```bash
uv run python - <<'PY'
import ast
from pathlib import Path

threshold = 100
violations = []

for path in Path("src/erdos").rglob("*.py"):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.lineno and node.end_lineno:
            length = node.end_lineno - node.lineno + 1
            if length > threshold:
                violations.append((length, path, node.name, node.lineno, node.end_lineno))

violations.sort(reverse=True)
print(f"Functions > {threshold} lines: {len(violations)}")
for length, path, name, start, end in violations:
    print(f"{length:4d} {path}:{start}-{end} {name}")
PY
```

## Current State (2026-01-20)

- No functions exceed 100 lines in `src/erdos/` (verified via the script above).
- Remaining 50–100 line functions are cohesive parsing/subprocess/DDL code (or Typer annotation-heavy callbacks) and are acceptable for their purpose.

Example “long but cohesive” functions (for awareness):

- `src/erdos/core/ingest.py:_fetch_reference_entry` (~96)
- `src/erdos/core/ingest.py:ingest_problem_references` (~92)
- `src/erdos/core/lean_runner.py:check` (~91)
- `src/erdos/commands/list_cmd.py:list_` (~91; Typer annotations dominate)
- `src/erdos/core/ask.py:ask_question` (~73)

## What Changed

- `src/erdos/core/ingest.py`: extracted small helpers and removed duplicated error-entry construction; reduced `_process_single_reference()` below 100 lines (`aa0b92e`).
- `src/erdos/core/ask.py`: extracted helpers to keep orchestration readable/testable (`64d3293`, `fb85afe`).
- `src/erdos/commands/{ingest,search,list_cmd}.py`: moved orchestration into helper functions/value objects (`94c3788`, `9e5de0a`, `b8d5395`).
- Removed `# noqa: PLR091*` suppressions from refactored targets.

## Acceptance Criteria

- [x] No orchestration function exceeds 100 lines (AST verified)
- [x] No `# noqa: PLR091*` suppressions remain
- [x] All tests pass (`make ci`)
- [x] Coverage maintained at 80%+ (`make ci`)

## References

- Robert C. Martin, "Clean Code" Chapter 3: Functions
- "The first rule of functions is that they should be small. The second rule of functions is that they should be smaller than that."
