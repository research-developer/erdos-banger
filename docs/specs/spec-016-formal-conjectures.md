# Spec 016: Formal Conjectures Integration

> Imports and tracks existing formalizations from the Lean community to avoid duplicating work.

**Status:** Pending
**Target:** v1.4
**Prerequisites (SSOT):**
- Lean integration: `docs/_archive/specs/spec-007-lean-integration.md`
- Problem loader: `docs/_archive/specs/spec-005-problem-loader.md`

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
- Verifying upstream proofs (assume they compile)

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
- `--diff`: Show differences between local and upstream (if both exist)
- `--no-network`: Do not fetch remote Lean sources (diff/import checks use cache only)

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
- `--skip-lean-validation`: Skip Lean syntax validation if Lean toolchain is unavailable (emits a warning)

### 1.3 `erdos lean formalize` (Extended)

Add option:

- `--no-import`: Generate fresh skeleton even if upstream formalization exists

Default behavior: Check upstream first, import if available, else generate skeleton.

### Examples

```bash
# Show formalization status for all problems
uv run erdos lean status

# Show status for specific problem
uv run erdos lean status 6

# Import upstream formalization
uv run erdos lean import 6

# Force fresh skeleton (ignore upstream)
uv run erdos lean formalize 6 --no-import

# Diff local vs upstream
uv run erdos lean status 6 --diff
```

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
      "hash": "abc123"
    },
    "comparison": "differs"
  }
}
```

---

## 4) Import Behavior

### Import Flow

1. Check upstream metadata for `formalized.state == "yes"` (if upstream metadata is available)
2. Derive candidate source URL from known repository path patterns (or use `--source URL`)
3. Fetch Lean file from source (unless `--no-network` and not cached)
4. Validate it's syntactically valid Lean 4 using the local Lean toolchain
   - If Lean is unavailable: fail with a clear error unless `--skip-lean-validation` is set
5. Write to `formal/lean/Erdos/Problem{id:03d}.lean`
6. Record provenance in local metadata

### Provenance Tracking

Create `formal/lean/Erdos/.provenance.yaml`:

```yaml
schema_version: 1
imports:
  - problem_id: 6
    source: "google-deepmind/formal-conjectures"
    url: "https://raw.githubusercontent.com/google-deepmind/formal-conjectures/main/FormalConjectures/ErdosProblems/6.lean"
    imported_at: "2026-01-18T10:30:45Z"
    commit: "abc123"
    local_hash: "def456"
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

### 5.3 Extend: `src/erdos/core/models.py`

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
  - Parse formalization metadata from problem record
  - Provenance file serialization
  - Diff detection between local and upstream

### Integration Tests

- `tests/integration/test_lean_import.py`
  - `erdos lean status` returns correct counts
  - `erdos lean import` with fixture source
  - `--force` overwrites existing file
  - `--no-import` on formalize generates skeleton

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
- Cache fetched files locally
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
