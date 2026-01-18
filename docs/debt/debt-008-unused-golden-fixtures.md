# DEBT-008: Unused Fixtures - No Golden File Testing

**Priority:** P2
**Status:** Open
**Found:** 2026-01-18
**Affects:** Test coverage, regression detection, output stability

## Problem

Several fixture directories exist but are **never used** in any test:
- `tests/fixtures/arxiv_responses/` - API response mocks, unused
- `tests/fixtures/crossref_responses/` - API response mocks, unused
- `tests/fixtures/lean_outputs/` - Compiler output samples, unused

Additionally, there are no "golden file" tests that compare actual output against known-good baselines. This means:
- Output format could silently change
- API response parsing could regress
- Lean output interpretation could break

## Evidence

**Unused fixture directories:**
```
tests/fixtures/arxiv_responses/arxiv_2203.00001.xml
tests/fixtures/arxiv_responses/arxiv_not_found.xml
tests/fixtures/crossref_responses/doi_10.1007_BF01940595.json
tests/fixtures/crossref_responses/doi_not_found.json
tests/fixtures/lean_outputs/sorry_warning.txt
tests/fixtures/lean_outputs/successful_compile.txt
tests/fixtures/lean_outputs/type_error.txt
```

**Grep for usage:**
```bash
$ grep -r "arxiv_responses\|crossref_responses\|lean_outputs" tests/
# (no output - none of these are imported or referenced)
```

**Missing golden comparisons:**
- No snapshot of expected SQLite schema
- No snapshot of expected CLI output format
- No snapshot of expected Lean skeleton

## Risk

1. **Silent regressions:** Output format could change without any test failing
2. **Dead code:** Fixtures were created but feature was never completed
3. **Wasted effort:** Future developers might think these features work
4. **API drift:** When arxiv/crossref APIs change, we have no regression test

## Proposed Resolution

1. **Either use the fixtures or delete them:**
   - If reference ingestion (spec-010) is planned, write tests using these fixtures
   - If not planned for v1.x, delete to avoid confusion

2. **Add golden file testing:**
   ```python
   def test_cli_output_matches_golden(tmp_path, golden_output):
       result = runner.invoke(cli, ["list"])
       assert result.output == golden_output
   ```

3. **Document fixture purpose:**
   - Add `tests/fixtures/README.md` explaining what each fixture is for
   - Mark unused fixtures as "pending implementation"

## Acceptance Criteria

- [ ] Every fixture file is either used in a test OR documented as "pending"
- [ ] At least one golden file comparison test exists
- [ ] `tests/fixtures/README.md` documents the purpose of each fixture directory
- [ ] No orphaned fixture files (files that exist but serve no purpose)
