/-
Problem 074 - Ordered Edge Graphs OE(G,<) Experimental Notes

Status: INCONCLUSIVE (2026-01-31)

EHS82 Definition 1.3 defines the ordered edge graph OE(G,<):
  - vertices are edges of G, with endpoints oriented by a total order <
  - two edges {x0<x1}, {y0<y1} are adjacent iff x1=y0 or y1=x0

Special case: OE(K_n, natural order) is the shift graph Sh(n), which is refuted for strict √n.

We experimented with OE applied to other base graphs + random vertex orders:
  `scripts/ordered_edge_graph_sqrt_test.py`

Early computational notes:
- OE(K_{6,6}, random order) appears to have ebip=0 on many sampled induced subsets (sizes 15/18/20),
  suggesting the OE output may be bipartite or nearly bipartite in these cases.
- This is not yet useful for Problem 74: we did not find evidence of large chromatic number in these OE outputs.

Next step (if we revisit):
- Search for a base family (G_n, <_n) whose OE outputs have unbounded chromatic number while remaining
  hereditarily almost-bipartite (ebip ≤ √n).

No axioms in this file; notes-only.
-/

import Erdos.Problem074_experimental

namespace Erdos.Problem074.OrderedEdgeGraph

universe u

/-- The $500 question (square-root bound), stated as a `Prop`. -/
abbrev erdos_74_sqrt : Prop :=
  Erdos.Problem074.erdos_74_sqrt.{u}

end Erdos.Problem074.OrderedEdgeGraph
