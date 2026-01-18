# Spec 008: Test Fixtures & Sample Data

> Defines the test fixtures, sample data files, and shared testing utilities that all specs depend on.

---

## Overview

Test fixtures are the foundation of our testing strategy. This spec defines:

1. Sample `problems.yaml` for testing without the full dataset
2. Recorded API responses for integration tests
3. Sample Lean files for compiler tests
4. Fixture file contents (pytest fixture *code* lives in Spec 002)

### Guiding Principles

1. **Self-contained** - Tests can run without external dependencies
2. **Realistic** - Sample data matches production format
3. **Minimal** - Only include data needed for tests
4. **Version-controlled** - All fixtures committed to git

---

## 1) Fixtures Directory Structure

```
tests/
├── __init__.py
├── conftest.py                    # Root fixtures (shared by all tests)
├── fixtures/
│   ├── __init__.py
│   ├── sample_problems.yaml       # Minimal problems dataset
│   ├── single_problem.yaml        # Single problem for unit tests
│   ├── invalid_problems.yaml      # Malformed YAML for error tests
│   ├── crossref_responses/
│   │   ├── doi_10.1007_BF01940595.json
│   │   └── doi_not_found.json
│   ├── arxiv_responses/
│   │   ├── arxiv_2203.00001.xml
│   │   └── arxiv_not_found.xml
│   └── lean_outputs/
│       ├── successful_compile.txt
│       ├── type_error.txt
│       └── sorry_warning.txt
├── unit/
│   ├── __init__.py
│   └── conftest.py                # Unit test specific fixtures
├── integration/
│   ├── __init__.py
│   └── conftest.py                # Integration test specific fixtures
└── e2e/
    ├── __init__.py
    └── conftest.py                # E2E test specific fixtures
```

---

## 2) Sample Problems YAML

**Note:** Test fixtures use the **enriched format** (with `id`, `title`, `statement`) as defined in Spec 005, not the upstream teorth/erdosproblems metadata-only format. This allows testing the full ProblemLoader and CLI functionality without scraping external sources.

```yaml
# tests/fixtures/sample_problems.yaml
# Minimal dataset with representative problems for testing
# Uses enriched format (see Spec 005 for format details)

- id: 1
  title: "Sum of reciprocals of primes"
  statement: |
    Prove that the sum of the reciprocals of the primes diverges:
    $$\sum_{p \text{ prime}} \frac{1}{p} = \infty$$
  status: proved
  prize: 0
  tags:
    - number theory
    - primes
  references:
    - key: Euler1737
      citation: "L. Euler, Variae observationes circa series infinitas, 1737"
  notes: "Classic result by Euler."
  oeis_ids:
    - A000040
  formalized: false

- id: 6
  title: "Small primes in arithmetic progressions"
  statement: |
    Let $p_1 < p_2 < \ldots$ be the sequence of primes.
    For every positive integer $k$, prove there exist infinitely many
    arithmetic progressions of length $k$ consisting entirely of primes.
  status: proved
  prize: 100
  tags:
    - number theory
    - primes
    - arithmetic progressions
  references:
    - key: GreenTao2008
      citation: "B. Green, T. Tao, The primes contain arbitrarily long arithmetic progressions, Ann. of Math. 167 (2008), 481–547"
      doi: "10.4007/annals.2008.167.481"
      arxiv_id: "math/0404188"
  notes: "Solved by Green and Tao in 2004, published 2008."
  oeis_ids: []
  formalized: true

- id: 42
  title: "A test open problem"
  statement: |
    This is a test problem statement for an open problem.
    It contains some mathematical notation: $n^2 + 1$.
  status: open
  prize: 500
  tags:
    - number theory
    - test
  references: []
  notes: null
  oeis_ids: []
  formalized: false

- id: 100
  title: "Graph coloring conjecture"
  statement: |
    Every planar graph with girth at least 5 is 3-colorable.
  status: open
  prize: 0
  tags:
    - graph theory
    - coloring
  references:
    - key: Erdos1959
      citation: "P. Erdős, Graph theory and probability, 1959"
  notes: null
  oeis_ids: []
  formalized: false

- id: 316
  title: "Covering systems counterexample"
  statement: |
    Does there exist a covering system with all moduli distinct and greater than 10?
  status: disproved
  prize: 0
  tags:
    - combinatorics
    - covering systems
  references:
    - key: Hough2015
      citation: "B. Hough, Solution of the minimum modulus problem for covering systems, Ann. of Math. 181 (2015), 361–382"
      doi: "10.4007/annals.2015.181.1.6"
  notes: "Disproved by Hough in 2015."
  oeis_ids: []
  formalized: false

- id: 999
  title: "Partially solved problem"
  statement: |
    A problem that has been partially resolved.
  status: partially_solved
  prize: 250
  tags:
    - number theory
  references: []
  notes: "Partial progress made in several papers."
  oeis_ids: []
  formalized: false
```

---

## 3) Single Problem YAML

```yaml
# tests/fixtures/single_problem.yaml
# Minimal single problem for simple unit tests

- id: 6
  title: "Small primes in arithmetic progressions"
  statement: "Prove that for every k, there exist infinitely many arithmetic progressions of length k consisting of primes."
  status: proved
  prize: 100
  tags:
    - number theory
  references: []
```

---

## 4) Invalid Problems YAML

```yaml
# tests/fixtures/invalid_problems.yaml
# Intentionally malformed for error testing

- id: "not a number"  # Should be int
  title: "Bad problem"
  statement: "Test"
  status: open

- title: "Missing ID"  # No id field
  statement: "Test"
  status: open

- id: 1
  # Missing title
  statement: "Test"
  status: open

- id: 2
  title: "Bad status"
  statement: "Test"
  status: "invalid_status"  # Not a valid status
```

---

## 5) Recorded API Responses

### Crossref Response

```json
// tests/fixtures/crossref_responses/doi_10.1007_BF01940595.json
{
  "status": "ok",
  "message-type": "work",
  "message": {
    "DOI": "10.1007/BF01940595",
    "title": ["Some problems on number theory"],
    "author": [
      {"given": "Paul", "family": "Erdős"}
    ],
    "published-print": {"date-parts": [[1975]]},
    "container-title": ["Journal of Number Theory"],
    "type": "journal-article",
    "URL": "https://doi.org/10.1007/BF01940595"
  }
}
```

### Crossref Not Found

```json
// tests/fixtures/crossref_responses/doi_not_found.json
{
  "status": "error",
  "message-type": "error",
  "message": "Resource not found."
}
```

### ArXiv Response

```xml
<!-- tests/fixtures/arxiv_responses/arxiv_2203.00001.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2203.00001v1</id>
    <title>Sample ArXiv Paper Title</title>
    <summary>This is the abstract of the paper.</summary>
    <author>
      <name>Test Author</name>
    </author>
    <published>2022-03-01T00:00:00Z</published>
    <link href="http://arxiv.org/abs/2203.00001v1" rel="alternate" type="text/html"/>
    <link href="http://arxiv.org/pdf/2203.00001v1" title="pdf" rel="related" type="application/pdf"/>
  </entry>
</feed>
```

---

## 6) Lean Output Samples

### Successful Compile

```text
# tests/fixtures/lean_outputs/successful_compile.txt
Build completed successfully.
```

### Type Error

```text
# tests/fixtures/lean_outputs/type_error.txt
Erdos/Problem006.lean:12:5: error: type mismatch
  rfl
has type
  ?m = ?m
but is expected to have type
  1 = 2
Erdos/Problem006.lean:15:10: error: unknown identifier 'Nat.prime'
```

### Sorry Warning

```text
# tests/fixtures/lean_outputs/sorry_warning.txt
Erdos/Problem006.lean:20:2: warning: declaration uses 'sorry'
```

---

## 7) Pytest Fixture Code

**Single source of truth:** Pytest fixture code is defined in **Spec 002** and implemented in:

- `tests/conftest.py`
- `tests/unit/conftest.py`
- `tests/integration/conftest.py`
- `tests/e2e/conftest.py`

This spec only owns the fixture *files* under `tests/fixtures/`.

---

## 8) Test Harness Coverage

Fixture files here are consumed by tests defined in Spec 002 (and feature specs),
including CLI E2E tests and Lean parsing tests.

## 11) Verification: This Spec is Testable

### Setup Verification

```bash
# 1. Fixtures directory exists
ls tests/fixtures/
# Should show: sample_problems.yaml, crossref_responses/, etc.

# 2. YAML fixtures are valid
uv run python -c "
import yaml
from pathlib import Path
yaml_path = Path('tests/fixtures/sample_problems.yaml')
data = yaml.safe_load(yaml_path.read_text())
print(f'Loaded {len(data)} problems')
"

# 3. JSON fixtures are valid
uv run python -c "
import json
from pathlib import Path
json_path = Path('tests/fixtures/crossref_responses/doi_10.1007_BF01940595.json')
data = json.loads(json_path.read_text())
print(f'Loaded DOI: {data[\"message\"][\"DOI\"]}')
"

# 4. Fixtures are importable in tests
uv run python -c "
import pytest
from tests.conftest import sample_problem
# Should not raise
print('Fixtures importable')
"
```

### Test Meta-Test

```python
# tests/test_fixtures.py
"""Verify test fixtures are correctly set up."""

from pathlib import Path

import pytest
import yaml


class TestFixturesExist:
    def test_fixtures_dir_exists(self, fixtures_dir: Path) -> None:
        """Fixtures directory should exist."""
        assert fixtures_dir.exists()
        assert fixtures_dir.is_dir()

    def test_sample_problems_yaml_exists(self, sample_problems_yaml: Path) -> None:
        """Sample problems YAML should exist."""
        assert sample_problems_yaml.exists()

    def test_sample_problems_yaml_valid(self, sample_problems_yaml: Path) -> None:
        """Sample problems YAML should be valid."""
        data = yaml.safe_load(sample_problems_yaml.read_text())
        assert isinstance(data, list)
        assert len(data) > 0

    def test_crossref_fixtures_exist(self, fixtures_dir: Path) -> None:
        """Crossref response fixtures should exist."""
        crossref_dir = fixtures_dir / "crossref_responses"
        assert crossref_dir.exists()
        assert (crossref_dir / "doi_10.1007_BF01940595.json").exists()

    def test_lean_fixtures_exist(self, fixtures_dir: Path) -> None:
        """Lean output fixtures should exist."""
        lean_dir = fixtures_dir / "lean_outputs"
        assert lean_dir.exists()
        assert (lean_dir / "type_error.txt").exists()


class TestFixturesContent:
    def test_sample_problem_fixture(self, sample_problem) -> None:
        """sample_problem fixture should have expected fields."""
        assert sample_problem.id == 6
        assert sample_problem.status.value == "proved"
        assert len(sample_problem.tags) > 0

    def test_open_problem_fixture(self, open_problem) -> None:
        """open_problem fixture should be open."""
        assert open_problem.status.value == "open"

    def test_crossref_response_fixture(self, crossref_response: dict) -> None:
        """crossref_response fixture should have expected structure."""
        assert crossref_response["status"] == "ok"
        assert "message" in crossref_response
        assert "DOI" in crossref_response["message"]

    def test_lean_error_output_fixture(self, lean_error_output: str) -> None:
        """lean_error_output fixture should contain error pattern."""
        assert "error:" in lean_error_output
        assert ".lean:" in lean_error_output


class TestTempDirectoryFixtures:
    def test_temp_project_dir_structure(self, temp_project_dir: Path) -> None:
        """temp_project_dir should have expected structure."""
        assert (temp_project_dir / "data" / "erdosproblems" / "data").exists()
        assert (temp_project_dir / "formal" / "lean" / "Erdos").exists()
        assert (temp_project_dir / "index").exists()

    def test_in_memory_db_works(self, in_memory_db) -> None:
        """in_memory_db fixture should provide working connection."""
        cursor = in_memory_db.execute("SELECT 1 as test")
        row = cursor.fetchone()
        assert row["test"] == 1
```

---

## 12) Usage Examples

### Using Fixtures in Unit Tests

```python
# tests/unit/test_example.py

def test_using_sample_problem(sample_problem):
    """Example using sample_problem fixture."""
    assert sample_problem.id == 6


def test_using_fixtures_dir(fixtures_dir):
    """Example using fixtures_dir fixture."""
    sample_file = fixtures_dir / "sample_problems.yaml"
    assert sample_file.exists()
```

### Using Fixtures in Integration Tests

```python
# tests/integration/test_example.py

def test_with_loader(problem_loader):
    """Example using problem_loader fixture."""
    problems = problem_loader.load_all()
    assert len(problems) > 0


def test_with_index(populated_index):
    """Example using populated_index fixture."""
    results = populated_index.search("prime")
    # Results depend on sample data
```

### Using Fixtures in E2E Tests

```python
# tests/e2e/test_example.py

@pytest.mark.e2e
def test_cli_list(cli_runner):
    """Example using cli_runner fixture."""
    result = cli_runner("list", "--limit", "5")
    assert result.returncode == 0


@pytest.mark.e2e
def test_cli_show(cli_runner):
    """Example using cli_runner fixture."""
    result = cli_runner("show", "6", "--json")
    assert '"id": 6' in result.stdout
```

---

## 13) References

- [pytest Fixtures](https://docs.pytest.org/en/stable/explanation/fixtures.html)
- [pytest conftest.py](https://docs.pytest.org/en/stable/reference/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files)
- [pytest tmp_path](https://docs.pytest.org/en/stable/how-to/tmp_path.html)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-16 | Initial spec |
