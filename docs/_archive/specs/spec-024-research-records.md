# Spec 024: Research Records (Leads, Attempts, Hypotheses, Tasks)

> Adds merge-safe, one-record-per-file structured research entities and CRUD commands under `erdos research`.

**Status:** Archived
**Target:** v3.0
**Prerequisites (SSOT):**
- Research workspace: `docs/_archive/specs/spec-023-research-workspace.md`
- Output envelope: `docs/_archive/specs/spec-003-domain-models.md` (`CLIOutput`)
- CLI patterns: `docs/_archive/specs/spec-004-cli-architecture.md`
- Research state design (proposal): `docs/future/research-state-management-v3.md`

---

## 0) Scope (v3.0)

### In scope

1) Define structured record schemas (Pydantic) and on-disk formats (YAML).
2) Store structured entities as **one YAML file per record** to minimize merge conflicts:
   - `leads/lead_*.yaml`
   - `attempts/att_*.yaml`
   - `hypotheses/hyp_*.yaml`
   - `tasks/task_*.yaml`
3) Add CRUD commands:
   - `erdos research lead add/list/update`
   - `erdos research hypothesis add/list/update`
   - `erdos research task add/list/update`
   - `erdos research attempt log/list`
4) Add maintenance commands:
   - `erdos research fmt PROBLEM_ID` (canonical YAML serialization)
   - `erdos research validate PROBLEM_ID` (schema + invariants)
5) All commands support `--json` with stable output schema.

### Out of scope

- Indexing records into SQLite (`index/erdos.sqlite`) → SPEC-025
- Generating/maintaining `SYNTHESIS.md` → SPEC-026
- Writing attempt records automatically from `erdos loop` → SPEC-027

---

## 1) Record Identity + File Naming (authoritative)

### ID format

All record IDs are generated as:

```text
{kind}_{YYYYMMDDTHHMMSSZ}_{rand6}
```

Where:
- `{kind}` is one of: `lead`, `att`, `hyp`, `task`
- `{rand6}` is 6 lowercase hex chars (3 bytes) from a cryptographically secure RNG

Example:
`lead_20260123T000501Z_a1b2c3`

### File naming

The filename is `{id}.yaml` under the appropriate folder.

Example:
`research/problems/0006/leads/lead_20260123T000501Z_a1b2c3.yaml`

---

## 2) Data Schemas (YAML)

All YAML records must include:
- `schema_version: 1`
- `problem_id: <int>`
- `id: <string>`

### 2.1 Lead record (`leads/*.yaml`)

```yaml
schema_version: 1
problem_id: 6
id: lead_20260123T000501Z_a1b2c3
title: "Green–Tao theorem"
status: new                 # new | investigating | promising | dead_end | incorporated
priority: high              # low | medium | high
tags: []
source:
  doi: "10.4007/annals.2008.167.481"
  arxiv_id: "math/0404188"
  url: null
notes: "Map to the problem statement."
created_at: "2026-01-23T00:05:01Z"
updated_at: "2026-01-23T00:05:01Z"
```

### 2.2 Hypothesis record (`hypotheses/*.yaml`)

```yaml
schema_version: 1
problem_id: 6
id: hyp_20260123T001000Z_d4e5f6
statement: "Conjecture: ..."
status: active              # active | refuted | proven | incorporated
confidence: medium          # low | medium | high
evidence: []                # list of lightweight refs (strings)
notes: ""
created_at: "2026-01-23T00:10:00Z"
updated_at: "2026-01-23T00:10:00Z"
```

### 2.3 Task record (`tasks/*.yaml`)

```yaml
schema_version: 1
problem_id: 6
id: task_20260123T002000Z_f00baa
title: "Extract exact lemma statement needed for step X"
status: todo                # todo | doing | blocked | done
priority: high              # low | medium | high
blocked_on: []              # list of task ids
links: []                   # list of lightweight refs (strings)
created_at: "2026-01-23T00:20:00Z"
updated_at: "2026-01-23T00:20:00Z"
```

### 2.4 Attempt record (`attempts/*.yaml`)

Attempts are treated as immutable after creation (append-only history).

```yaml
schema_version: 1
problem_id: 6
id: att_20260123T010203Z_ab12cd
kind: lean_loop             # lean_loop | manual
result: failed              # failed | partial | success
summary: "Stuck on lemma X; induction hypothesis too weak."
artifacts:
  lean_file: "formal/lean/Erdos/Problem006.lean"
  loop_run_log: "logs/loop/run_20260123_010203_ab12cd.jsonl"
created_at: "2026-01-23T01:02:03Z"
```

---

## 3) CLI Interface

All commands are under `erdos research`.

### Leads

```text
erdos research lead add PROBLEM_ID --title TEXT [--doi TEXT] [--arxiv-id TEXT] [--url TEXT]
                                  [--status STATUS] [--priority PRIORITY] [--notes TEXT]

erdos research lead list PROBLEM_ID [--status STATUS] [--priority PRIORITY]

erdos research lead update PROBLEM_ID LEAD_ID [--status STATUS] [--priority PRIORITY] [--notes TEXT]
```

### Hypotheses

```text
erdos research hypothesis add PROBLEM_ID --statement TEXT [--status STATUS] [--confidence CONF] [--notes TEXT]
erdos research hypothesis list PROBLEM_ID [--status STATUS]
erdos research hypothesis update PROBLEM_ID HYP_ID [--status STATUS] [--confidence CONF] [--notes TEXT]
```

### Tasks

```text
erdos research task add PROBLEM_ID --title TEXT [--status STATUS] [--priority PRIORITY]
erdos research task list PROBLEM_ID [--status STATUS] [--priority PRIORITY]
erdos research task update PROBLEM_ID TASK_ID [--status STATUS] [--priority PRIORITY]
```

### Attempts

```text
erdos research attempt log PROBLEM_ID --result RESULT --summary TEXT
                                     [--lean-file PATH] [--loop-log PATH]

erdos research attempt list PROBLEM_ID [--result RESULT]
```

### Maintenance

```text
erdos research fmt PROBLEM_ID
erdos research validate PROBLEM_ID
```

---

## 4) Output Schema (JSON)

All outputs use `CLIOutput`. Each command’s `data` must include:

- `problem_id`
- `record_kind` (when applicable: `lead|hypothesis|task|attempt`)
- `path` (created/updated record path, when applicable)
- `record` (the full record object for add/update)
- `records` (list result for list)

Example (`lead add`):

```json
{
  "problem_id": 6,
  "record_kind": "lead",
  "path": "…/research/problems/0006/leads/lead_20260123T000501Z_a1b2c3.yaml",
  "record": { "...": "..." }
}
```

---

## 5) Implementation (modules / wiring)

### New core modules

- `src/erdos/core/research/models.py`
  - Pydantic models + enums for record types.
- `src/erdos/core/research/store_fs.py`
  - Filesystem adapter for CRUD, plus `fmt` and `validate`.
- `src/erdos/core/research/ids.py`
  - Deterministic record ID generation.
- `src/erdos/core/research/yaml_io.py`
  - Canonical YAML serialization + atomic writes.
- `src/erdos/core/research/errors.py`
  - Typed exceptions for not-found/invalid-record cases.

### CLI wiring

- Extend `src/erdos/commands/research.py` with subcommand groups:
  - `lead`, `attempt`, `hypothesis`, `task`, plus `fmt` and `validate`.

---

## 6) Verification (TDD; testable claims)

### Unit tests (`tests/unit/research/`)

1) ID generation:
   - IDs match regex `^(lead|att|hyp|task)_[0-9]{8}T[0-9]{6}Z_[0-9a-f]{6}$`
2) Schema validation:
   - Missing required fields fails validation.
   - `problem_id` mismatch with folder fails validation.
3) Canonical formatting:
   - `fmt` produces stable ordering (byte-for-byte identical across repeated runs).

### Integration tests (`tests/integration/`)

1) Create workspace → create lead → list lead:
   - `--json research init 6`
   - `--json research lead add 6 --title "X" --notes "Y"`
   - `--json research lead list 6` includes the created record.
2) Update lead status:
   - `lead update` modifies `updated_at` and `status`.
3) `validate` catches corruption:
   - Create an invalid YAML file and ensure `validate` fails with `success=false`.

All integration tests must set:
- `ERDOS_DATA_PATH` (sample problems)
- `ERDOS_REPO_ROOT` (tmp workspace root)

---

## 7) References

- `docs/_archive/specs/spec-023-research-workspace.md`
- `docs/future/research-state-management-v3.md`

---

## 8) Changelog

- v1 (Complete): One-record-per-file schemas + CRUD + fmt/validate.
