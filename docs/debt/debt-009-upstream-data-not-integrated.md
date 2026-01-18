# DEBT-009: teorth/erdosproblems Never Integrated

**Priority:** P1
**Status:** Open
**Found:** 2026-01-18
**Affects:** Data loading, schema validation, real-world usability

## Problem

The actual upstream data source (`teorth/erdosproblems`) has never been integrated:
- `data/erdosproblems/` doesn't exist
- No git submodule is configured
- No test fetches or parses real problem data
- We don't know if our YAML schema matches theirs

The entire project is built around a 6-problem test fixture that may not reflect the real dataset's structure.

## Evidence

**Missing data directory:**
```bash
$ ls data/erdosproblems/
ls: data/erdosproblems/: No such file or directory
```

**CI claims to use submodules but none exist:**
```yaml
# .github/workflows/ci.yml:22-23
- uses: actions/checkout@v6
  with:
    submodules: recursive  # <-- but no .gitmodules file
```

**No .gitmodules file:**
```bash
$ cat .gitmodules
cat: .gitmodules: No such file or directory
```

**Test fixture vs reality:**
- Fixture: 6 problems in `tests/fixtures/sample_problems.yaml`
- Reality: teorth/erdosproblems has ~1000+ problems
- Schema may have diverged, extra fields, different formats

**ProblemLoader fallback chain assumes paths that don't exist:**
The loader likely has hardcoded paths that have never been tested with real data.

## Risk

1. **Schema mismatch:** Real problems might have fields we don't parse
2. **Scale issues:** 6 problems work, 1000 might not (memory, indexing time)
3. **Data format drift:** Upstream could change format without us knowing
4. **First-user failure:** Real user clones repo, data doesn't exist

## Proposed Resolution

1. **Add git submodule:**
   ```bash
   git submodule add https://github.com/teorth/erdosproblems data/erdosproblems
   ```

2. **Add schema validation test:**
   ```python
   def test_real_data_parses():
       """All problems from teorth/erdosproblems parse without error."""
       loader = ProblemLoader("data/erdosproblems")
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
