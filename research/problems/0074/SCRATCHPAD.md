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

## 2026-01-31 — Hasse diagrams / Suk–Tomon rank-parity experiments (prototype)

Implemented a prototype of Tomon’s Claim 12 construction ("Hasse diagrams with large chromatic number")
and the **rank-parity defect** upper bound on `ebip` in:

- `scripts/hasse_poset_test.py`

Notes:
- The implementation uses the paper’s *incidence* definition, but models the required “distinct x / distinct slopes”
  via deterministic injective order-keys (`x_key`, `slope_key`) rather than an explicit projective transformation.
- Experiments sample both uniformly random subsets and “connected” subsets (BFS-grown) to make cycles more likely.

Findings (exact MaxCut on selected samples with |S|≤25):
- `t=4` approximant (`|V|=220, |E|=380`) has a **connected** induced subset `S` with `|S|=25` and
  `ebip(G[S])=6 > √25=5` (so the strict constant-1 `√n` bound fails for this *naive* model).
  The script prints the subset vertex ids and decoded incidences for reproduction (seed is fixed in `main()`).
- For `t=3` (`|V|=72, |E|=56`) and `t=5` quick probe (`|V|=525, |E|=1600`), no strict `√n` violations were
  found in the limited MaxCut samples, but this is not exhaustive.
