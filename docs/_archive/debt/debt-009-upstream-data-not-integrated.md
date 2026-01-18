# DEBT-009: teorth/erdosproblems Never Integrated

**Priority:** P1
**Status:** Fixed
**Found:** 2026-01-18
**Fixed:** 2026-01-18
**Commit:** 70ae1ab,96eb024
**Affects:** Data loading, schema validation, real-world usability

## Resolution

- Added the upstream `teorth/erdosproblems` repository as a git submodule at `data/erdosproblems/`.
- Added a schema smoke test that loads `data/erdosproblems/data/problems.yaml` to catch upstream structural changes.
- Added `data/README.md` explaining the relationship between the upstream metadata-only dataset and the local enriched v1 dataset.

## Problem (before fix)

The actual upstream data source (`teorth/erdosproblems`) has never been integrated:
- `data/erdosproblems/` doesn't exist
- No git submodule is configured
- No test fetches or parses real problem data
- We don't know if our YAML schema matches theirs

The entire project is built around a 6-problem test fixture that may not reflect the real dataset's structure.

Additionally, the current `ProblemLoader` explicitly rejects the upstream metadata-only YAML format, so integrating the upstream repository requires an ingest/enrichment step (or a deliberate change in the loader contract).

## Evidence (before fix)

**Missing data directory:**
```bash
$ ls data/erdosproblems/
ls: data/erdosproblems/: No such file or directory
```

**CI checks out submodules recursively (`.github/workflows/ci.yml:22-24`):**
```yaml
      - uses: actions/checkout@v6
        with:
          submodules: recursive
```

**No .gitmodules file:**
```bash
$ cat .gitmodules
cat: .gitmodules: No such file or directory
```

**Test fixture vs reality:**
- Fixture: 6 problems in `tests/fixtures/sample_problems.yaml`
- Reality: upstream is orders of magnitude larger than the fixture (exact count not verified here)
- Schema may have diverged (extra fields, different formats)

**ProblemLoader fallback chain does not validate real upstream data:**
`ProblemLoader.from_default()` includes a fallback for `./data/erdosproblems/data/problems.yaml`, but this is only unit-tested using fixture YAML (and the loader currently rejects the real upstream metadata-only schema).

## Risk

1. **Schema mismatch:** Real problems might have fields we don't parse
2. **Scale issues:** 6 problems work, larger datasets might not (memory, indexing time)
3. **Data format drift:** Upstream could change format without us knowing
4. **First-user failure:** Real user clones repo, data doesn't exist

## Proposed Resolution

1. **Add git submodule:**
   ```bash
   git submodule add https://github.com/teorth/erdosproblems data/erdosproblems
   ```

2. **Add schema validation test:**
   ```python
   from pathlib import Path
   from erdos.core.problem_loader import ProblemLoader

   def test_real_data_parses():
       """
       All problems from the upstream snapshot parse without error.

       Note: this requires an ingest/enrichment step to produce enriched v1 YAML
       (the current loader rejects metadata-only upstream YAML).
       """
       loader = ProblemLoader(Path("data/problems_enriched.yaml"))
       problems = loader.load_all()
       assert len(problems) > 100  # Sanity check
   ```

3. **Add CI step to update submodule:**
   - Periodic job to fetch latest upstream
   - Fail if schema changes break parsing

4. **Document the data source:**
   - Add `data/README.md` explaining the source
   - Link to upstream repository

## Acceptance Criteria

- [ ] `data/erdosproblems/` exists as git submodule
- [ ] `.gitmodules` file configured correctly
- [ ] At least one test loads real problem data (not fixture)
- [ ] CI fetches and tests against real data
- [ ] Schema validation catches field mismatches
- [ ] Documentation explains data source and update process
