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

## Upstream API Response Mocks (Pending Spec 010)

These fixtures are reserved for reference-ingestion tests and are not yet consumed by the v1 codebase.

- `crossref_responses/doi_10.1007_BF01940595.json`
- `crossref_responses/doi_not_found.json`
- `arxiv_responses/arxiv_2203.00001.xml`
- `arxiv_responses/arxiv_not_found.xml`
