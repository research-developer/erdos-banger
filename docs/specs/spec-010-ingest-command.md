# Spec 010: Ingest Command (Literature Metadata + Cache)

> Adds `erdos ingest` to fetch and cache reference metadata/content for Erdős problems in a reproducible, testable way.

**Status:** Pending
**Target:** v1.1
**Prerequisites (SSOT):**
- Problem loading: `docs/_archive/specs/spec-005-problem-loader.md`
- Domain models: `docs/_archive/specs/spec-003-domain-models.md`
- CLI patterns: `docs/_archive/specs/spec-004-cli-architecture.md`
- Presenter utilities: `docs/_archive/specs/spec-009-architecture-cleanup.md`
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

### JSON Output Schema (SSOT)

All JSON output must be wrapped in `CLIOutput` (archived Spec 003).

On success (`success=true`), `CLIOutput.data` must include:

```json
{
  "problem_id": 6,
  "manifest_path": "literature/manifests/0006.yaml",
  "references_total": 2,
  "entries_written": 1,
  "skipped": 0,
  "manifest": {
    "schema_version": 1,
    "problem_id": 6,
    "entries": []
  }
}
```

Notes:
- `entries_written` is the number of `manifest.entries` written (which may be less than `references_total` because v1.1 skips references without DOI/arXiv ids).
- `manifest` must be `ProblemManifest.model_dump(mode="json")` so `Path` and `datetime` fields serialize deterministically.
- When `--json` is enabled, no progress/human text may be written to stdout.

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

**Serialization note (Pydantic SSOT):**
- `ManifestEntry.cache_path` and `ManifestEntry.extract_path` are `Path | None` in `src/erdos/core/models.py`.
- When writing YAML, dump using `ProblemManifest.model_dump(mode="json")` so `Path` values serialize as POSIX strings.
- Reject absolute paths at write time (treat as `ExitCode.CONFIG_ERROR`).

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

**Polite pool:** Crossref considers clients “polite” if they include contact info via either:
- a `mailto=` query parameter, or
- a `mailto:` entry in the `User-Agent` header.

Reference: `https://github.com/CrossRef/rest-api-doc` (API etiquette / polite pool).

---

## 5) Core Implementation (Modules to Create)

This spec keeps the current v1 structure (`src/erdos/core`, `src/erdos/commands`) and uses the shared presenter helpers from Spec 009 for output/exit behavior.

### 5.0 Dependencies (Explicit)

To keep HTTP behavior testable and consistent, v1.1 ingestion uses:

- Runtime dependency: `requests>=2.32.5`
- Test dependency (already present): `responses` for mocking `requests` calls

Rationale: unit/integration tests must be able to run with **zero network** and still exercise HTTP error paths deterministically.

### 5.1 `src/erdos/core/ingest.py`

Responsibilities:

- Load `ProblemRecord` via `ProblemLoader.from_default()` + `get_by_id()`
- Iterate `problem.references`
- For each reference:
  - If `doi` → fetch Crossref metadata. If `arxiv_id` is also present and downloads are enabled, download/extract the arXiv source tarball and attach it to the same manifest entry.
  - Else if `arxiv_id` → fetch arXiv metadata + optionally download source tarball + compute MD5 (`ManifestEntry.cache_hash`) + write extract
  - Else → record “skipped (no identifier)” in CLI output (no manifest entry in v1.1)
- **Reference identity and merging (non-negotiable):**
  - Each `ReferenceEntry` maps to **at most one** `ManifestEntry`.
  - If a `ReferenceEntry` has **both** `doi` and `arxiv_id`, treat it as **one** reference:
    - Fetch metadata via Crossref (DOI is authoritative for bibliographic metadata).
    - Set `ReferenceRecord.doi=<doi>` and `ReferenceRecord.arxiv_id=<arxiv_id>`.
    - If downloads are enabled, download/extract the arXiv tarball and attach the cache/extract state to the same `ManifestEntry`.
  - Manifest entry matching for idempotence uses this stable key:
    - Prefer DOI when present (`doi` lowercased).
    - Else use `arxiv_id` as written in the YAML (including version suffix if present).
  - If two references in the current YAML resolve to the same stable key (duplicate DOI/arXiv id), treat this as a fatal configuration error: return `CLIOutput.err(...)` with `error.type="ConfigError"` and `error.code=ExitCode.CONFIG_ERROR` (SSOT: `src/erdos/core/exit_codes.py`) and do not write/modify the manifest.
- Read/merge existing manifest if present (idempotent):
  - if an entry already exists and `--force` is false, keep existing cache paths + hashes **and do not re-fetch metadata**
  - if `--force`, overwrite cached state for that reference
- If the current problem YAML reference list removes a previously ingested reference, drop that entry from the rewritten manifest (cached files remain on disk; manifest reflects current YAML refs).
- Write updated manifest to `literature/manifests/{problem_id:04d}.yaml` **atomically** (write to a temp file in the same directory, then replace).
- Return:
  - `CLIOutput.ok(...)` when **all** references were processed without errors, or
  - `CLIOutput.err(...)` when **any** reference failed, but still write the manifest first.

For error returns, include structured details as extra keys under `CLIOutput.error` (allowed by `CLIOutput` invariants), e.g.:

```json
{
  "type": "NetworkError",
  "message": "1 reference failed (see manifest)",
  "code": 4,
  "manifest_path": "literature/manifests/0006.yaml",
  "references_processed": 3,
  "references_failed": 1
}
```

### 5.2 `src/erdos/core/arxiv_client.py`

Responsibilities:

- Provide **two-layer API** to keep tests network-free:
  - `fetch_arxiv_atom(arxiv_id: str, *, timeout: float) -> str`
  - `parse_arxiv_atom(xml_text: str) -> ReferenceRecord`

Mapping rules (in `parse_arxiv_atom`):

- Map to `ReferenceRecord`:
  - `ReferenceRecord(arxiv_id=..., title=..., authors=[...], year=..., source="arxiv")`
  - Set `oa_status=OpenAccessStatus.GREEN` and `oa_url=https://arxiv.org/abs/<id>`
- Download source tarball via `https://arxiv.org/e-print/<arxiv_id>` into deterministic cache path.
  - Strip any version suffix for export API queries (`2203.00001v1` → `2203.00001`) but preserve the versioned id for cache paths if present.

**Source extraction (best-effort, but specified):**

- If `--no-download` is set, skip download and extraction.
- If downloading succeeds, write `literature/extracts/arxiv/{arxiv_id}/fulltext.txt` using this deterministic heuristic:
  1. Extract the tarball to a temp directory.
  2. Collect `*.tex` files (recursively). If none exist, mark `ManifestEntry.extracted=false` and set `ManifestEntry.error`.
  3. Choose the **largest** `.tex` file by byte size as the “main” source file.
  4. Write its raw text to `fulltext.txt` (UTF-8 decode with `errors="replace"`), capped at 2 MiB.

Note: this is not “PDF-quality text”; it is an inexpensive searchable proxy for later indexing.

### 5.3 `src/erdos/core/crossref_client.py`

Responsibilities:

- Provide **two-layer API** to keep tests network-free:
  - `fetch_crossref_work(doi: str, *, mailto: str, timeout: float) -> dict[str, object]`
  - `parse_crossref_work(payload: dict[str, object], *, doi: str) -> ReferenceRecord`

Mapping rules (in `parse_crossref_work`):

- Map the Crossref JSON payload to `ReferenceRecord`:
  - Must supply non-empty `title` (required by `ReferenceRecord`)
  - Map authors to a list of display strings
  - Set `source="crossref"`

Note: The `mailto=` query parameter and User-Agent belong in `fetch_crossref_work`, not `parse_crossref_work`.

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
  - `parse_arxiv_atom` parses `tests/fixtures/arxiv_responses/arxiv_2203.00001.xml`
  - Not-found handling parses `tests/fixtures/arxiv_responses/arxiv_not_found.xml`
- `tests/unit/test_arxiv_extract.py`
  - Builds a tiny synthetic `tar.gz` with two `.tex` files and asserts the “largest .tex wins” heuristic and the 2 MiB cap.
- `tests/unit/test_crossref_client.py`
  - `parse_crossref_work` parses `tests/fixtures/crossref_responses/doi_10.1007_BF01940595.json` (fixture-shaped Crossref JSON)
  - Not-found handling parses `tests/fixtures/crossref_responses/doi_not_found.json`
- `tests/unit/test_ingest_service.py`
  - Builds a manifest for a problem containing both DOI + arXiv refs (use `tests/fixtures/sample_problems.yaml`)
  - Asserts `--no-download` avoids writing cache files
  - Asserts `--no-network` returns existing manifest when present
  - Asserts partial failure still writes a manifest file before returning `CLIOutput.err(...)` (e.g., Crossref 404 for one DOI while another ref succeeds)

**Mocking rule:** All HTTP fetch functions must be covered by tests using `responses` (no real network).

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
