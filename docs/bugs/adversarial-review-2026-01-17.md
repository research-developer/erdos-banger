# Adversarial Codebase Review - 2026-01-17

> Comprehensive audit of erdos-banger codebase comparing implementations against specs.

---

## Executive Summary

This review covers all specs implemented thus far (spec-003 through spec-006) and identifies:
- **3 spec drift issues** (implementation deviates from spec) - *Updated after verification*
- **9 missing test scenarios**
- **2 inappropriate mock patterns**
- **5 confirmed bugs** (2 P2, 3 P3) - *Reduced from 12 after verification*

**Overall Assessment:** The codebase is well-structured with good test coverage for core paths. Several initial findings were false positives after careful spec comparison. Real issues include dead global flags and missing duration measurement.

**Verification Status:** ✅ All findings verified against specs on 2026-01-17

---

## 1. Spec Drift

### 1.1 [DRIFT-001] ~~Missing `--prize-max` Filter~~ → ENHANCEMENT

**Status:** ⚠️ **RECLASSIFIED** - Not a bug, but useful enhancement
**Original Severity:** P1 (High) → **Now:** P4 (Enhancement)
**Spec:** spec-004-cli-architecture.md, Section 8 (Help Text Quality)
**File:** `src/erdos/commands/list_cmd.py`

**Verification Notes:**
After careful review, spec-004 Section 8 (lines 825-862) only specifies `--prize-min`, NOT `--prize-max`. The original review incorrectly stated the spec required `--prize-max`.

However, spec-005 `ProblemLoader.filter()` method (lines 376-383) already supports `prize_max` parameter. Adding `--prize-max` to the CLI would be a useful enhancement since the loader already supports it.

**Resolution:** Implemented as enhancement (not bug fix)

---

### 1.2 [DRIFT-002] Dead Global Flags (spec-004)

**Status:** ✅ **CONFIRMED** - Partially fixed
**Severity:** P2 (Medium)
**Spec:** spec-004-cli-architecture.md, Section 2 (Application Structure)
**File:** `src/erdos/cli.py`

The following global flags are defined but never used:

| Flag | Spec Requirement | Current State | Resolution |
|------|------------------|---------------|------------|
| `--config` / `-c` | "Path to config file" | Stored but never read | Deferred to v1.1 |
| `--no-network` | "Disable all network requests" | Stored but no code checks it | Reserved for future network commands |
| `--log-level` | "Logging level" | Stored but logging never configured | **FIXED** |

**Evidence:**
```python
# cli.py:79-88
ctx.obj.update({
    "json": json_output,
    "no_network": no_network,  # No network code exists yet
    "config": config,          # Deferred to v1.1
    "log_level": log_level,    # NOW CONFIGURED
})
```

**Impact:** `--log-level` now works. Other flags documented as reserved for v1.1.

**Fix Applied:** Implemented logging configuration for `--log-level`.

---

### 1.3 [DRIFT-003] Config File Support Not Implemented (spec-005)

**Severity:** P2 (Medium)
**Spec:** spec-005-problem-loader.md, Section 4 (Configuration)
**File:** N/A (missing implementation)

The spec defines config file support:
```yaml
# erdos.yaml (config file)
data:
  problems_path: "data/erdosproblems/data/problems.yaml"
  cache_parsed: true
```

**Actual Implementation:** No config file parsing exists. The `--config` flag is accepted but ignored.

**Impact:** Configuration documented in spec cannot be used.

**Fix:** Implement YAML config loading or defer to v1.1 with explicit documentation.

---

### 1.4 [DRIFT-004] `duration_ms` Never Populated (spec-003, spec-004)

**Severity:** P3 (Low)
**Spec:** spec-003-domain-models.md (CLIOutput), spec-004 (JSON Output Schema)
**Files:** All command files

The `CLIOutput` model has a `duration_ms` field specified in the JSON schema:
```json
{
  "duration_ms": 42
}
```

**Actual Implementation:** Commands never measure or populate this field. All JSON output has `duration_ms: null`.

**Impact:** Performance metrics unavailable for automation consumers.

**Fix:** Add timing measurement in command handlers.

---

### 1.5 [DRIFT-005] Search Command Has Undocumented `--build-index` Flag

**Severity:** P4 (Enhancement)
**Spec:** spec-006-search-index.md, Section 5 (CLI Integration)
**File:** `src/erdos/commands/search.py`

The implementation adds `--build-index` flag not in the spec. This is actually a useful enhancement but represents spec drift.

**Impact:** None (positive feature addition).

**Action:** Update spec-006 to document `--build-index` flag.

---

## 2. Missing Tests

### 2.1 [TEST-001] No E2E Tests for `erdos list` Command

**Priority:** P2
**Current State:** Only integration tests exist (CliRunner in-process).
**Gap:** No subprocess-based E2E test validating real CLI invocation.

**Missing Tests:**
- `test_list_human_output()` - table formatting
- `test_list_json_output()` - JSON structure
- `test_list_with_filters()` - filter combinations
- `test_list_exit_codes()` - error scenarios

---

### 2.2 [TEST-002] No E2E Tests for `erdos refs` Command

**Priority:** P2
**Current State:** Only integration tests exist.
**Gap:** No subprocess-based E2E test.

**Missing Tests:**
- `test_refs_human_output()` - table formatting
- `test_refs_json_output()` - JSON structure
- `test_refs_not_found()` - exit code 3

---

### 2.3 [TEST-003] No E2E Tests for `erdos search` Command

**Priority:** P2
**Current State:** Only integration tests exist.
**Gap:** No subprocess-based E2E test.

**Missing Tests:**
- `test_search_with_fts_index()` - BM25 ranking
- `test_search_fallback_to_basic()` - no index scenario
- `test_search_build_index_flag()` - `--build-index` behavior
- `test_search_fts5_syntax()` - phrase, prefix, NOT queries

---

### 2.4 [TEST-004] No Unit Tests for `list_cmd.list_problems()` Function

**Priority:** P3
**File:** `src/erdos/commands/list_cmd.py:53`
**Gap:** Core logic function has no dedicated unit tests.

**Missing Tests:**
- Filter by status
- Filter by prize_min
- Filter by tags (multiple)
- Combined filters
- Error handling

---

### 2.5 [TEST-005] No Unit Tests for `refs.get_refs()` Function

**Priority:** P3
**File:** `src/erdos/commands/refs.py:53`
**Gap:** Core logic function has no dedicated unit tests.

**Missing Tests:**
- Problem with references
- Problem with no references
- Problem not found

---

### 2.6 [TEST-006] Insufficient Fixture Diversity

**Priority:** P3
**File:** `tests/fixtures/sample_problems.yaml`
**Current State:** Only 3 problems (id: 1, 6, 42).

**Missing Coverage:**
- Problem with `partially_solved` status
- Problem with `disproved` status
- Problem with multiple references
- Problem with `formalized: true` but open status
- Problem with very long statement (truncation testing)
- Problem with Unicode in title/statement

---

### 2.7 [TEST-007] No Tests for Edge Cases in Search

**Priority:** P3
**Gap:** Missing property-based and edge case tests.

**Missing Tests:**
- Search with special FTS5 characters: `" * - ( )`
- Search with very long queries
- Search with Unicode queries
- Search with SQL injection attempts
- Search result ordering stability

---

### 2.8 [TEST-008] Missing `--help` Output Validation

**Priority:** P4
**Gap:** No tests verify help text content for commands.

**Missing Tests:**
- `test_list_help_shows_all_options()`
- `test_refs_help_shows_usage()`
- `test_search_help_shows_fts5_syntax()`
- `test_lean_subcommands_help()`

---

### 2.9 [TEST-009] Unused `in_memory_db` Fixture

**Priority:** P4
**File:** `tests/conftest.py:45`
**Current State:** Fixture defined but never used.

```python
@pytest.fixture
def in_memory_db() -> Iterator[sqlite3.Connection]:
    """SQLite in-memory database for search index tests."""
    conn = sqlite3.connect(":memory:")
    # ...
```

**Action:** Either use in search index tests or remove.

---

## 3. Inappropriate Mocks

### 3.1 [MOCK-001] Incomplete `_MockLoader` Interface

**Priority:** P3
**File:** `tests/unit/conftest.py:23`
**Issue:** Mock only implements `get_by_id()`, not full `ProblemLoader` interface.

```python
class _MockLoader:
    def __init__(self, problem: ProblemRecord | None) -> None:
        self._problem = problem

    def get_by_id(self, problem_id: int) -> ProblemRecord | None:
        # Only this method implemented
```

**Missing Methods:**
- `load_all()`
- `filter()`
- `iter_problems()`
- `count()`
- `clear_cache()`
- `yaml_path` property

**Impact:** Cannot use mock for testing commands that call other loader methods.

**Fix:** Extend mock to implement full interface or use `unittest.mock.MagicMock` with spec.

---

### 3.2 [MOCK-002] Class-Level Monkeypatching for LeanRunner

**Priority:** P4
**File:** `tests/integration/test_cli_commands.py:249`
**Issue:** Patching at class level affects all instances.

```python
monkeypatch.setattr(LeanRunner, "check", fake_check_ok)
```

**Risk:** Test execution order dependency if other tests create LeanRunner instances.

**Recommendation:** Use instance-level mocking or dependency injection pattern.

---

## 4. Bugs by Priority

### P1 - High Priority

#### [BUG-P1-001] ~~`--prize-max` Filter Not Implemented~~ → ENHANCEMENT

**Status:** ⚠️ **RECLASSIFIED** - Not a bug (see DRIFT-001)
**File:** `src/erdos/commands/list_cmd.py`

**Verification Notes:**
Spec-004 does NOT define `--prize-max` as required. However, the loader (spec-005) supports it. Implemented as an enhancement.

**Resolution:** Added `--prize-max` option as enhancement (not bug fix).

---

### P2 - Medium Priority

#### [BUG-P2-001] `--config` Flag Does Nothing

**Status:** ⏳ **DEFERRED** to v1.1
**File:** `src/erdos/cli.py:58-64`
**Description:** Config path stored but never loaded.
**User Impact:** Configuration cannot be customized via file.

**Resolution:** Deferred to v1.1. Help text updated to indicate future feature.

---

#### [BUG-P2-002] `--no-network` Flag Does Nothing

**Status:** ⏳ **RESERVED** for future use
**File:** `src/erdos/cli.py:51-56`
**Description:** Flag stored but no network code exists yet.
**User Impact:** None currently - no v1 commands use network.

**Resolution:** Flag reserved for v1.1 network commands (ingest, ask). Help text clarified.

---

#### [BUG-P2-003] `--log-level` Flag Does Nothing

**Status:** ✅ **CONFIRMED & FIXED**
**File:** `src/erdos/cli.py:66-71`
**Description:** Log level stored but logging never configured.
**User Impact:** Cannot control verbosity.
**Fix Applied:** Implemented logging configuration in CLI callback.

---

#### [BUG-P2-004] ~~`iter_problems()` Re-parses YAML on Every Call~~ → FALSE POSITIVE

**Status:** ⚠️ **FALSE POSITIVE** - Implementation matches spec exactly
**File:** `src/erdos/core/problem_loader.py:214-223`

**Verification Notes:**
After reviewing spec-005 lines 349-358 and the test at lines 600-610, this is **intentional behavior**. The spec explicitly shows `iter_problems()` calling `_load_raw()` directly, and the test asserts "Cache should still be None (didn't call load_all)".

This is a design choice: `iter_problems()` is meant to be independent of the cache for true lazy iteration without populating the cache (useful for memory-constrained scenarios with 1135+ problems).

**Resolution:** No fix needed - working as designed.

---

### P3 - Low Priority

#### [BUG-P3-001] `CLIOutput.duration_ms` Always Null

**Status:** ✅ **CONFIRMED & FIXED**
**Files:** All command files
**Description:** Duration never measured or set.
**User Impact:** Automation cannot measure command performance.
**Fix Applied:** Added timing measurement to all commands.

---

#### [BUG-P3-002] ~~Search Fallback Uses Case-Insensitive Match but FTS Uses Stemming~~ → BY DESIGN

**Status:** ⚠️ **BY DESIGN** - Documented limitation
**File:** `src/erdos/commands/search.py:127-138`

**Verification Notes:**
The code at line 48 explicitly documents this: `"[dim]Using basic substring search (run 'erdos search --build-index' for better results)[/dim]"`. This is intentional fallback behavior when no FTS index exists, not a bug.

**Resolution:** No fix needed - documented and working as designed.

---

#### [BUG-P3-003] No Validation of Status String in List Filter

**Status:** ✅ **CONFIRMED & FIXED**
**File:** `src/erdos/commands/list_cmd.py:63`
**Description:** Invalid status string silently becomes `UNKNOWN` via `ProblemStatus.from_string()`.
**User Impact:** Typos in `--status` give unexpected empty results.
**Fix Applied:** Added validation with helpful error message listing valid values.

---

#### [BUG-P3-004] ~~Empty Tags List Not Handled Consistently~~ → FALSE POSITIVE

**Status:** ⚠️ **FALSE POSITIVE** - Code works correctly
**File:** `src/erdos/core/problem_loader.py:172`

**Verification Notes:**
The expression `tags=list(raw.get("tags", []) or [])` correctly handles:
1. `tags` key not present → `[]`
2. `tags: null` in YAML → `[]` (via `or []`)
3. `tags: []` in YAML → `[]`

This is defensive programming that handles all edge cases correctly. The code is slightly verbose but correct.

**Resolution:** No fix needed - working correctly.

---

### P4 - Cosmetic/Enhancement

#### [BUG-P4-001] No Exit Code Documentation in `--help`

**Files:** All command files
**Description:** Exit codes (0, 1, 2, 3, 5, 10) not documented in help text.
**User Impact:** Users must read docs to understand exit codes.
**Fix:** Add exit code section to command docstrings.

---

#### [BUG-P4-002] Rich Table Truncation Untested

**Files:** `src/erdos/commands/list_cmd.py`, `refs.py`
**Description:** Tables on narrow terminals may truncate unexpectedly.
**User Impact:** Output may be unreadable in constrained terminals.
**Fix:** Add tests with `COLUMNS` env var or use Rich's overflow handling.

---

#### [BUG-P4-003] No Progress Indicator for `--build-index`

**File:** `src/erdos/commands/search.py:220-222`
**Description:** Large datasets may take time; only shows "Building search index...".
**User Impact:** No feedback during index build.
**Fix:** Add Rich progress bar or problem count updates.

---

## 5. Test Coverage Analysis

### Current Coverage by Command

| Command | Unit Tests | Integration Tests | E2E Tests |
|---------|------------|-------------------|-----------|
| `show`  | 2 (get_problem) | 2 | 6 |
| `list`  | 0 | 4 | 0 |
| `refs`  | 0 | 4 | 0 |
| `search`| 26 (SearchIndex) | 7 | 0 |
| `lean`  | 0 | 8 | 0 |

### Recommended Additions

1. Add `tests/e2e/test_cli_list.py` - 6 tests
2. Add `tests/e2e/test_cli_refs.py` - 4 tests
3. Add `tests/e2e/test_cli_search.py` - 8 tests
4. Add `tests/unit/test_list_logic.py` - 6 tests
5. Add `tests/unit/test_refs_logic.py` - 4 tests
6. Expand `tests/fixtures/sample_problems.yaml` to 8-10 problems

---

## 6. Security Considerations

### 6.1 SQL Injection in Search (Low Risk)

**File:** `src/erdos/core/search_index.py:245-294`
**Analysis:** Uses parameterized queries correctly.
```python
cursor = conn.execute(sql, params)  # Safe
```
**Status:** No vulnerability found.

### 6.2 Path Traversal in Loader (Low Risk)

**File:** `src/erdos/core/problem_loader.py`
**Analysis:** Paths come from env vars or defaults, not user input.
**Status:** No vulnerability found, but validate `ERDOS_DATA_PATH` if used in web context.

### 6.3 YAML Safe Loading (Correct)

**File:** `src/erdos/core/problem_loader.py:107`
```python
data = yaml.safe_load(f)  # Safe, not yaml.load()
```
**Status:** Correctly uses safe_load.

---

## 7. Recommendations

### Immediate Actions (Before Next Release)

1. **[P1]** Implement `--prize-max` filter in list command
2. **[P2]** Either implement or remove dead global flags
3. **[TEST]** Add E2E tests for list, refs, search commands

### Short-Term Actions

1. **[P2]** Fix `iter_problems()` to use cache
2. **[P3]** Add duration_ms measurement to commands
3. **[TEST]** Expand test fixtures with more diverse problems
4. **[MOCK]** Extend `_MockLoader` to full interface

### Documentation Updates

1. Update spec-006 to document `--build-index` flag
2. Add note about unimplemented config file support
3. Document exit codes in CLI help text

---

## Appendix: Files Reviewed

| File | Lines | Status |
|------|-------|--------|
| `src/erdos/cli.py` | 99 | Reviewed |
| `src/erdos/commands/list_cmd.py` | 158 | Reviewed |
| `src/erdos/commands/show.py` | 132 | Reviewed |
| `src/erdos/commands/refs.py` | 113 | Reviewed |
| `src/erdos/commands/search.py` | 237 | Reviewed |
| `src/erdos/core/models.py` | 420 | Reviewed |
| `src/erdos/core/problem_loader.py` | 296 | Reviewed |
| `src/erdos/core/search_index.py` | 364 | Reviewed |
| `tests/**/*.py` | ~1200 | Reviewed |
| `docs/specs/spec-003-*.md` | 774 | Compared |
| `docs/specs/spec-004-*.md` | 1032 | Compared |
| `docs/specs/spec-005-*.md` | 700 | Compared |
| `docs/specs/spec-006-*.md` | 892 | Compared |

---

*Review conducted by adversarial analysis on 2026-01-17*
*Codebase commit: 7a2432b*
