# SPEC-035: Unified Problem Data Sync

> **Status:** Complete
>
> **Target:** v3.2 (critical path)
>
> **Resolves:** Data source fragmentation; missing proofs when problems are solved
>
> **Prerequisites:** SPEC-028 (v3 verification)

---

## Summary

Unify the four Erdős problem data sources into a single, coherent pipeline:

| Source | Has | Missing |
|--------|-----|---------|
| **teorth/erdosproblems** (submodule) | Status, metadata | Statements, proofs |
| **google-deepmind/formal-conjectures** | Lean statements | Status, proofs |
| **erdosproblems.com website** | Statements, LaTeX, tags, refs | API |
| **erdosproblems.com forum** | Proofs (as links) | API |

**Example failure mode (real incident):** A problem can be solved and we miss it because:
- the `data/erdosproblems` submodule can be stale locally,
- DeepMind formal statements don’t imply a solved status (they intentionally contain `sorry`),
- the actual proof may only be discoverable via a forum comment that links to a code repository.

---

## Goals / Non-Goals

### Goals

1. **Maintain the local CLI dataset** (`data/problems_enriched.yaml`, gitignored) by merging:
   - **metadata** from `data/erdosproblems/data/problems.yaml` (submodule): `status`, `prize`, `tags`, `formalized`, `oeis_ids` (and optionally `notes` from upstream comments)
   - **content** from `erdosproblems.com/{id}` (structured parsing): `title`, `statement`, `references`
   - **sync timestamps / last_update fields** are recorded in `data/sync_cache/` (not in `ProblemRecord`, which is intentionally minimal)
2. **Keep formal Lean statements synced** using the existing `erdos lean import` pipeline (SPEC-016), optionally surfaced via `erdos sync statements` as a thin wrapper.
3. **Extract proof repository links** from `erdosproblems.com/forum/thread/{id}` (best-effort).
4. **Optionally verify proofs** by cloning and running `lake build` in a temp directory (opt-in), recording toolchain + logs.
5. **Record provenance** as best-effort structured metadata (some fields may be unknown/unavailable).
6. **Offline-first** — cached data is used when network is unavailable; network is only required for sync steps.

### Non-Goals

- **Arbitrary HTML scraping** (we parse structured fields, not arbitrary content).
- Replacing the submodule with a custom data format.
- Real-time sync (daily is sufficient).
- Hosting our own problem database (we track, not publish).

### Clarification: Structured Parsing vs Scraping

We **do** parse HTML from erdosproblems.com, but only **structured fields**:
- Status badges (CSS class-based, stable)
- LaTeX statements (dedicated `<div>` containers)
- Tags (semantic markup)
- "View LaTeX source" links (stable URL pattern)

We **don't** scrape arbitrary prose or layout-dependent content.

---

## Architecture

### SSOT & Merge Rules (Precise)

This spec intentionally distinguishes:

- **Operational SSOT for CLI**: `data/problems_enriched.yaml` (gitignored) is the *effective* dataset the CLI reads via `ProblemLoader`.
- **Provenance SSOT for sync**: `data/sync_cache/` (gitignored) records what we fetched, when, from where, and what we verified.

#### Field Precedence (per `ProblemRecord`)

| Field | Source | Merge rule |
|------|--------|------------|
| `id` | CLI input / derived from upstream number | Must match requested problem id |
| `title` | Website | Overwrite only on successful parse |
| `statement` | Website (HTML) or LaTeX (optional) | Overwrite only on successful parse; never write empty |
| `references` | Website | Overwrite only on successful parse |
| `status` | Submodule | Overwrite on successful submodule parse (this is the main “staleness” fix) |
| `prize` | Submodule | Overwrite on successful submodule parse |
| `tags` | Submodule (primary), website (optional secondary) | Default: submodule tags; optional: union with website tags if we decide it’s safe |
| `formalized` | Submodule | Overwrite on successful submodule parse |
| `oeis_ids` | Submodule | Overwrite on successful submodule parse (normalizing `oeis` → `oeis_ids`) |
| `notes` | Local (optional), or submodule comments (optional) | Default: preserve existing `notes`; only fill when missing unless `--overwrite-notes` is set |

#### Cross-checks (never authoritative by default)

- If website “status badge” disagrees with submodule `status`, record a warning and store the observed badge text under `data/sync_cache/website/<id>.json`.
- DeepMind “formalized” UI hints from the website are treated as *advisory*; `formalized` remains submodule-sourced.

### Data Flow

```text
Sources
  - data/erdosproblems/ (git submodule): status/prize/tags/formalized/oeis/comments (+ last_update, recorded in sync cache)
  - https://www.erdosproblems.com/{id}: title/statement + references + (optional) LaTeX source
  - https://www.erdosproblems.com/forum/thread/{id}: proof repo links (GitHub/GitLab)
  - google-deepmind/formal-conjectures: Lean statement skeletons (with sorry)

Artifacts / outputs
  - data/problems_enriched.yaml (gitignored; ProblemLoader schema; SSOT for CLI)
      <- merged status/prize/tags/formalized/oeis_ids (+ optional notes) + title/statement/references
  - data/latex/{id}.tex (gitignored; raw LaTeX source, optional)
  - formal/lean/Erdos/Problem{ID}.lean (tracked; from `erdos lean import`, optional)
  - data/sync_cache/proofs/{id}/... (gitignored; cloned repos + verification logs, optional)
```

### Module Structure

```text
src/erdos/commands/
  sync/
    __init__.py         # `erdos sync` Typer app entrypoint
    all_cmd.py          # `erdos sync all`
    proof_cmd.py        # `erdos sync proof`
    statements_cmd.py   # `erdos sync statements` (thin wrapper over `erdos lean import`)
    submodule_cmd.py    # `erdos sync submodule`
    website_cmd.py      # `erdos sync website`
src/erdos/core/
  sync/
    __init__.py
    submodule.py        # Git submodule operations (teorth/erdosproblems)
    website.py          # Website extraction (title/statement/refs + optional LaTeX)
    forum.py            # Forum thread fetch + proof link extraction
    proofs.py           # Repo clone + Lean verification (opt-in)
    models.py           # Sync models + provenance records
    service.py          # Orchestrates all sync operations
  formal_conjectures/   # Existing DeepMind import (SPEC-016; used by `erdos lean import`)
```

---

## Determinism, Idempotency, and Safety (MUST)

1. Every `erdos sync ...` command is **idempotent** (running twice yields no changes on the second run).
2. Writes are **atomic**:
   - `data/problems_enriched.yaml` is written via temp file + replace (no partial writes).
   - sync cache JSON files use the same atomic strategy.
3. Sync is **deterministic**:
   - merge order is stable (per-field precedence defined above),
   - iteration order is stable (ascending problem id),
   - selection among multiple proof links is deterministic (see below).
4. Defaults are **safe**:
   - `erdos sync proof <id>` is discover-only (no cloning, no executing build tools),
   - `--verify` is explicit and prints a clear warning that it runs untrusted build tooling.

---

## CLI Interface

### Submodule Sync

```bash
# Update the submodule to latest
erdos sync submodule

# Check for stale submodule (CI warning)
erdos sync submodule --check
```

### Statement Sync (DeepMind → Lean)

This delegates to the existing `erdos lean import` command (SPEC-016). The `erdos sync` wrapper exists only so `erdos sync all` can orchestrate it.

```bash
# Import the upstream Lean statement skeleton into our Lean project
erdos lean import 347

# Equivalent wrapper (optional; kept under `erdos sync` for orchestration)
erdos sync statements 347
```

### Website Sync (erdosproblems.com → problems_enriched.yaml)

```bash
# Fetch and parse the public problem page, updating data/problems_enriched.yaml
erdos sync website 275

# Optional: also fetch raw LaTeX source (saved to data/latex/275.tex)
erdos sync website 275 --latex
```

### Proof Sync

```bash
# Extract proof repo links from the forum thread (records provenance)
erdos sync proof <problem_id>

# Additionally clone + verify proof (opt-in; runs `lake build`)
erdos sync proof <problem_id> --verify

# Example:
erdos sync proof 347 --verify

# Output:
# Problem #347: status=proved (from submodule)
# Found proof repo link in forum: https://github.com/ebarschkis/erdos-347-proof
# Cloning repository...
# Verifying Lean compilation...
# ✓ Proof verified (lake build)
# Recorded provenance: data/sync_cache/proofs/347/provenance.json
```

### Full Sync

```bash
# Run all sync operations
erdos sync all

# Dry-run (report what would change)
erdos sync all --dry-run
```

### JSON Output Contract (Global `--json`)

All `erdos sync ...` commands MUST support the global `--json` flag and return `CLIOutput` with deterministic `data` shapes suitable for tests:

- `erdos --json sync submodule`: `{ "checked": bool, "updated": bool, "previous_commit": str | null, "current_commit": str | null, "stale": bool | null }`
- `erdos --json sync website <id>`: `{ "problem_id": int, "updated": bool, "latex_saved": bool, "cached": bool, "warnings": list[str] }`
- `erdos --json sync proof <id>`: `{ "problem_id": int, "links": list[{"url": str}], "provenance_path": str, "verification_status": str }`
- `erdos --json sync all`: `{ "submodule": {...}, "website": {...}, "proofs": {...}, "statements": {...} }`

---

## Forum Proof Extraction Strategy

**Key insight:** We don't scrape HTML. We extract **GitHub/GitLab links** from forum posts.

This is still HTML parsing, but it’s intentionally narrow: we treat the forum page as a transport for links, and the Git host as the durable storage.

### Why This Works

1. **Proofs are code** — They live in Git repositories, not forum text.
2. **Links are stable** — GitHub URLs don't break on forum redesign.
3. **Verification is binary** — Either `lake build` succeeds or it doesn't.

### Safety Constraints (MUST)

- Default behavior is **discover-only** (extract links + record provenance). No cloning/building unless `--verify` is set.
- Only allow `https://` links to an allowlist of hosts by default (at least `github.com` and `gitlab.com`).
- Enforce clone/build timeouts and bounded log sizes; record logs to the sync cache for debugging.

### Extraction Pipeline

```python
# src/erdos/core/sync/proofs.py

@dataclass
class ProofSource:
    """Extracted proof link from forum."""
    problem_id: int
    url: str                    # GitHub/GitLab URL
    author: str | None          # Forum username (best-effort)
    posted_at: datetime | None  # Best-effort
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
    2. Run `lake build` (bounded time, bounded output)
    3. Stronger check (when possible): run `lake env lean --no-sorries` on the best-matching problem file
    4. Record verification strength + artifacts (toolchain, selected file)
    5. Return success/failure with logs
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
    """Best-effort record of an external proof repository + verification."""
    problem_id: int
    forum_thread_url: str
    extracted_at: datetime

    repo_url: str
    repo_commit: str | None

    posted_by: str | None
    posted_at: datetime | None

    verification_status: Literal[
        "unverified",
        "verified",
        "inconclusive",
        "failed",
        "source_unavailable",
    ]
    verification_strength: Literal["none", "build_only", "no_sorries"]  # see Verification section
    verification_error: str | None  # short, user-facing reason (e.g., "toolchain install failed")
    verified_at: datetime | None
    verification_command: str | None  # e.g., "lake build"
    toolchain: str | None             # raw `lean-toolchain` contents, when present
    verified_files: list[str]         # paths that were checked (best-effort)
    log_path: str | None              # path under data/sync_cache/...
```

### Storage Layout

```text
data/sync_cache/proofs/
  <problem_id>/
    links.json            # Extracted forum links (discover-only)
    provenance.json       # Selected repo + verification metadata
    verify.log            # Captured stdout/stderr from `lake build` (when verified)
    repos/                # Optional clone cache (implementation detail; gitignored)
```

`provenance.json` example:

```json
{
  "problem_id": 347,
  "forum_thread_url": "https://www.erdosproblems.com/forum/thread/347",
  "extracted_at": "2026-01-23T15:30:00Z",
  "repo_url": "https://github.com/ebarschkis/erdos-347-proof",
  "repo_commit": "abc123def456",
  "posted_by": "forum_user",
  "posted_at": "2026-01-21T21:37:00Z",
  "verification_status": "verified",
  "verified_at": "2026-01-23T15:30:00Z"
}
```

---

## Caching Strategy

```text
data/sync_cache/
  submodule_status.json     # Last sync time, commit hash
  website/
    <problem_id>.html       # Cached problem page HTML (optional)
  proofs/
    <problem_id>/
      links.json            # Extracted proof links
      provenance.json       # Selected repo + verification metadata
      verify.log            # Captured stdout/stderr from `lake build` (when verified)
```

Note: DeepMind statement caching already exists via SPEC-016 (`formal/lean/.upstream_cache/...`) and should be reused.

---

## Configuration

```bash
# .env
ERDOS_DATA_PATH=...                  # Optional: directory containing problems_enriched.yaml
```

Note: v3.2 sync is CLI-driven. There is no background daemon/auto-sync process in this spec.

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Submodule fetch fails | Warn, continue with cached data |
| Submodule not initialized / missing git | Fail with clear setup instructions |
| Website HTTP error (403/404/429/5xx) | Warn, keep existing `data/problems_enriched.yaml` fields untouched; record status code in sync cache |
| Website HTML parse fails (structure changed) | Warn, keep existing `data/problems_enriched.yaml` fields untouched; record failure + HTML snapshot in sync cache |
| No proof link found | Log as "no proof available yet" |
| Proof link broken (404) | Mark as "source_unavailable" |
| Lean compilation fails | Mark `verification_status=\"failed\"`, store logs |
| Multiple proof links | Record all links; `--verify` tries each deterministically and keeps the first that reaches `verification_strength=no_sorries` |
| Verification toolchain missing | Mark failed with actionable instructions (and never auto-install toolchains by default) |

---

## Verification Semantics (What “Verified” Means)

`lake build` is necessary but not sufficient: Lean can compile with `sorry` (warnings), and a repository may build without proving the specific problem.

This spec defines two verification strengths:

- `build_only`: repository builds successfully (`lake build`).
- `no_sorries`: we successfully identify a problem-relevant Lean file and run `lake env lean --no-sorries` on it (or an equivalent no-sorry check).

`verification_status="verified"` MUST imply `verification_strength="no_sorries"`.

If we can only reach `build_only` (i.e., `lake build` succeeds but we cannot prove “no sorries for the right file”), we record:

- `verification_status="inconclusive"`
- `verification_strength="build_only"`
- `verification_error` explaining the limiting factor (e.g., “could not identify problem file”, “toolchain install failed”, “no-sorries check unsupported”)

`verification_status="unverified"` is reserved for “verification was not attempted”.

---

## Security Considerations (Untrusted Code Execution)

Verifying third-party repos is inherently risky because `lake build` executes repo-provided build configuration.

Minimum guardrails (MUST):

1. `--verify` is explicit and prints a warning before doing anything.
2. Verification runs in a temp directory and never modifies the working tree.
3. Verification sanitizes the environment:
   - do not pass API keys / tokens into the child process environment,
   - record only bounded logs (truncate stdout/stderr).
4. Verification never runs git hooks and does not update submodules recursively.

Recommended guardrails (SHOULD):

- Add an optional “sandboxed verification” mode (e.g., Docker) that disables network access.
- Maintain an allowlist of repo hosts and optionally an allowlist of orgs/users.

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

### Deterministic Offline Tests (Required)

To keep CI reliable, the core of this spec should be testable without network:

- Website parsing uses committed HTML fixtures under `tests/fixtures/sync/website/*.html`.
- Forum parsing uses committed HTML fixtures under `tests/fixtures/sync/forum/*.html`.
- Proof verification uses a tiny local fixture repo under `tests/fixtures/sync/proof_repo/` that:
  - contains a minimal Lean project,
  - includes one file with `sorry` (must fail `no_sorries` verification),
  - includes one file without `sorry` (must pass).

---

## Acceptance Criteria

1. [ ] `erdos sync submodule` updates `data/erdosproblems` (or fails with a clear `requires_network` error when offline)
2. [ ] `erdos sync submodule --check` warns/fails if the submodule is stale (CI-friendly)
3. [ ] `erdos sync website <id>` updates/creates a valid `data/problems_enriched.yaml` entry (ProblemLoader schema: `id,title,statement,status,prize,tags,references,oeis_ids,notes,formalized`)
4. [ ] `erdos sync website <id> --latex` saves raw LaTeX source to `data/latex/<id>.tex` (gitignored)
5. [ ] `erdos sync statements <id>` delegates to `erdos lean import <id>` (SPEC-016) without duplicating the import/cache logic
6. [ ] `erdos sync proof <id>` extracts proof repo links from the forum thread and writes `data/sync_cache/proofs/<id>/links.json` + `provenance.json`
7. [ ] `erdos sync proof <id> --verify` runs `lake build` with timeouts and updates `verification_status` + `verify.log`
8. [ ] `erdos sync all` orchestrates submodule + website + proofs (+ optional statements) deterministically
9. [ ] Offline-friendly: cached data is used when network is unavailable; sync steps degrade gracefully with warnings

---

## Website Data Extraction (Beyond Forum)

The erdosproblems.com **main pages** (not just forum) have structured data we should extract:

### Available Data per Problem Page

| Field | URL Pattern | Value |
|-------|-------------|-------|
| Status badge | `erdosproblems.com/{id}` | "PROVED (LEAN)", "OPEN", etc. |
| Problem statement | Same page | Full statement with LaTeX math |
| LaTeX source | "View the LaTeX source" link | Raw `.tex` for formalization |
| Tags | Same page | "number theory \| covering systems" |
| References | `[Er65]`, `[ErGr80]` | Links to original Erdős papers |
| Formalized? | "Formalized statement? Yes/No" | DeepMind formalization flag |
| Difficulty | Community votes | "This problem looks difficult" |
| Collaborators | Community list | Who's working on it |

### Extraction Strategy

```python
# src/erdos/core/sync/website.py

@dataclass
class WebsiteProblemData:
    """Structured data from erdosproblems.com main page."""
    problem_id: int
    title: str
    statement: str
    tags: list[str]
    references: list[dict[str, str | None]]  # key/citation/doi/arxiv_id/url shape
    status_badge_text: str | None            # best-effort (for cross-check only)
    latex_source: str | None                 # saved separately (data/latex/<id>.tex)

def fetch_problem_page(problem_id: int) -> WebsiteProblemData:
    """
    Fetch and parse a single problem page.

    URL: https://www.erdosproblems.com/{problem_id}

    Strategy:
    1. HTTP GET the main page
    2. Extract title + statement from stable containers
    3. Parse tags + references into ProblemRecord-compatible shapes
    4. (Optional) Follow "View LaTeX source" link and save `data/latex/<id>.tex`
    5. Return structured data
    """
    ...
```

### CLI Commands for Website Sync

```bash
# Fetch structured data from website for a problem
erdos sync website <problem_id>

# Batch sync all problems (with rate limiting)
# Output example:
# Problem #275:
#   Status: PROVED (LEAN)
#   Tags: number theory, covering systems
#   References: Er65, Er65b, ErGr80
#   Formalized: Yes
#   LaTeX source: Saved to data/latex/275.tex
```

### Integration with Local Cache

Website data enriches `problems_enriched.yaml`:

```yaml
- id: 275
  title: "..."                       # From website
  statement: "If a finite..."        # From website
  status: proved                     # From submodule (normalized)
  prize: 0                           # From submodule
  tags: ["number theory", "covering systems"]
  references:
    - key: Er65
      citation: null
      doi: null
      arxiv_id: null
      url: "https://www.erdosproblems.com/..."   # From website
  oeis_ids: []
  notes: null
  formalized: true                   # From submodule
```

Note: raw LaTeX (when fetched) is stored separately under `data/latex/<id>.tex` (gitignored).

### Rate Limiting for Website

```python
# Be polite to T. F. Bloom's server
WEBSITE_RATE_LIMIT = 2.0  # seconds between requests
MAX_CONCURRENT = 1        # Sequential only
```

---

## Future Enhancements

- **RSS feed** for forum updates (if available) — more efficient than polling
- **Contact T. F. Bloom** for structured data export, API, or webhook
- **CI integration** — Auto-sync on schedule, PR on new proofs
- **Notification** when a problem in your watchlist is solved
- **LaTeX → Lean pipeline** — Use extracted LaTeX as input to formalization

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
