# Spec 023: Research Workspace (Filesystem SSOT)

> Adds a canonical, git-tracked `research/` workspace for per-problem “campaign memory” (scratchpad + synthesis + structured record folders).

**Status:** Archived
**Target:** v3.0
**Prerequisites (SSOT):**
- CLI patterns: `docs/_archive/specs/spec-004-cli-architecture.md`
- Output envelope: `docs/_archive/specs/spec-003-domain-models.md` (`CLIOutput`)
- Problem loader: `docs/_archive/specs/spec-005-problem-loader.md`
- Research state design (proposal): `docs/future/research-state-management-v3.md`

---

## 0) Scope (v3.0)

### In scope

1) Introduce a canonical research workspace rooted at `research/` (git-tracked).
2) Define and create a per-problem workspace directory structure under `research/problems/{problem_id:04d}/`.
3) Add a new top-level CLI group: `erdos research`.
4) Implement the following subcommands end-to-end (CLI → core → tests):
   - `erdos research init PROBLEM_ID`
   - `erdos research open PROBLEM_ID`
   - `erdos research note PROBLEM_ID TEXT` (append-only)
   - `erdos research status PROBLEM_ID` (minimal dashboard: counts + paths)
5) Ensure all commands support `--json` via `CLIOutput`.

### Out of scope

- CRUD for structured records (leads/attempts/hypotheses/tasks) → SPEC-024
- Indexing research state into `index/erdos.sqlite` → SPEC-025
- Deterministic synthesis generation → SPEC-026
- Loop → research integration → SPEC-027
- Any database-as-SSOT approach

---

## 1) CLI Interface

### Command group

```text
erdos research [SUBCOMMAND]
```

### `erdos research init`

```text
erdos research init PROBLEM_ID
```

Behavior:
- Validates `PROBLEM_ID` exists in the problem dataset (`ProblemRepository.get_by_id`).
- Creates `research/` workspace (if missing).
- Creates per-problem workspace directory and template files if missing.
- Idempotent: running again must not overwrite existing user content.

### `erdos research open`

```text
erdos research open PROBLEM_ID
```

Behavior:
- Prints the absolute path to `research/problems/{problem_id:04d}/` (and returns it in JSON mode).
- Does not open an editor in v3 (keep behavior deterministic and CI-safe).

### `erdos research note`

```text
erdos research note PROBLEM_ID TEXT
erdos research note PROBLEM_ID -    # read TEXT from stdin
```

Behavior:
- Appends a timestamped entry to `SCRATCHPAD.md` (append-only).
- Must not rewrite prior content.

### `erdos research status`

```text
erdos research status PROBLEM_ID
```

Behavior:
- Produces a minimal “dashboard” with:
  - workspace path
  - presence of `SCRATCHPAD.md` and `SYNTHESIS.md`
  - counts of record files in `leads/`, `attempts/`, `hypotheses/`, `tasks/`

---

## 2) Output Schema (JSON)

All JSON output must be wrapped in `CLIOutput` (schema_version=1).

### `erdos research init`

`data` must include:

```json
{
  "problem_id": 6,
  "research_root": "…/research",
  "problem_dir": "…/research/problems/0006",
  "created": true,
  "created_paths": [
    "research/VERSION",
    "research/problems/0006/meta.yaml",
    "research/problems/0006/README.md",
    "research/problems/0006/SCRATCHPAD.md",
    "research/problems/0006/SYNTHESIS.md",
    "research/problems/0006/leads",
    "research/problems/0006/attempts",
    "research/problems/0006/hypotheses",
    "research/problems/0006/tasks"
  ],
  "workspace_version": 1
}
```

Notes:
- `created=false` and `created_paths=[]` is valid on a no-op/idempotent run.

### `erdos research open`

```json
{
  "problem_id": 6,
  "problem_dir": "…/research/problems/0006"
}
```

### `erdos research note`

```json
{
  "problem_id": 6,
  "scratchpad_path": "…/research/problems/0006/SCRATCHPAD.md",
  "appended_bytes": 123
}
```

### `erdos research status`

```json
{
  "problem_id": 6,
  "problem_dir": "…/research/problems/0006",
  "files": {
    "meta": true,
    "scratchpad": true,
    "synthesis": true
  },
  "counts": {
    "leads": 0,
    "attempts": 0,
    "hypotheses": 0,
    "tasks": 0
  }
}
```

---

## 3) Filesystem Contract (authoritative)

### Workspace root resolution

All research paths are relative to:

1) `ERDOS_REPO_ROOT` if set (via `AppConfig.repo_root`), else
2) the current working directory (assumed to be repo root)

The workspace root is `{repo_root}/research/`.

### Workspace layout (created by `init`)

```text
research/
  VERSION                         # "1\n"
  global/
    TECHNIQUES.md                 # stub (non-empty)
    GLOSSARY.md                   # stub (non-empty)
  problems/
    0006/
      meta.yaml                   # schema_version=1
      README.md                   # stub (non-empty)
      SCRATCHPAD.md               # stub (non-empty)
      SYNTHESIS.md                # stub (non-empty)
      leads/                      # empty
      attempts/                   # empty
      hypotheses/                 # empty
      tasks/                      # empty
```

Template stubs must be deterministic and safe to commit.

---

## 4) Implementation (modules / wiring)

### New core modules

- `src/erdos/core/research/paths.py`
  - Resolve `research/` root and per-problem directories.
- `src/erdos/core/research/workspace.py`
  - Create workspace structure + templates idempotently.
- `src/erdos/core/research/note.py`
  - Append-only scratchpad writer (stdin support).
- `src/erdos/core/research/status.py`
  - Minimal status computation (counts + file presence).

### New CLI adapter

- `src/erdos/commands/research.py`
  - Typer app group with subcommands: `init`, `open`, `note`, `status`.

### Modify CLI composition root

- `src/erdos/cli.py`
  - Register the `research` command group.

---

## 5) Verification (TDD; testable claims)

### Unit tests

Add tests under `tests/unit/research/`:

1) Path resolution:
   - With `ERDOS_REPO_ROOT=/tmp/x`, workspace root is `/tmp/x/research`.
   - Without `ERDOS_REPO_ROOT`, workspace root is `Path.cwd()/research`.
2) Workspace init is idempotent:
   - Second call must not modify existing file content (except allowed metadata fields if any are updated; v3 forbids overwrites).
3) `note` appends without rewriting:
   - A second note call must preserve the first entry.

### Integration tests

Add tests under `tests/integration/`:

1) `erdos --json research init 6`:
   - exit code 0
   - valid JSON CLIOutput
   - creates all required paths under `tmp_path/research/...`
2) `erdos --json research note 6 "hello"`:
   - scratchpad contains the appended text
   - output includes `scratchpad_path`
3) `erdos --json research status 6`:
   - reports `counts.* == 0` on fresh workspace

Test harness requirements:
- Use `sample_problems_yaml` fixture and set `ERDOS_DATA_PATH` + `ERDOS_REPO_ROOT`.

---

## 6) References

- `docs/future/research-state-management-v3.md`
- `docs/specs/master-vision.md`

---

## 7) Changelog

- v1 (Complete): Introduce canonical `research/` workspace + minimal CLI.
