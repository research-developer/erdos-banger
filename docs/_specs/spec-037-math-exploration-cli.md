# SPEC-037: Math Exploration CLI

> CLI commands for computational exploration of Erdős problems using SymPy and NetworkX before formal Lean proof.

**Status:** Draft
**Target:** v4.3
**Prerequisites:**
- Issue #32: Math exploration & automation tools investigation
- `[explore]` extras already added (SymPy, NetworkX)

---

## 0) Motivation

Many Erdős problems benefit from computational exploration before formal proof:
- **Number theory**: Check small cases, find patterns in factorizations
- **Graph theory**: Compute chromatic numbers, find counterexamples
- **Combinatorics**: Enumerate structures, verify bounds

Currently, users must write Python scripts or use REPL. This spec adds CLI commands for common exploration patterns.

---

## 1) Scope

### In Scope (v4.3)

1. **`erdos explore <problem_id>`** - Problem-specific explorations
2. **`erdos explore number <n>`** - Number theory utilities (factorize, divisors, primes)
3. **`erdos explore graph <type>`** - Graph construction and analysis
4. **`erdos explore sequence <oeis>`** - OEIS sequence inspection
5. **JSON output** for automation

### Out of Scope

- SageMath integration (heavy dependency, future spec)
- Visualization commands (separate spec, needs graphviz/matplotlib)
- Jupyter notebook support (separate spec)
- Automated conjecture testing (requires problem-specific logic)

---

## 2) CLI Interface

### `erdos explore <problem_id>`

Run problem-specific explorations based on problem tags.

```bash
# Auto-detect exploration based on problem tags
erdos explore 848  # number theory → factorization patterns
erdos explore 67   # graph theory → chromatic computations

# Limit computation
erdos explore 848 --max-n 1000

# JSON output
erdos explore 848 --json
```

**Behavior:**
1. Load problem metadata (tags, statement)
2. Detect problem type from tags:
   - `number theory` → number-theoretic explorations
   - `graph theory` → graph-theoretic explorations
   - `combinatorics` → combinatorial explorations
3. Run appropriate exploration functions
4. Display patterns and small-case results

### `erdos explore number <n>`

Number theory utilities for manual exploration.

```bash
# Factorization
erdos explore number 12345 --factorize
# Output: 12345 = 3 × 5 × 823

# Divisors
erdos explore number 12345 --divisors
# Output: [1, 3, 5, 15, 823, 2469, 4115, 12345]

# Prime check
erdos explore number 12345 --is-prime
# Output: False

# Totient
erdos explore number 12345 --totient
# Output: φ(12345) = 6576

# All info
erdos explore number 12345 --all
erdos explore number 12345 --json
```

### `erdos explore primes`

Prime number utilities.

```bash
# List primes up to N
erdos explore primes --up-to 100

# Primes in range
erdos explore primes --range 100 200

# Nth prime
erdos explore primes --nth 100
# Output: p(100) = 541

# Prime gaps
erdos explore primes --gaps --up-to 1000

# Twin primes
erdos explore primes --twin --up-to 1000
```

### `erdos explore sequence <oeis_id>`

OEIS sequence inspection (requires network for lookup).

```bash
# Compute terms
erdos explore sequence A000040 --terms 20
# Output: 2, 3, 5, 7, 11, 13, 17, 19, 23, 29, ...

# Check if n is in sequence (for well-known sequences)
erdos explore sequence A000040 --contains 101

# Link to OEIS
erdos explore sequence A000040 --link
```

### `erdos explore graph <type>`

Graph construction and analysis.

```bash
# Complete graph chromatic number
erdos explore graph complete --n 5 --chromatic
# Output: χ(K₅) = 5

# Petersen graph properties
erdos explore graph petersen --all

# Random graph
erdos explore graph random --n 10 --p 0.5 --chromatic

# Cycle graph
erdos explore graph cycle --n 7 --properties
```

### `erdos explore squarefree`

Squarefree-specific utilities (relevant to problems like #848).

```bash
# Check if n is squarefree
erdos explore squarefree 12345

# List squarefree numbers up to N
erdos explore squarefree --up-to 100

# Squarefree density
erdos explore squarefree --density --up-to 10000
# Output: 6079/10000 ≈ 0.6079 (theory: 6/π² ≈ 0.6079)

# Check ab+1 squarefree for set
erdos explore squarefree --check-product-plus-one 1,2,3,4,5
```

---

## 3) Implementation

### Module Structure

```
src/erdos/
├── commands/
│   └── explore/
│       ├── __init__.py
│       ├── main.py          # erdos explore <problem_id>
│       ├── number.py        # erdos explore number
│       ├── primes.py        # erdos explore primes
│       ├── sequence.py      # erdos explore sequence
│       ├── graph.py         # erdos explore graph
│       └── squarefree.py    # erdos explore squarefree
└── core/
    └── explore/
        ├── __init__.py
        ├── number_theory.py  # SymPy wrappers
        ├── graph_theory.py   # NetworkX wrappers
        └── oeis.py           # OEIS lookup
```

### Dependencies

```toml
# Already in pyproject.toml [project.optional-dependencies]
explore = [
    "sympy>=1.13",
    "networkx>=3.4",
]
```

Commands should gracefully fail if extras not installed:

```python
try:
    import sympy
except ImportError:
    return CLIOutput.err(
        command="erdos explore",
        error_type="DependencyError",
        message="Install explore extras: uv sync --extra explore",
        code=ExitCode.CONFIG_ERROR,
    )
```

### Core Functions

```python
# src/erdos/core/explore/number_theory.py
from sympy import factorint, divisors, isprime, totient, primerange, prime

def factorize(n: int) -> dict[int, int]:
    """Return prime factorization as {prime: exponent}."""
    return factorint(n)

def is_squarefree(n: int) -> bool:
    """Check if n has no repeated prime factors."""
    return all(exp == 1 for exp in factorint(n).values())

def squarefree_up_to(n: int) -> list[int]:
    """List all squarefree numbers up to n."""
    return [k for k in range(1, n + 1) if is_squarefree(k)]
```

```python
# src/erdos/core/explore/graph_theory.py
import networkx as nx

def chromatic_number(G: nx.Graph) -> int:
    """Compute chromatic number (greedy approximation for large graphs)."""
    if G.number_of_nodes() <= 10:
        # Exact for small graphs
        return len(set(nx.greedy_color(G).values()))
    # Greedy approximation
    return len(set(nx.greedy_color(G, strategy="largest_first").values()))
```

---

## 4) Problem-Specific Explorations

### Number Theory Problems

For problems tagged `number theory`:

```python
def explore_number_theory_problem(problem: ProblemRecord, max_n: int = 1000):
    """Run number-theoretic explorations."""
    results = {}

    # Check for squarefree-related keywords
    if "squarefree" in problem.statement.lower():
        results["squarefree_density"] = len(squarefree_up_to(max_n)) / max_n
        results["squarefree_examples"] = squarefree_up_to(min(100, max_n))

    # Check for prime-related keywords
    if "prime" in problem.statement.lower():
        results["primes_up_to"] = list(primerange(2, min(100, max_n)))

    return results
```

### Graph Theory Problems

For problems tagged `graph theory`:

```python
def explore_graph_theory_problem(problem: ProblemRecord, max_n: int = 20):
    """Run graph-theoretic explorations."""
    results = {}

    # Check for chromatic number keywords
    if "chromatic" in problem.statement.lower():
        for n in range(3, min(10, max_n)):
            G = nx.complete_graph(n)
            results[f"K_{n}_chromatic"] = chromatic_number(G)

    return results
```

---

## 5) Output Schema

### JSON Output

```json
{
  "schema_version": 1,
  "command": "erdos explore number",
  "success": true,
  "data": {
    "input": 12345,
    "factorization": {"3": 1, "5": 1, "823": 1},
    "divisors": [1, 3, 5, 15, 823, 2469, 4115, 12345],
    "is_prime": false,
    "is_squarefree": true,
    "totient": 6576
  }
}
```

### Human Output

```
Number: 12345

Factorization: 3 × 5 × 823
Divisors: 1, 3, 5, 15, 823, 2469, 4115, 12345
Is Prime: No
Is Squarefree: Yes
Totient φ(n): 6576
```

---

## 6) Verification

### Unit Tests

```python
# tests/unit/core/explore/test_number_theory.py
def test_factorize():
    assert factorize(12) == {2: 2, 3: 1}

def test_is_squarefree():
    assert is_squarefree(6) == True
    assert is_squarefree(12) == False

# tests/unit/core/explore/test_graph_theory.py
def test_chromatic_complete():
    G = nx.complete_graph(5)
    assert chromatic_number(G) == 5
```

### CLI Tests

```bash
# Number exploration
erdos explore number 12345 --json | jq .data.factorization

# Graph exploration (requires explore extras)
erdos explore graph complete --n 5 --chromatic --json
```

### Integration Tests

```bash
# Full workflow
erdos explore 848 --max-n 100 --json
```

---

## 7) Future Extensions

1. **SageMath integration** - Heavy-duty symbolic computation
2. **Visualization** - `erdos viz` command with graphviz/matplotlib
3. **Jupyter support** - Interactive exploration notebooks
4. **Automated testing** - Check conjectures against computed examples
5. **OEIS integration** - Link problem sequences to OEIS

---

## 8) Related

- Issue #32: Math exploration & automation tools
- Problem #848: Squarefree products (prime use case)
- SymPy docs: https://docs.sympy.org/
- NetworkX docs: https://networkx.org/documentation/

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-26 | Initial draft |
