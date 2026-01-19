# Spec 013: Logging & Evaluation Harness

> Adds structured logging for all CLI commands and a run log query interface for evaluating progress.

**Status:** Pending
**Target:** v1.2
**Prerequisites (SSOT):**
- CLI architecture: `docs/_archive/specs/spec-004-cli-architecture.md`
- Domain models: `docs/_archive/specs/spec-003-domain-models.md`

---

## 0) Scope (v1.2)

### In scope

1. **Structured run logs** for every CLI command
   - JSON Lines format (`.jsonl`) for easy parsing
   - One log entry per command invocation
   - Captures: command, args, timestamp, duration, success/failure, key outputs
2. **Log storage** in `logs/` directory (gitignored)
3. **`erdos logs` command** to query and summarize logs
4. **Problem-level progress tracking** via log aggregation

### Out of scope

- Real-time metrics dashboards
- Log shipping to external services
- Distributed tracing across multiple machines

---

## 1) CLI Interface

### 1.1 Automatic Logging (All Commands)

Every command invocation automatically writes a log entry. No flags required.

**Log location:** `logs/runs.jsonl` (append-only)

**Integration SSOT (v1.2):** Logging is implemented centrally in `erdos.commands.presenter.exit_with_result(...)` so:
- every command that uses the presenter is logged automatically
- commands do not need bespoke logging code

**Captured args:** Use `typer.Context` to capture a sanitized snapshot of `ctx.command_path` and `ctx.params` (no secrets; redact values for keys containing `token`, `key`, or `secret`).

### 1.2 `erdos logs` Command

```text
erdos logs [OPTIONS]
```

#### Options

- `--problem-id, -p INT`: Filter logs by problem ID
- `--command TEXT`: Filter by command name (e.g., `lean check`, `ingest`)
- `--since TEXT`: Filter logs after date (ISO 8601 or relative like `7d`, `1h`)
- `--status TEXT`: Filter by `success` or `failure`
- `--limit, -n INT`: Max entries to return (default: `50`)
- `--summary`: Show aggregated summary instead of individual entries

#### Global flags

- `--json` is a **global** flag (see `src/erdos/cli.py`) and must be supported.
- `--log-level` is a **global** flag (see `src/erdos/cli.py`).

### Examples

```bash
# Show last 10 log entries
uv run erdos logs --limit 10

# Show all Lean check failures for problem 6
uv run erdos logs --problem-id 6 --command "lean check" --status failure

# Summary of activity in the last 7 days
uv run erdos logs --since 7d --summary

# Machine output
uv run erdos --json logs --problem-id 6
```

---

## 2) Log Entry Schema

Each log entry is a single JSON object on one line:

```json
{
  "schema_version": 1,
  "id": "run_20260118_103045_a1b2c3",
  "timestamp": "2026-01-18T10:30:45.123Z",
  "command": "erdos lean check",
  "args": {
    "file": "Erdos/Problem006.lean"
  },
  "problem_id": 6,
  "duration_ms": 1234,
  "success": true,
  "result": {
    "errors": [],
    "warnings": 0,
    "has_sorry": true
  },
  "context": {
    "git_commit": "abc123",
    "lean_version": "4.12.0"
  }
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | int | Always `1` for this spec |
| `id` | string | Unique run ID: `run_{timestamp}_{random}` |
| `timestamp` | string | ISO 8601 with milliseconds |
| `command` | string | Full command name (e.g., `erdos lean check`) |
| `args` | object | Command arguments (sanitized, no secrets) |
| `duration_ms` | int | Execution time in milliseconds |
| `success` | bool | Whether command succeeded |

**Command string SSOT:** `entry.command` must equal the `CLIOutput.command` value produced by the command (so log filtering and JSON output are consistent).

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `problem_id` | int | Problem ID if command relates to a specific problem |
| `result` | object | Command-specific result summary |
| `context` | object | Environment context (git commit, versions) |
| `error` | object | Error details if `success=false` |

---

## 3) Command-Specific Logging

Note: Each log entry includes all required fields from Section 2. The examples below omit common fields (`schema_version`, `id`, `timestamp`, `duration_ms`) for brevity and show the command-specific fields only.

### 3.1 `erdos show`

```json
{
  "command": "erdos show",
  "success": true,
  "args": {"problem_id": 6},
  "problem_id": 6,
  "result": {"status": "open", "has_prize": true}
}
```

### 3.2 `erdos search`

```json
{
  "command": "erdos search",
  "success": true,
  "args": {"query": "prime arithmetic progression", "limit": 10},
  "result": {"hit_count": 5, "top_problem_ids": [4, 6, 123]}
}
```

### 3.3 `erdos lean check`

```json
{
  "command": "erdos lean check",
  "success": false,
  "args": {"file": "Erdos/Problem006.lean"},
  "problem_id": 6,
  "result": {
    "success": false,
    "error_count": 2,
    "has_sorry": true,
    "errors": [
      {"line": 15, "message": "type mismatch"}
    ]
  },
  "context": {"lean_version": "4.12.0"}
}
```

### 3.4 `erdos lean formalize`

```json
{
  "command": "erdos lean formalize",
  "success": true,
  "args": {"problem_id": 6},
  "problem_id": 6,
  "result": {"file_created": "formal/lean/Erdos/Problem006.lean"}
}
```

### 3.5 `erdos ingest` (when implemented)

```json
{
  "command": "erdos ingest",
  "success": true,
  "args": {"problem_id": 6},
  "problem_id": 6,
  "result": {
    "references_processed": 3,
    "arxiv_fetched": 2,
    "crossref_fetched": 1,
    "manifest_path": "literature/manifests/0006.yaml"
  }
}
```

### 3.6 `erdos ask` (when implemented)

```json
{
  "command": "erdos ask",
  "success": true,
  "args": {"problem_id": 6, "question": "What partial results?"},
  "problem_id": 6,
  "result": {
    "sources_retrieved": 5,
    "llm_enabled": true,
    "answer_length": 450
  }
}
```

### 3.7 `erdos loop` (when implemented)

```json
{
  "command": "erdos loop",
  "success": true,
  "args": {"problem_id": 6, "max_iter": 10},
  "problem_id": 6,
  "result": {
    "iterations_completed": 5,
    "final_status": "max_iterations",
    "sorry_count_start": 3,
    "sorry_count_end": 1
  }
}
```

---

## 4) Summary Output Schema

When `--summary` is used:

```json
{
  "schema_version": 1,
  "command": "erdos logs",
  "success": true,
  "data": {
    "period": {"from": "2026-01-11T00:00:00Z", "to": "2026-01-18T23:59:59Z"},
    "total_runs": 47,
    "by_command": {
      "erdos show": {"runs": 15, "success": 15, "failure": 0},
      "erdos lean check": {"runs": 20, "success": 12, "failure": 8},
      "erdos search": {"runs": 12, "success": 12, "failure": 0}
    },
    "by_problem": {
      "6": {"runs": 10, "last_success": "2026-01-18T10:30:45Z"},
      "123": {"runs": 5, "last_success": null}
    },
    "metrics": {
      "problems_attempted": 2,
      "lean_compiles_passed": 12,
      "lean_compiles_failed": 8
    }
  }
}
```

---

## 5) Implementation

### 5.1 Core Module: `src/erdos/core/run_logger.py`

Responsibilities:

1. Generate unique run IDs
2. Capture timing via context manager
3. Write log entries to `logs/runs.jsonl`
4. Read and filter log entries
5. Compute summaries

```python
# Example API (not prescriptive)
from erdos.core.run_logger import RunLogger

logger = RunLogger()
logger.log(ctx, cli_output)
```

### 5.2 Command Integration

`erdos.commands.presenter.exit_with_result(...)` calls `RunLogger.log(ctx, result)` immediately before raising a non-zero `typer.Exit` (for failures) and after printing output (for successes). This ensures that logs match user-visible results and JSON outputs.

### 5.3 CLI Command: `src/erdos/commands/logs.py`

Follow Spec 004 patterns. Call `RunLogger.query(...)` and format output.

---

## 6) File Layout

```text
logs/
├── runs.jsonl          # Append-only run log (gitignored)
└── .gitkeep            # Ensure directory exists
```

**Repo hygiene:** Add `logs/*.jsonl` to `.gitignore` (Spec 001) to prevent accidental commits.

**Log rotation:** Not in v1.2 scope. For now, users can manually archive/delete old logs.

---

## 7) Verification: This Spec is Testable

### Vertical Slice Test

```bash
# Prepare a local data dir (v1 expects enriched YAML with title/statement)
tmp_data="$(mktemp -d)"
cp tests/fixtures/sample_problems.yaml "$tmp_data/problems_enriched.yaml"
export ERDOS_DATA_PATH="$tmp_data"

# Run a command
uv run erdos show 6

# Verify log was created
uv run erdos --json logs --limit 1 | jq '.data[0].command'
# Should output: "erdos show"

# Run lean check
uv run erdos lean check formal/lean/Erdos/Basic.lean

# Query logs for this problem
uv run erdos logs --problem-id 6 --command "lean check"
```

### Unit Tests

- `tests/unit/test_run_logger.py`
  - Log entry generation with correct schema
  - Timing capture via context manager
  - Query filtering by problem_id, command, since, status

### Integration Tests

- `tests/integration/test_cli_logs.py`
  - Run `erdos show 6`, verify log entry exists
  - Run `erdos --json logs`, verify valid JSON output
  - Run `erdos logs --summary`, verify aggregation

### Acceptance Criteria

```bash
uv run ruff check .
uv run mypy src/
uv run pytest -m "not requires_lean and not requires_network"
```

---

## References

- JSON Lines format: `https://jsonlines.org/`
- Master vision logging section: `docs/specs/master-vision.md` (Section 2)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-18 | Initial spec |
