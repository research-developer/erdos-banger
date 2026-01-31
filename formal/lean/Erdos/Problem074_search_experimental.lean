/-
Problem 074 - Heuristic Finite Search Experiments

Status: INCONCLUSIVE (2026-01-31)

This approach uses *computer search* rather than a named construction family:
  - search for finite graphs with high chromatic number and small ebip
  - inspect the resulting "extremal" graphs for structure that could generalize

Script:
  `scripts/ebip_chromatic_extremal_search.py`

Computational notes:
- For n=18, the script found a graph with χ=4 and ebip=4 = Nat.sqrt 18 (whole-graph constraint).
- However, a sampled induced subgraph already violates the hereditary √k bound:
    k=12 sample with ebip=4 > Nat.sqrt 12 = 3.

Interpretation:
- Enforcing ebip(G) ≤ √|V(G)| for the whole graph is significantly easier than enforcing the
  hereditary constraint required by Problem 74 (all induced subgraphs).
- The heuristic still seems valuable as a "pattern discovery" tool.

No axioms in this file; notes-only.
-/

import Erdos.Problem074_experimental

namespace Erdos.Problem074.Search

universe u

/-- The $500 question (square-root bound), stated as a `Prop`. -/
abbrev erdos_74_sqrt : Prop :=
  Erdos.Problem074.erdos_74_sqrt.{u}

end Erdos.Problem074.Search
