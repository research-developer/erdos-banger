# Spec 015: Batch Operations

> Adds batch processing for ingest and formalize commands to scale across multiple problems.

**Status:** Pending
**Target:** v1.3
**Prerequisites (SSOT):**
- Ingest command: `docs/specs/spec-010-ingest-command.md`
- Lean integration: `docs/_archive/specs/spec-007-lean-integration.md`
- Logging: `docs/specs/spec-013-logging-evaluation.md`

---

## 0) Scope (v1.3)

### In scope

1. **Batch ingest** for multiple problems with filters
2. **Batch formalize** for multiple problems
3. **Rate limiting** for external API calls
4. **Progress tracking** with resumption support
5. **Parallel execution** where safe (Lean compilation)

### Out of scope

- Distributed processing across machines
- Queue-based job scheduling
- Real-time progress streaming via WebSocket

---

## 1) CLI Interface

### 1.1 `erdos ingest` (Extended)

```text
erdos ingest [PROBLEM_ID] [OPTIONS]
```

When `PROBLEM_ID` is omitted, batch mode is activated.

**Batch Options**

- `--all`: Process all problems
- `--status TEXT`: Filter by status (`open`, `proved`, `disproved`, `partially_solved`, `unknown`)
- `--prize-min INT`: Minimum prize amount
- `--prize-max INT`: Maximum prize amount
- `--tag TEXT`: Filter by tag (can be repeated)
- `--limit INT`: Max problems to process
- `--skip INT`: Skip first N problems (for manual pagination)
- `--resume`: Resume from last incomplete batch run
- `--dry-run`: Show what would be processed without doing it
- `--no-network`: Do not make external API calls (ingest uses local/cache only; error if required)

**Rate Limiting Options**

- `--delay FLOAT`: Seconds between API calls (default: `3.0`)
- `--max-concurrent INT`: Max parallel operations (v1.3: ingest enforces `1`; values >1 are rejected)

### 1.2 `erdos lean formalize` (Extended)

```text
erdos lean formalize [PROBLEM_ID] [OPTIONS]
```

When `PROBLEM_ID` is omitted, batch mode is activated.

**Batch Options**

- `--all`: Process all problems
- `--status TEXT`: Filter by status
- `--tag TEXT`: Filter by tag
- `--limit INT`: Max problems to process
- `--skip-existing`: Skip problems that already have Lean files
- `--resume`: Resume from last incomplete batch run
- `--dry-run`: Show what would be processed
- `--max-concurrent INT`: Max parallel Lean compilations (default: `4`)

### Examples

```bash
# Ingest all open problems with prizes
uv run erdos ingest --status open --prize-min 1

# Ingest problems tagged "number theory", limit to 10
uv run erdos ingest --tag "number theory" --limit 10

# Dry run to see what would be processed
uv run erdos ingest --status open --dry-run

# Resume interrupted batch
uv run erdos ingest --status open --resume

# Formalize all open problems, skip existing files
uv run erdos lean formalize --status open --skip-existing

# Formalize with parallel Lean compilation
uv run erdos lean formalize --all --max-concurrent 8
```

**Global flags**

- `--json` is a **global** flag (see `src/erdos/cli.py`) and must be supported.
- `--log-level` is a **global** flag (see `src/erdos/cli.py`).

---

## 2) Batch State Tracking

### State File

Batch operations write state to a per-run file:

- `logs/batches/{batch_id}.json` (append/overwrite as the run progresses)
- `logs/batches/latest.json` (pointer to the most recent batch run for `--resume`)

Example state (`logs/batches/{batch_id}.json`):

```json
{
  "schema_version": 1,
  "batch_id": "batch_20260118_103045",
  "command": "erdos ingest",
  "filters": {
    "status": "open",
    "prize_min": 1
  },
  "started_at": "2026-01-18T10:30:45Z",
  "problem_ids": [4, 6, 67, 123, 148, 295],
  "completed": [4, 6, 67],
  "failed": [],
  "pending": [123, 148, 295],
  "last_updated": "2026-01-18T10:35:12Z"
}
```

### Resume Behavior

When `--resume` is passed:
1. Load `logs/batches/latest.json`, then load the referenced `{batch_id}.json`
2. Verify the saved `command` and `filters` match the current invocation (otherwise usage error)
2. Skip problems in `completed` list
3. Retry problems in `failed` list
4. Continue with `pending` list

---

## 3) Rate Limiting

### Default Delays

This spec uses a single `--delay` option (default `3.0`) applied to all external API calls. This is conservative for Crossref and aligned with arXiv politeness guidance.

### Implementation

```python
from erdos.core.rate_limiter import RateLimiter

def run(problem_ids: list[int]) -> None:
    limiter = RateLimiter(delay_seconds=3.0)
    for problem_id in problem_ids:
        limiter.sleep_if_needed()
        ingest_problem(problem_id)
```

---

## 4) Progress Output

### Human Mode

```text
Batch ingest: 6 problems (status=open, prize_min=1)
[1/6] Problem 4... ✓ (3 refs, 2 arxiv)
[2/6] Problem 6... ✓ (2 refs, 1 arxiv)
[3/6] Problem 67... ✗ (network timeout)
[4/6] Problem 123... ✓ (1 ref, 1 crossref)
[5/6] Problem 148... ⏳ (in progress)
...
Completed: 5/6 (1 failed)
Failed: [67]
```

### JSON Mode

```json
{
  "schema_version": 1,
  "command": "erdos ingest",
  "success": true,
  "data": {
    "batch_id": "batch_20260118_103045",
    "mode": "batch",
    "filters": {"status": "open", "prize_min": 1},
    "total": 6,
    "completed": 5,
    "failed": 1,
    "failed_ids": [67]
  },
  "duration_ms": 45200
}
```

---

## 5) Parallel Execution

### Safe for Parallelization

- **Lean compilation**: Independent per file, CPU-bound
- **Index building**: After all ingests complete

### Not Safe (Must Be Sequential)

- **API calls**: Rate limiting required
- **SQLite writes**: Single writer constraint

### Implementation

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def batch_formalize(problem_ids: list[int], max_concurrent: int):
    with ThreadPoolExecutor(max_workers=max_concurrent) as pool:
        futures = {pool.submit(run_lean_formalize, pid): pid for pid in problem_ids}
        results = []
        for fut in as_completed(futures):
            results.append(fut.result())
        return results
```

---

## 6) Implementation

### 6.1 New Module: `src/erdos/core/batch.py`

Responsibilities:

1. Filter problems by criteria
2. Track batch state
3. Handle resume logic
4. Rate limiting
5. Progress reporting

### 6.2 New Module: `src/erdos/core/rate_limiter.py`

Simple synchronous rate limiter with configurable delay.

### 6.3 Extend Commands

- `src/erdos/commands/ingest.py` - Add batch mode
- `src/erdos/commands/lean.py` - Add batch formalize

---

## 7) Verification: This Spec is Testable

### Vertical Slice Test

```bash
# Prepare a local data dir (v1 expects enriched YAML with title/statement)
tmp_data="$(mktemp -d)"
cp tests/fixtures/sample_problems.yaml "$tmp_data/problems_enriched.yaml"
export ERDOS_DATA_PATH="$tmp_data"

# Dry run batch ingest
uv run erdos ingest --status open --limit 3 --dry-run
# Should list 3 problem IDs without making API calls

# Batch formalize with fixtures
uv run erdos lean formalize --limit 2 --skip-existing

# Check batch state was created
cat logs/batch_state.json | jq '.completed'
```

### Unit Tests

- `tests/unit/test_batch.py`
  - Problem filtering by status, prize, tags
  - Batch state serialization/deserialization
  - Resume logic skips completed problems
- `tests/unit/test_rate_limiter.py`
  - Delay enforcement between calls

### Integration Tests

- `tests/integration/test_batch_operations.py`
  - Batch ingest with `--no-network` (ingest option; not a global flag) and fixtures
  - Batch formalize creates multiple Lean files
  - `--resume` continues from state file
  - `--dry-run` doesn't modify anything

### Acceptance Criteria

```bash
uv run ruff check .
uv run mypy src/
uv run pytest -m "not requires_lean and not requires_network"
```

---

## 8) Error Handling

### Partial Failure

- Batch continues on individual problem failure
- Failed problems recorded in state file
- Exit code reflects overall success (0 only if all succeeded; nonzero if any failed)

### Network Interruption

- State file updated after each problem
- `--resume` picks up from last successful problem

### Ctrl+C Handling

- Graceful shutdown: finish current problem, save state
- Second Ctrl+C: immediate exit

---

## References

- Master vision batch mode: `docs/specs/master-vision.md` (Section 6)
- arXiv API politeness: `https://info.arxiv.org/help/api/user-manual.html`

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-18 | Initial spec |
