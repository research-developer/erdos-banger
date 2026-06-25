# Problem 1052 — Unitary perfect numbers (OPEN)

Exact-integer computational study for Erdős #1052 (Linear MATH-11):
*are there only finitely many unitary perfect numbers?*

- `unitary_perfect.py` — `sigma_star`, `is_unitary_perfect`, exact
  verification of the 5 known unitary perfect numbers, an exhaustive linear
  sieve search, a secondary block-DFS cross-check, and structural notes.
  Run: `python3 unitary_perfect.py [N]` (default `N = 10^8`).
- `test_unitary_perfect.py` — fast self-tests (`python3 -m pytest` or
  `python3 test_unitary_perfect.py`).
- `RESULTS.md` — the verified data, search coverage, structural observations,
  and an explicit honest-scope statement (the problem is **not** resolved).

Discipline: zero floating point; Python big integers throughout.
