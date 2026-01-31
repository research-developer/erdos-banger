/-
Problem 074 - SAT/Backtracking Search Experiments (Edge-Deletion Search)

Status: INCONCLUSIVE / NEGATIVE EVIDENCE (2026-01-31)

Goal (computational): Search for a *finite* graph G with:
  - χ(G) ≥ 5, and
  - for every induced subgraph H on k vertices:
      ebip(H) ≤ ⌊√k⌋
where ebip(H) = |E(H)| - MaxCut(H).

Script:
  `scripts/ebip_sat_search.py`

Search method:
  - Fix a base 5-chromatic graph (e.g. Mycielski M5, or a randomized Hajós-chain graph),
  - Treat each base edge as a boolean variable (keep/delete),
  - Backtrack with pruning driven by *exact* MaxCut witnesses:
      If H violates ebip(H) ≤ ⌊√|V(H)|⌋, compute a MaxCut witness and branch by deleting
      one of the witness’s monochromatic edges (a deletion that provably decreases ebip(H)
      for that witness cut).

Current findings (whole-graph checks are exact; induced-subgraph checks are sampled):
  - Mycielski M5 has n=23, χ=5, ebip=16 > ⌊√23⌋=4 and appears “edge-critical” relative to
    edges whose deletion would reduce ebip: deleting any such edge drops χ below 5 immediately.
  - Randomized Hajós-chain graphs at n=25 similarly appear edge-critical for single-edge deletions
    that would reduce ebip.

Interpretation:
  - These experiments suggest that “standard” 5-chromatic generators may be structurally
    incompatible with the strict √n regime, even before enforcing the full hereditary constraint.

No axioms in this file; notes-only.
-/

import Erdos.Problem074_experimental

namespace Erdos.Problem074.SATSearch

universe u

/-- The $500 question (square-root bound), stated as a `Prop`. -/
abbrev erdos_74_sqrt : Prop :=
  Erdos.Problem074.erdos_74_sqrt.{u}

end Erdos.Problem074.SATSearch
