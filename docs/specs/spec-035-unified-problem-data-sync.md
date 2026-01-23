# SPEC-035: Unified Problem Data Sync

> **Status:** Pending
>
> **Target:** v3.2 (critical path)
>
> **Resolves:** Data source fragmentation; missing proofs when problems are solved
>
> **Prerequisites:** SPEC-028 (v3 verification)

---

## Summary

Unify the three Erdős problem data sources into a single, coherent pipeline:

| Source | Has | Missing |
|--------|-----|---------|
| **teorth/erdosproblems** (submodule) | Status, metadata | Statements, proofs |
| **google-deepmind/formal-conjectures** | Lean statements | Status, proofs |
| **erdosproblems.com forum** | Proofs (as links) | API |

**Current gap:** When problem #347 was solved (2026-01-21), we didn't know:
- Our submodule was stale
- DeepMind still shows `sorry` (they don't track solutions)
- The actual Lean proof exists only as a GitHub link in a forum comment

---

## Goals / Non-Goals

### Goals

1. **Single source of truth** for problem status (submodule → local cache).
2. **Automated sync** of formal statements from DeepMind.
3. **Proof extraction** when problems are solved (GitHub links, not HTML scraping).
4. **Provenance tracking** (who solved, when, verification status).
5. **Offline-first** — all data cached locally, network only for sync.

### Non-Goals

- HTML scraping of erdosproblems.com (fragile, breaks on redesign).
- Replacing the submodule with a custom data format.
- Real-time sync (daily is sufficient).
- Hosting our own problem database (we track, not publish).

---

## Architecture

### Data Flow

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         SYNC PIPELINE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐                                                │
│  │  teorth/erdos-  │─────┐                                          │
│  │  problems       │     │                                          │
│  │  (submodule)    │     │  ┌──────────────────────────────────┐   │
│  └─────────────────┘     ├─▶│  Local Problem Cache             │   │
│          │               │  │  data/problems_enriched.yaml     │   │
│          ▼               │  │                                  │   │
│  git submodule update    │  │  - status (from submodule)       │   │
│                          │  │  - statement (from DeepMind)     │   │
│  ┌─────────────────┐     │  │  - proof_url (from forum)        │   │
│  │  DeepMind       │─────┤  │  - provenance metadata           │   │
│  │  formal-        │     │  └──────────────────────────────────┘   │
│  │  conjectures    │     │                    │                    │
│  └─────────────────┘     │                    ▼                    │
│          │               │  ┌──────────────────────────────────┐   │
│          ▼               │  │  formal/lean/Community/          │   │
│  erdos sync statements   │  │  (verified proofs)               │   │
│                          │  └──────────────────────────────────┘   │
│  ┌─────────────────┐     │                                          │
│  │  erdosproblems  │─────┘                                          │
│  │  .com forum     │                                                │
│  │  (proof links)  │                                                │
│  └─────────────────┘                                                │
│          │                                                          │
│          ▼                                                          │
│  erdos sync proofs --problem 347                                    │
│  (extracts GitHub link, clones, verifies, stores)                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Module Structure

```
src/erdos/core/
  sync/
    __init__.py
    submodule.py        # Git submodule operations
    statements.py       # DeepMind formal-conjectures sync
    proofs.py           # Forum proof link extraction + verification
    models.py           # SyncStatus, ProofProvenance, etc.
    service.py          # Orchestrates all sync operations
```

---

## CLI Interface

### Submodule Sync

```bash
# Update the submodule to latest
erdos sync submodule

# Check for stale submodule (CI warning)
erdos sync submodule --check
```

### Statement Sync

```bash
# Sync formal statements from DeepMind
erdos sync statements

# Sync specific problem
erdos sync statements --problem 347
```

### Proof Sync

```bash
# Attempt to fetch proof for a solved problem
erdos sync proof <problem_id>

# Example: Problem #347 was solved
erdos sync proof 347

# Output:
# Problem #347: Status = proved (Lean)
# Found proof link: https://github.com/ebarschkis/erdos-347-proof
# Cloning repository...
# Verifying Lean compilation...
# ✓ Proof verified (Lean 4.24.0)
# Stored: formal/lean/Community/Problem347.lean
```

### Full Sync

```bash
# Run all sync operations
erdos sync all

# Dry-run (report what would change)
erdos sync all --dry-run
```

---

## Forum Proof Extraction Strategy

**Key insight:** We don't scrape HTML. We extract **GitHub/GitLab links** from forum posts.

### Why This Works

1. **Proofs are code** — They live in Git repositories, not forum text.
2. **Links are stable** — GitHub URLs don't break on forum redesign.
3. **Verification is binary** — Either `lake build` succeeds or it doesn't.

### Extraction Pipeline

```python
# src/erdos/core/sync/proofs.py

@dataclass
class ProofSource:
    """Extracted proof link from forum."""
    problem_id: int
    url: str                    # GitHub/GitLab URL
    author: str                 # Forum username
    posted_at: datetime
    lean_version: str | None    # If mentioned

def extract_proof_links(problem_id: int) -> list[ProofSource]:
    """
    Extract proof repository links from forum thread.

    Strategy:
    1. Fetch forum thread (single HTTP request per problem)
    2. Find GitHub/GitLab links (regex: github.com/*, gitlab.com/*)
    3. Parse surrounding context for Lean version hints
    4. Return structured ProofSource list
    """
    ...

def verify_proof(source: ProofSource) -> VerificationResult:
    """
    Clone repository and verify the Lean proof compiles.

    Strategy:
    1. Clone to temp directory
    2. Run `lake build` (or `lean --run` for single files)
    3. Check for compilation errors
    4. Return success/failure with logs
    """
    ...
```

### Forum Thread URL Pattern

```
https://www.erdosproblems.com/forum/thread/{problem_id}
```

This is the **only** URL we need per problem. Stable, predictable.

---

## Provenance Model

```python
# src/erdos/core/sync/models.py

@dataclass
class ProofProvenance:
    """Track where a proof came from."""
    problem_id: int
    status: Literal["verified", "pending", "failed"]

    # Source information
    source_url: str             # GitHub repo URL
    source_commit: str          # Specific commit hash
    author: str                 # Who solved it
    solved_at: datetime         # When (from submodule)

    # Verification
    lean_version: str           # e.g., "4.24.0"
    verified_at: datetime | None
    verification_log: str | None

    # Storage
    local_path: str             # formal/lean/Community/Problem347.lean
```

### Storage Layout

```
formal/lean/Community/
  Problem347/
    Problem347.lean           # The actual proof
    lakefile.lean             # Build config
    PROVENANCE.json           # Metadata
```

`PROVENANCE.json` example:
```json
{
  "problem_id": 347,
  "status": "verified",
  "source_url": "https://github.com/ebarschkis/erdos-347-proof",
  "source_commit": "abc123def456",
  "author": "ebarschkis",
  "solved_at": "2026-01-21T21:37:00Z",
  "lean_version": "4.24.0",
  "verified_at": "2026-01-23T15:30:00Z"
}
```

---

## Caching Strategy

```
data/sync_cache/
  submodule_status.json     # Last sync time, commit hash
  statements/
    <problem_id>.lean       # Cached formal statements
  proofs/
    <problem_id>/
      links.json            # Extracted proof links
      verification.json     # Last verification result
```

---

## Configuration

```bash
# .env
ERDOS_SYNC_INTERVAL=86400           # Seconds between auto-syncs (default: 24h)
ERDOS_FORMAL_CONJECTURES_PATH=      # Override DeepMind repo path (optional)
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Submodule fetch fails | Warn, continue with cached data |
| No proof link found | Log as "no proof available yet" |
| Proof link broken (404) | Mark as "source_unavailable" |
| Lean compilation fails | Mark as "verification_failed", store logs |
| Multiple proof links | Verify all, prefer latest with matching Lean version |

---

## Testing

### Unit Tests

```python
# tests/unit/sync/test_proofs.py

def test_extract_github_links():
    """Verify GitHub link extraction from forum HTML."""
    html = '<a href="https://github.com/user/proof">proof</a>'
    links = extract_proof_links_from_html(html, problem_id=347)
    assert links[0].url == "https://github.com/user/proof"

def test_extract_ignores_non_code_links():
    """Don't extract documentation links, only code repos."""
    ...
```

### Integration Tests

```python
# tests/integration/test_sync.py

@pytest.mark.requires_network
def test_sync_submodule():
    """Verify submodule sync works."""
    ...

@pytest.mark.requires_network
def test_extract_real_proof_link():
    """Extract proof link from actual forum thread."""
    # Use problem #347 as test case
    ...
```

---

## Acceptance Criteria

1. [ ] `erdos sync submodule` updates the submodule
2. [ ] `erdos sync submodule --check` warns if stale (for CI)
3. [ ] `erdos sync statements` imports from DeepMind formal-conjectures
4. [ ] `erdos sync proof <id>` extracts GitHub link from forum
5. [ ] Proof verification runs `lake build` and reports success/failure
6. [ ] Verified proofs stored in `formal/lean/Community/`
7. [ ] `PROVENANCE.json` tracks who solved, when, source URL
8. [ ] `erdos sync all` orchestrates full pipeline
9. [ ] Offline-friendly: cached data used when network unavailable

---

## Future Enhancements

- **RSS feed** for forum updates (if available) — more efficient than polling
- **Contact Terence Tao** for structured data export or webhook
- **CI integration** — Auto-sync on schedule, PR on new proofs
- **Notification** when a problem in your watchlist is solved

---

## References

- [teorth/erdosproblems](https://github.com/teorth/erdosproblems) — Status tracking repo
- [google-deepmind/formal-conjectures](https://github.com/google-deepmind/formal-conjectures) — Formal statements
- [erdosproblems.com](https://www.erdosproblems.com/) — Forum with proofs
- SPEC-016: Formal Conjectures (existing DeepMind import)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-23 | Initial draft |
