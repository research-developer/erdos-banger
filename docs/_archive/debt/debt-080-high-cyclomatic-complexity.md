# DEBT-080: High Cyclomatic Complexity Functions

**Priority:** P3 (Minor; clean up when touching nearby code)

**Status:** Fixed
**Fixed:** 2026-01-23
**Commit:** f1dbe92

## Problem

`radon cc` reported a **D-grade** (≥21) complexity hotspot in Crossref parsing. While C-grade (11–20)
functions remain in the codebase (common in orchestration / parsing boundaries), the D-grade hotspot
was the highest-risk item and was addressed first.

## Evidence

### Radon Complexity Analysis

```bash
$ uv run radon cc src/erdos/ -a -s --min C
```

Top hotspots (score ≥15):

| File:Line | Function | Grade | Score |
|-----------|----------|-------|-------|
| `core/research/synthesis.py:62` | `synthesize_problem` | C | 20 |
| `core/loop/runner.py:191` | `_run_single_iteration` | C | 19 |
| `core/clients/openalex.py:230` | `openalex_to_reference` | C | 18 |
| `core/run_logger.py:305` | `RunLogger.query` | C | 18 |
| `commands/search.py:43` | `_print_human` | C | 16 |
| `core/problem_loader.py:388` | `ProblemLoader.filter` | C | 15 |
| `core/ingest/fetch.py:233` | `_fetch_with_provider` | C | 15 |

Note: additional C-grade blocks exist with scores 11–14 (run the command above for the full list).

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

### 1. `openalex_to_reference` (C, 18) — `openalex.py:230`

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

## Resolution

The only D-grade hotspot (`parse_crossref_work`) was refactored into small helper functions without
changing behavior. After f1dbe92, `radon cc src/erdos/ -a -s --min D` reports **no D-grade blocks**.

## Follow-ups (Optional)

### Short-term (when touching these files)

1. **Extract helper functions** for repeated patterns
2. **Use early returns** to reduce nesting
3. **Consider parse-into-dataclass patterns** for API responses

Consider tackling remaining C-grade hotspots opportunistically when touching nearby code.

## Acceptance Criteria

- [x] No functions with D-grade (≥21) complexity
- [ ] `make ci` passes

## Impact

- **Risk:** Low (internal refactoring)
- **Effort:** ~2-3 hours across multiple files
- **Benefit:** Improved testability, easier debugging, reduced cognitive load

## References

- [Radon documentation](https://radon.readthedocs.io/en/latest/intro.html)
- Clean Code, Chapter 17: "Functions should be small" (≤10 complexity recommended)
- Detection: `uv run radon cc src/erdos/ -a -s --min C`
