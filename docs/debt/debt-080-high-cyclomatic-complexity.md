# DEBT-080: High Cyclomatic Complexity Functions

**Priority:** P3 (Minor; clean up when touching nearby code)

**Status:** Open

## Problem

Seven functions have cyclomatic complexity ≥15 (C grade or worse), exceeding the Clean Code recommendation of ≤10 for maintainable code. One function (`parse_crossref_work`) scores D-grade (21).

## Evidence

### Radon Complexity Analysis

```bash
$ uv run radon cc src/erdos/ -a -s --min C
```

| File:Line | Function | Grade | Score |
|-----------|----------|-------|-------|
| `core/clients/crossref.py:20` | `parse_crossref_work` | **D** | 21 |
| `core/research/synthesis.py:62` | `synthesize_problem` | C | 20 |
| `core/loop/runner.py:191` | `_run_single_iteration` | C | 19 |
| `core/clients/openalex.py:229` | `openalex_to_reference` | C | 18 |
| `core/run_logger.py:309` | `RunLogger.query` | C | 18 |
| `commands/search.py:43` | `_print_human` | C | 16 |
| `core/problem_loader.py:388` | `ProblemLoader.filter` | C | 15 |

### Complexity Grade Definitions

| Grade | Score | Meaning |
|-------|-------|---------|
| A | 1-5 | Low risk, simple |
| B | 6-10 | Low risk, well structured |
| C | 11-20 | Moderate risk, more complex |
| D | 21-30 | High risk, harder to test |
| E | 31-40 | Very high risk |
| F | 41+ | Unmaintainable |

## Root Cause Analysis

### 1. `parse_crossref_work` (D, 21) — `crossref.py:20`

Heavy JSON parsing with many conditional branches:
- Error response check
- Nested dict extraction
- Author list iteration with null checks
- Date parsing with multiple fallbacks
- Venue extraction

**Pattern:** Deeply nested optional field extraction from untyped API responses.

### 2. `openalex_to_reference` (C, 18) — `openalex.py:229`

Similar pattern: API response parsing with many optional fields and type coercion.

### 3. `_run_single_iteration` (C, 19) — `loop/runner.py:191`

State machine with multiple exit paths:
- Success/failure/timeout branches
- Patch validation outcomes
- Verification results
- Error handling

**Pattern:** Complex orchestration with many possible outcomes.

### 4. `synthesize_problem` (C, 20) — `synthesis.py:62`

Aggregates data from multiple sources and formats output:
- Multiple store queries
- Sorting and limiting
- Template building

**Pattern:** Report generation with many formatting branches.

## Proposed Fix

### Short-term (when touching these files)

1. **Extract helper functions** for repeated patterns
2. **Use early returns** to reduce nesting
3. **Consider parse-into-dataclass patterns** for API responses

### `parse_crossref_work` Example Refactor

```python
# Before: Inline extraction
title_list = message.get("title")
if not title_list or not isinstance(title_list, list) or not title_list[0]:
    raise ValueError("Missing required field: title")
title = title_list[0]

# After: Helper function
def _extract_first(data: dict, key: str, required: bool = False) -> str | None:
    """Extract first element from a list field."""
    value = data.get(key)
    if not value or not isinstance(value, list):
        if required:
            raise ValueError(f"Missing required field: {key}")
        return None
    return value[0] if value else None

title = _extract_first(message, "title", required=True)
```

## Acceptance Criteria

- [ ] No functions with D-grade (≥21) complexity
- [ ] High-complexity functions documented with `# complexity: high` comment explaining why
- [ ] `make ci` passes

## Impact

- **Risk:** Low (internal refactoring)
- **Effort:** ~2-3 hours across multiple files
- **Benefit:** Improved testability, easier debugging, reduced cognitive load

## References

- [Radon documentation](https://radon.readthedocs.io/en/latest/intro.html)
- Clean Code, Chapter 17: "Functions should be small" (≤10 complexity recommended)
- Detection: `uv run radon cc src/erdos/ -a -s --min C`
