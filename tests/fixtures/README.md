# Test Fixtures

This directory contains small, version-controlled fixtures used by the test suite.

## Problem YAML

- `sample_problems.yaml`: Enriched v1 problems used across unit/integration/E2E tests.
- `single_problem.yaml`: Minimal enriched problem list (1 entry).
- `invalid_problems.yaml`: Invalid YAML used to exercise loader validation paths.

## Lean Output Samples

- `lean_outputs/type_error.txt`: Sample `stderr` with multiple errors (used by `tests/unit/test_lean_runner.py`).
- `lean_outputs/sorry_warning.txt`: Sample `stderr` with a `sorry` warning (used by `tests/unit/test_lean_runner.py`).
- `lean_outputs/successful_compile.txt`: Sample *stdout* from a successful `lake build` (currently informational; not parsed by the error parser).

## Upstream API Response Mocks

These fixtures are consumed by unit tests to keep parsing behavior deterministic (no network required):

- `crossref_responses/doi_10.1007_BF01940595.json`
- `crossref_responses/doi_not_found.json`
- `arxiv_responses/arxiv_2203.00001.xml`
- `arxiv_responses/arxiv_not_found.xml`
- `exa_responses/search_sum_free_sets.json`
- `semantic_scholar_responses/paper_green_tao.json`
- `zbmath_responses/document_green_tao.json`

## Sync Fixtures (SPEC-035)

HTML fixtures used for deterministic parsing tests:

- `sync/website/*.html`: problem-page HTML snapshots
- `sync/forum/*.html`: forum-thread HTML snapshots

Local “toy repo” fixtures used to test proof verification behavior without cloning:

- `sync/proof_repo/no_sorry/`: minimal Lean project with no `sorry`
- `sync/proof_repo/with_sorry/`: minimal Lean project with a `sorry`

## External API Mocks (Inline)

Some clients still use inline sample JSON payloads in unit tests (mocked via `responses`):

- OpenAlex (`tests/unit/clients/test_openalex.py`)
