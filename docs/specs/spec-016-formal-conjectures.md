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
  state: yes  # or "no", "partial"
  lean4: true
  source: "formal-conjectures"  # or URL
```

Many problems (~50+) already have Lean 4 formalizations in community repositories. We should import these rather than generating fresh skeletons.

---

## 1) CLI Interface

### 1.1 `erdos lean status`

```text
erdos lean status [PROBLEM_ID] [OPTIONS]
```

**Arguments**

- `PROBLEM_ID` (optional): Show status for specific problem

**Options**

- `--upstream`: Check upstream metadata for formalization status
- `--local`: Check local `formal/lean/Erdos/` directory
- `--diff`: Show differences between local and upstream (if both exist)

### 1.2 `erdos lean import`

```text
erdos lean import PROBLEM_ID [OPTIONS]
```

**Arguments**

- `PROBLEM_ID` (required): Problem to import formalization for

**Options**

- `--source URL`: Override source URL (default: from upstream metadata)
- `--force`: Overwrite existing local file
- `--dry-run`: Show what would be imported without writing

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
- id: 6
  status:
    state: proved
  formalized:
    state: yes
    lean4: true
    source: "https://github.com/teorth/formal-conjectures/blob/main/FormalConjectures/Erdos/Problem006.lean"
```

### Secondary: Known Repositories

Fallback sources if metadata doesn't specify:

| Repository | Path Pattern |
|------------|--------------|
| teorth/formal-conjectures | `FormalConjectures/Erdos/Problem{id:03d}.lean` |
| leanprover-community/mathlib4 | Various locations |

---

## 3) Status Output

### Human Mode (Single Problem)

```
Problem 6: Primes in Arithmetic Progressions

Upstream formalization:
  Status: formalized (Lean 4)
  Source: teorth/formal-conjectures
  URL: https://github.com/teorth/formal-conjectures/...

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
      "formalized": true,
      "lean4": true,
      "source": "teorth/formal-conjectures",
      "url": "https://..."
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

1. Check upstream metadata for `formalized.source` or `formalized.url`
2. Fetch Lean file from source
3. Validate it's syntactically valid Lean 4
4. Write to `formal/lean/Erdos/Problem{id:03d}.lean`
5. Record provenance in local metadata

### Provenance Tracking

Create `formal/lean/Erdos/.provenance.yaml`:

```yaml
schema_version: 1
imports:
  - problem_id: 6
    source: "teorth/formal-conjectures"
    url: "https://..."
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

Add to `ProblemRecord`:

```python
class FormalizationMeta(BaseModel):
    state: Literal["yes", "no", "partial"]
    lean4: bool = False
    source: str | None = None
    url: str | None = None
```

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

- Use GitHub raw URLs for known repositories
- Cache fetched files locally
- Respect rate limits (GitHub: 60 req/hour unauthenticated)
- `--no-network` flag should use cached/local data only

### Offline Mode

If upstream URL is unreachable:
- Fall back to cached version if available
- Error with clear message if not cached

---

## References

- teorth/erdosproblems: `https://github.com/teorth/erdosproblems`
- Formal Conjectures Repository: `https://github.com/teorth/formal-conjectures`
- Master vision formalization strategy: `docs/specs/master-vision.md` (Section 5)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-18 | Initial spec |
