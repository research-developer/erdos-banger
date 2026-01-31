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

## 2026-01-31 — Hasse diagrams update: explicit projective transforms still violate √n

We implemented the paper’s “apply a projection” step explicitly (sampled random invertible 3×3 projective
transforms over rationals, rejecting transforms that create duplicate point x-coordinates / duplicate line slopes).

Code:
- `scripts/hasse_poset_test.py`: `use_projective_transform=True`
- `scripts/hasse_projection_sweep.py`: quick robustness sweep across projections

Findings (Monte Carlo, exact MaxCut on each sampled subset):
- The strict constant-1 `⌊√n⌋` bound still fails for small `n` in projective mode.
  - Example failures observed include `n=20` with `ebip=5 > ⌊√20⌋=4` and `n=25` with `ebip=6 > ⌊√25⌋=5`
    (for `t=4` and multiple random projections).
  - An ad-hoc sweep at `t=4`, `n=20` found violations in **3/10** random projections (with moderate sampling).
- Rank-parity defects `|D(S)|` are often a very loose upper bound (e.g. defects ≫ ebip on the same subset).
- Tooling: `scripts/ebip_utils.py` now exposes a MaxCut witness assignment; `scripts/hasse_poset_test.py` prints the
  explicit edge-deletion witness (monochromatic edges) for violating subsets to help pattern-hunt.

Interpretation:
- “Projection details” do not appear to rescue the strict √n bound for the Suk–Tomon / Tomon Claim 12 graph,
  at least on these small instances.

## 2026-01-31 — New families tested (computational, exact MaxCut on sampled subsets)

All scripts below compute exact `ebip = |E| - MaxCut` (Gray-code) on sampled induced subgraphs with `|S| ≤ 25`.

### Specker graph G1(n,3,1) (EHS82 Def. 1.2)

- Script: `scripts/specker_graph_sqrt_test.py`
- Result: **refuted for strict √n**.
  - For `n=13` (`|V|=286`), the script includes a deterministic witness `k=20` induced subset with
    `ebip=5 > ⌊√20⌋=4`.

### Edge graph G0(n,3,1) prototype (EHS82 Def. 1.1)

- Script: `scripts/edge_graph_g0_sqrt_test.py`
- Result (Monte Carlo, `n=11`, `|V|=165`):
  - Found strict √n violation at `k=18`: `ebip=6 > ⌊√18⌋=4`.
- Status: refuted (for the strict bound).

### Cayley graphs on (Z/2Z)^d

- Script: `scripts/cayley_z2_sqrt_test.py`
- Result (Monte Carlo, random generator sets, `d=6`, `|V|=64`):
  - Found strict √n violation at `k=18`: `ebip=7 > ⌊√18⌋=4`.
- Status: refuted (for the strict bound).

### Ordered edge graphs OE(G,<)

- Script: `scripts/ordered_edge_graph_sqrt_test.py`
- Result (very small sweep):
  - OE applied to `K_{6,6}` with random orders produced many bipartite-looking induced samples (`ebip=0`).
  - This does not establish usefulness: chromatic behavior looks small and we did not push parameters.
- Status: inconclusive.

### Heuristic extremal search (finite graphs)

- Script: `scripts/ebip_chromatic_extremal_search.py`
- Result (n=18):
  - Found a graph with `χ=4` and whole-graph `ebip=4 = ⌊√18⌋`.
  - But sampled induced subgraphs already violate strict √k (e.g. `k=12` sample with `ebip=4 > ⌊√12⌋=3`).
- Interpretation: hereditary √n appears much tighter than whole-graph √n.

## 2026-01-31 — SAT/backtracking search over edge deletions (global and hereditary)

Script:
- `scripts/ebip_sat_search.py`

Idea:
- “SAT-like” search space: fix a base graph with `χ ≥ 5`, treat each base edge as a boolean variable
  (keep/delete), and backtrack.
- Pruning is driven by **exact** MaxCut witnesses:
  - If a subset violates `ebip(G[S]) ≤ ⌊√|S|⌋`, compute a MaxCut witness for `G[S]` and branch by deleting one of the
    witness’s monochromatic edges (those deletions provably decrease `ebip(G[S])` for that cut).

Findings so far (exact `χ`, exact MaxCut on whole graph; induced-subgraph checks are sampled):

### Mycielski M5 (n=23)

Run:
- `uv run python scripts/ebip_sat_search.py --base mycielski5 --global-only --branch-limit 0 --max-deletions 1`

Observed:
- `M5`: `χ=5`, `ebip=16`, `⌊√23⌋=4` (fails whole-graph bound).
- In the backtracking search, deleting any edge that would decrease `ebip` causes `χ` to drop below 5 immediately.
  So within this base, we cannot even satisfy the *necessary* whole-graph √n constraint while keeping `χ ≥ 5`.

### Randomized Hajós chains (n=25)

Run:
- `uv run python scripts/ebip_sat_search.py --base hajos25 --hajos-samples 1 --global-only --branch-limit 0 --max-deletions 1`

Observed (for the sampled chain instance):
- `χ=5`, `ebip=19`, `⌊√25⌋=5` (fails whole-graph bound).
- Deleting any edge that would decrease `ebip` collapses `χ` below 5 immediately (edge-critical behavior).

Interpretation:
- These two independent “generic” 5-chromatic generators (Mycielski and Hajós) look structurally incompatible with
  the strict √n regime even at the whole-graph level; the search repeatedly runs into edge-criticality barriers.
