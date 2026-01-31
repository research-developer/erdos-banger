# Scratchpad

Append-only notes. Use:

- `erdos research note 74 "..."`

---

## 2026-01-31 — Novel computational refutations (exact MaxCut)

All computations are exact MaxCut (Gray-code / brute force); see scripts for details.

- Shift graphs `Sh(n)` (`scripts/shift_graph_sqrt_test.py`): `Sh(7)` has `|V|=21`, `ebip=5`, `⌊√21⌋=4` (fails).
- Kneser graphs `K(n,2)` (`scripts/kneser_graph_sqrt_test.py`): `K(6,2)` has `|V|=15`, `ebip=15`, `⌊√15⌋=3` (fails).
- Paley graphs `P(q)` (`scripts/paley_graph_sqrt_test.py`): `P(13)` has `|V|=13`, `ebip=13`, `⌊√13⌋=3` (fails).

Lean stubs + notes live in `formal/lean/Erdos/Problem074_novel_experimental.lean`.
