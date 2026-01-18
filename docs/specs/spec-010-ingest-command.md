# Spec 010: Ingest Command (Literature Metadata + Cache)

> Adds `erdos ingest` to fetch and cache reference metadata/content for Erdős problems in a reproducible, testable way.

**Status:** Pending  
**Target:** v1.1  
**Prerequisites (SSOT):**
- Problem loading: `docs/_archive/specs/spec-005-problem-loader.md`
- Domain models: `docs/_archive/specs/spec-003-domain-models.md`
- CLI patterns: `docs/_archive/specs/spec-004-cli-architecture.md`
- Fixture corpus: `docs/_archive/specs/spec-008-test-fixtures.md`

---

## 0) Scope (Measure 3x)

### In scope (v1.1)

1. **arXiv references** (identified by `ReferenceEntry.arxiv_id`)
   - Fetch metadata via the arXiv export API (Atom XML)
   - Download source tarball (`.tar.gz`) from arXiv for local cache
   - Extract a lightweight plain-text representation for later indexing (best-effort)
2. **DOI references** (identified by `ReferenceEntry.doi`)
   - Fetch metadata via Crossref REST API
   - **No full-text download** (content is often paywalled; ingestion is metadata-only)

### Explicitly out of scope (v1.1)

- Unpaywall / OA detection for DOI content (defer to a future spec)
- PDF downloading or PDF-to-text conversion
- Citation-only reference resolution (no DOI + no arXiv ID) beyond “skip with reason”
- Automatic search-index updates (this spec writes cache/extracts; indexing is handled separately)

---

## 1) CLI Interface

### Command signature

```text
erdos ingest PROBLEM_ID [OPTIONS]
```

**Arguments**

- `PROBLEM_ID` (int, required): Erdős problem id.

**Options**

- `--force, -f`: Re-fetch and re-write manifest entries (even if already cached).
- `--no-download`: Fetch metadata only; do not download arXiv source tarballs.
- `--no-network`: Fail if any network access would be required. If an on-disk manifest already exists and `--force` is not set, the command may return that manifest without network access.
- `--timeout SECONDS`: HTTP timeout (default: `30`).
- `--delay SECONDS`: Minimum delay between API requests for politeness (default: `3`).
- `--mailto EMAIL`: Contact email for Crossref polite pool (default: from `ERDOS_MAILTO`, else a documented placeholder).

**Global flags**

- `--json` is a **global** flag (see `src/erdos/cli.py`) and must be supported.
- `--log-level` is a **global** flag.

### Examples

```bash
# Ingest problem 6 references (arXiv + Crossref metadata)
uv run erdos ingest 6

# Metadata-only (no source downloads)
uv run erdos ingest 6 --no-download

# Idempotent: returns existing manifest without network calls
uv run erdos ingest 6 --no-network

# Force re-fetch
uv run erdos ingest 6 --force
```

---

## 2) Data Layout (File/Folder SSOT)

This spec uses paths consistent with existing `.gitignore`:

- **Version controlled**
  - `literature/manifests/####.yaml` (safe: metadata + cache references only)
- **Gitignored**
  - `literature/cache/` (downloaded tarballs / derived assets)
  - `literature/extracts/` (derived text extracts)

### Canonical paths

- Manifest path: `literature/manifests/{problem_id:04d}.yaml`
- arXiv source cache path: `literature/cache/arxiv/{arxiv_id}/source.tar.gz`
- arXiv extracted text path: `literature/extracts/arxiv/{arxiv_id}/fulltext.txt`

**Rule:** Cache and extract paths stored in manifests must be **relative paths** rooted at repo root, so manifests are portable across machines.

---

## 3) Models (SSOT)

This spec does **not** introduce new Pydantic models for ingestion.

Use these existing models from `src/erdos/core/models.py` (archived Spec 003):

- `ReferenceEntry` (input, from `ProblemRecord.references`)
- `ReferenceRecord` (enriched metadata)
- `ManifestEntry` (reference + local cache state)
- `ProblemManifest` (collection written to `literature/manifests/####.yaml`)
- `CLIOutput` (command output wrapper)

---

## 4) External APIs (Verified)

### arXiv export API (metadata)

- Endpoint: `https://export.arxiv.org/api/query`
- Use `id_list=<id_without_version>` for a single id.
- Politeness guidance: incorporate a 3-second delay when calling repeatedly.

Reference: `https://info.arxiv.org/help/api/user-manual.html`

### arXiv source tarballs (content)

- Source download endpoints (all return `application/gzip` tarballs):
  - `https://arxiv.org/e-print/<arxiv_id>`
  - `https://arxiv.org/src/<arxiv_id>` (equivalent)

Verified via HTTP HEAD requests against `2203.00001` (2026-01-18).

### Crossref REST API (metadata)

- Base URL: `https://api.crossref.org/works`
- Retrieve by DOI: `GET /works/<doi>`
- “Polite pool”: include `mailto=<email>` as a query parameter and provide a clear User-Agent.

Reference: `https://www.crossref.org/documentation/retrieve-metadata/rest-api/`

---

## 5) Core Implementation (Modules to Create)

This spec keeps the current v1 structure (`src/erdos/core`, `src/erdos/commands`) and does not require Spec 009.

### 5.1 `src/erdos/core/ingest.py`

Responsibilities:

- Load `ProblemRecord` via `ProblemLoader.from_default()` + `get_by_id()`
- Iterate `problem.references`
- For each reference:
  - If `arxiv_id` → fetch arXiv metadata + optionally download source tarball + compute hash + write extract
  - Else if `doi` → fetch Crossref metadata only
  - Else → record “skipped (no identifier)” in CLI output (no manifest entry in v1.1)
- Read/merge existing manifest if present (idempotent):
  - if an entry already exists and `--force` is false, keep existing cache paths + hashes
  - if `--force`, overwrite cached state for that reference
- Write updated manifest to `literature/manifests/{problem_id:04d}.yaml`
- Return `CLIOutput.ok(...)` with a summary payload and manifest path

### 5.2 `src/erdos/core/arxiv_client.py`

Responsibilities:

- Fetch metadata via export API and map to `ReferenceRecord`:
  - `ReferenceRecord(arxiv_id=..., title=..., authors=[...], year=..., source="arxiv")`
  - Set `oa_status=OpenAccessStatus.GREEN` and `oa_url=https://arxiv.org/abs/<id>`
- Download source tarball via `https://arxiv.org/e-print/<arxiv_id>` into deterministic cache path.

### 5.3 `src/erdos/core/crossref_client.py`

Responsibilities:

- Fetch metadata by DOI and map to `ReferenceRecord`:
  - Must supply non-empty `title` (required by `ReferenceRecord`)
  - Map authors to a list of display strings
  - Set `source="crossref"`
- Use `mailto=` query parameter (polite pool) and a descriptive User-Agent.

### 5.4 `src/erdos/core/literature_paths.py`

Responsibilities:

- Centralize all path conventions (manifest/cache/extract) so the rest of the code doesn’t hardcode strings.

---

## 6) Command Implementation

### `src/erdos/commands/ingest.py`

Follow the command-module pattern from archived Spec 004:

1. Parse arguments/options.
2. Call a pure-ish core function (e.g., `ingest_problem_references(...) -> CLIOutput`).
3. Print via the shared presenter helpers (`exit_with_result` from `erdos.commands.presenter`).
4. Exit codes:
   - Not found problem id → `ExitCode.NOT_FOUND`
   - Network disabled but required → `ExitCode.NETWORK_ERROR`
   - Other errors → `ExitCode.ERROR`

---

## 7) Verification: This Spec is Testable

### Unit tests (no network)

Create tests that use fixtures from `tests/fixtures/` (Spec 008):

- `tests/unit/test_arxiv_client.py`
  - Parse `tests/fixtures/arxiv_responses/arxiv_2203.00001.xml`
  - Handle not-found `tests/fixtures/arxiv_responses/arxiv_not_found.xml`
- `tests/unit/test_crossref_client.py`
  - Parse `tests/fixtures/crossref_responses/doi_10.1007_BF01940595.json`
  - Handle not-found `tests/fixtures/crossref_responses/doi_not_found.json`
- `tests/unit/test_ingest_service.py`
  - Builds a manifest for a problem containing both DOI + arXiv refs (use `tests/fixtures/sample_problems.yaml`)
  - Asserts `--no-download` avoids writing cache files
  - Asserts `--no-network` returns existing manifest when present

### Integration tests (still no network)

- `tests/integration/test_cli_ingest.py`
  - Use `typer.testing.CliRunner`
  - Run `erdos ingest 6 --no-download --json`
  - Assert stdout is valid JSON (`CLIOutput`) and does not include progress text

### Acceptance criteria

```bash
uv run ruff check .
uv run mypy src/
uv run pytest -m "not requires_lean and not requires_network"
uv run pytest --cov=erdos --cov-fail-under=80 -m "not requires_lean and not requires_network"
```

---

## 8) Error Handling (Non-negotiable)

- Never print human text to stdout when `--json` is enabled.
- Network failures must be surfaced as a structured `CLIOutput.err(...)` with an actionable message.
- A single reference failure must not abort ingestion of other references unless it’s a fatal configuration error (e.g., invalid manifest path).

---

## References

- arXiv API user manual (politeness guidance): `https://info.arxiv.org/help/api/user-manual.html`
- Crossref REST API docs (polite pool): `https://www.crossref.org/documentation/retrieve-metadata/rest-api/`

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.2.0 | 2026-01-18 | Rewrite: align with v1 `src/erdos/core` structure and Spec 003 models; scope v1.1 to arXiv + Crossref metadata only |
