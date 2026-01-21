# Spec 016: Formal Conjectures Integration

> Imports and tracks existing formalizations from the Lean community to avoid duplicating work.

**Status:** Complete
**Implemented In:** 85f4ddb
**Target:** v1.4
**Prerequisites (SSOT):**
- Lean integration: `docs/_archive/specs/spec-007-lean-integration.md`
- Problem loader: `docs/_archive/specs/spec-005-problem-loader.md`
- Upstream metadata checkout: `data/erdosproblems/data/problems.yaml` (git submodule; see `data/README.md`)

---

## 0) Scope (v1.4)

### In scope

1. **Detect formalized problems** from upstream `teorth/erdosproblems` metadata
2. **Import existing Lean files** from Formal Conjectures Repository (if available)
3. **Track formalization provenance** (upstream vs local)
4. **Diff local vs upstream** formalizations
5. **`erdos lean status`** command to show formalization coverage

### Out of scope

- Automatic proof merging
- Contributing back to upstream repositories
- Semantic proof checking beyond compilation (we only validate that imported files typecheck when Lean is available)

### Background

The `teorth/erdosproblems` dataset tracks formalization status in its metadata:
```yaml
formalized:
  state: "yes"  # or "no" (SSOT: archived Spec 005 upstream schema)
  last_update: "2025-09-18"
```

In erdos-banger v1, the enriched dataset uses `ProblemRecord.formalized: bool` (SSOT: archived Spec 003) derived from upstream `formalized.state` (SSOT: archived Spec 005). The upstream metadata does **not** provide a canonical Lean file URL; imports use known repository path patterns (see Section 2).

Many problems (hundreds) already have Lean formalizations in community repositories. We should import these rather than generating fresh skeletons.

---

## 1) CLI Interface

### 1.1 `erdos lean status`

```text
erdos lean status [PROBLEM_ID] [OPTIONS]
```

**Arguments**

- `PROBLEM_ID` (optional): Show status for specific problem

**Options** (default: check both upstream and local; `--diff` requires both)

- `--upstream`: Check upstream metadata for formalization status
- `--local`: Check local `formal/lean/Erdos/` directory
- `--diff`: Show differences between local and upstream (requires `PROBLEM_ID`)
- `--no-network`: Do not fetch remote Lean sources. For `--diff`: if the upstream Lean file is not already cached, return `ExitCode.NETWORK_ERROR` (otherwise use cache).

For `--diff`:
- If the upstream file is not cached and `--no-network` is **not** set, fetch it into the cache first, then compare.

### 1.2 `erdos lean import`

```text
erdos lean import PROBLEM_ID [OPTIONS]
```

**Arguments**

- `PROBLEM_ID` (required): Problem to import formalization for

**Options**

- `--source URL`: Override source URL (default: derived from Formal Conjectures path pattern)
- `--force`: Overwrite existing local file
- `--dry-run`: Show what would be imported without writing
- `--no-network`: Use cached upstream file only (error if not cached)
- `--skip-lean-validation`: Do not run `erdos lean check` on the imported file (emits a warning in human mode; emits `data.lean_validated=false` in JSON mode)

### 1.3 `erdos lean formalize` (Extended)

Add option:

- `--import-upstream`: If an upstream formalization is available, import it instead of generating a skeleton. (Default: generate a local skeleton; no network I/O.)

Default behavior: preserve v1 behavior (`erdos lean formalize` generates a local skeleton). Import is explicit via `erdos lean import` or `--import-upstream`.

### Examples

```bash
# Show formalization status for all problems
uv run erdos lean status

# Show status for specific problem
uv run erdos lean status 6

# Import upstream formalization
uv run erdos lean import 6

# Import upstream instead of generating a local skeleton
uv run erdos lean formalize 6 --import-upstream

# Diff local vs upstream
uv run erdos lean status 6 --diff
```

### Exit Codes (SSOT)

Use `ExitCode` from `src/erdos/core/exit_codes.py`:

- `ExitCode.SUCCESS` (0): command completed successfully
- `ExitCode.NOT_FOUND` (3): unknown problem id, missing local file, or no upstream formalization available for import/diff
- `ExitCode.NETWORK_ERROR` (4): `--no-network` prevents required remote fetch
- `ExitCode.LEAN_ERROR` (5): Lean validation failed (when validation is enabled)
- `ExitCode.CONFIG_ERROR` (10): missing upstream metadata checkout (`data/erdosproblems/data/problems.yaml`) when `--upstream` is requested
- `ExitCode.ERROR` (1): all other errors

---

## 2) Formalization Sources

### Primary: teorth/erdosproblems Metadata

The upstream dataset includes `formalized` field:

```yaml
- number: "6"
  status:
    state: "proved"
  formalized:
    state: "yes"
    last_update: "2025-09-18"
```

### Secondary: Known Repositories

Deterministic sources for import (derived; not present in upstream metadata):

| Repository | Path Pattern |
|------------|--------------|
| google-deepmind/formal-conjectures | `FormalConjectures/ErdosProblems/{id}.lean` |
| leanprover-community/mathlib4 | (future) best-effort heuristics; not in v1.4 scope |

**Upstream metadata source (SSOT):**
- Read upstream metadata from `data/erdosproblems/data/problems.yaml` (git submodule).
- If this file is missing and `--upstream` is requested, return `CLIOutput.err(...)` with `error.type="ConfigError"` and `error.code=ExitCode.CONFIG_ERROR` (SSOT: `src/erdos/core/exit_codes.py`).

**Upstream file fetch (default source):**
- Base raw URL: `https://raw.githubusercontent.com/google-deepmind/formal-conjectures/main/`
- Default file URL for a problem id: `{base}FormalConjectures/ErdosProblems/{problem_id}.lean` (verified for problem 6 as of 2026-01).

---

## 3) Status Output

### Human Mode (Single Problem)

```
Problem 6: Primes in Arithmetic Progressions

Upstream formalization:
  Status: formalized (Lean 4)
  Source: google-deepmind/formal-conjectures
  URL: https://github.com/google-deepmind/formal-conjectures/blob/main/FormalConjectures/ErdosProblems/6.lean

Local formalization:
  File: formal/lean/Erdos/Problem006.lean
  Has sorry: yes
  Last modified: 2026-01-15

Comparison: Local file differs from upstream (local has sorry, upstream complete)
```

### Human Mode (All Problems)

```
Formalization Status (1135 problems)

                    Upstream    Local
Formalized (Lean4)     52         12
Partial                 8          5
Not formalized       1075       1118

Problems with both:    10
  - Matching: 3
  - Differing: 7
```

### JSON Mode

```json
{
  "schema_version": 1,
  "command": "erdos lean status",
  "success": true,
  "data": {
    "problem_id": 6,
    "upstream": {
      "available": true,
      "formalized": true,
      "state": "yes",
      "last_update": "2025-09-18",
      "source": "google-deepmind/formal-conjectures",
      "url": "https://raw.githubusercontent.com/google-deepmind/formal-conjectures/main/FormalConjectures/ErdosProblems/6.lean"
    },
    "local": {
      "exists": true,
      "path": "formal/lean/Erdos/Problem006.lean",
      "has_sorry": true,
      "sha256": "abc123"
    },
    "comparison": "differs"
  }
}
```

### JSON Mode (`erdos lean import`)

On success, `erdos lean import --json` returns `CLIOutput.ok(...)` where `data` includes:

```json
{
  "problem_id": 6,
  "dry_run": false,
  "written": true,
  "path": "formal/lean/Erdos/Problem006.lean",
  "cache_path": "formal/lean/.upstream_cache/formal-conjectures/ErdosProblems/6.lean",
  "source": "google-deepmind/formal-conjectures",
  "url": "https://raw.githubusercontent.com/google-deepmind/formal-conjectures/main/FormalConjectures/ErdosProblems/6.lean",
  "sha256": "def456",
  "lean_validated": true
}
```

---

## 4) Import Behavior

### Import Flow

1. Check upstream metadata for `formalized.state == "yes"` (if upstream metadata is available)
2. Derive candidate source URL from known repository path patterns (or use `--source URL`)
3. Fetch Lean file from source (unless `--no-network` and not cached)
   - Cache path (SSOT): `formal/lean/.upstream_cache/formal-conjectures/ErdosProblems/{problem_id}.lean`
4. If `--skip-lean-validation` is not set, validate the imported file by running `erdos lean check` on it (requires Lean toolchain).
5. Write to `formal/lean/Erdos/Problem{id:03d}.lean` (or print the planned write in `--dry-run` mode)
6. Record provenance in local metadata (`.provenance.yaml`, below)

**Hashing (SSOT):**
- Use SHA-256 for file content hashes in both JSON output and `.provenance.yaml`.
- `sha256` must be computed on the raw file bytes written (post-download; pre/post newline normalization is not allowed).

### Provenance Tracking

Create `formal/lean/Erdos/.provenance.yaml`:

```yaml
schema_version: 1
imports:
  - problem_id: 6
    source: "google-deepmind/formal-conjectures"
    url: "https://raw.githubusercontent.com/google-deepmind/formal-conjectures/main/FormalConjectures/ErdosProblems/6.lean"
    imported_at: "2026-01-18T10:30:45Z"
    remote_etag: "\"5feb9d6a...\""
    sha256: "def456"
```

### Conflict Handling

| Scenario | Default Behavior |
|----------|------------------|
| No local file exists | Import upstream |
| Local file exists, same content | Skip (already imported) |
| Local file exists, different | Error unless `--force` |
| No upstream formalization | Error (nothing to import) |

---

## 5) Implementation

### 5.1 New Module: `src/erdos/core/formal_conjectures.py`

Responsibilities:

1. Parse upstream formalization metadata
2. Fetch Lean files from known sources
3. Compare local vs upstream files
4. Track provenance

### 5.2 Extend: `src/erdos/commands/lean.py`

Add subcommands:
- `status` - Show formalization coverage
- `import` - Import upstream formalizations

Modify `formalize`:
- Check upstream before generating skeleton

### 5.3 Extend: `src/erdos/core/models/`

**Do not change** `ProblemRecord` for v1.4.

- `ProblemRecord.formalized: bool` remains the SSOT field for “formalized yes/no” in the enriched dataset (archived Spec 003).
- Richer upstream/provenance details are returned by `erdos lean status` and stored in `formal/lean/Erdos/.provenance.yaml`.

---

## 6) Verification: This Spec is Testable

### Vertical Slice Test

```bash
# Check status (uses local dataset metadata)
uv run erdos lean status 6 --json | jq '.data.upstream.formalized'

# Import (with mock/fixture for network)
uv run erdos lean import 6 --dry-run

# Verify provenance tracking
cat formal/lean/Erdos/.provenance.yaml
```

### Unit Tests

- `tests/unit/test_formal_conjectures.py`
  - Parse formalization metadata from upstream YAML (`data/erdosproblems/data/problems.yaml` or a fixture copy)
  - Provenance file serialization
  - Diff detection between local and cached upstream (SHA-256 compare)
  - `has_sorry` detection on small Lean snippets (regex token match; ignore lines starting with `--`)

### Integration Tests

- `tests/integration/test_lean_import.py`
  - `erdos lean status` returns correct counts
  - `erdos lean import` with fixture source (network mocked via `responses`; no real network)
  - `--force` overwrites existing file
  - `--import-upstream` on formalize imports when cached; without cache and with `--no-network`, returns `ExitCode.NETWORK_ERROR`

### Acceptance Criteria

```bash
uv run ruff check .
uv run mypy src/
uv run pytest -m "not requires_lean and not requires_network"
```

---

## 7) Network Considerations

### Fetching Upstream Files

- Use GitHub raw URLs for known repositories (Formal Conjectures)
- Cache fetched files locally under `formal/lean/.upstream_cache/` (see Section 4)
- Respect rate limits (GitHub: 60 req/hour unauthenticated)
- `--no-network` (command option) must use cached/local data only

### Offline Mode

If upstream URL is unreachable:
- Fall back to cached version if available
- Error with clear message if not cached

---

## References

- teorth/erdosproblems: `https://github.com/teorth/erdosproblems`
- Formal Conjectures Repository: `https://github.com/google-deepmind/formal-conjectures`
- Master vision formalization strategy: `docs/specs/master-vision.md` (Section 5)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-18 | Initial spec |
