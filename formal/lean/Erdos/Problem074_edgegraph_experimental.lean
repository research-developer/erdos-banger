/-
Problem 074 - EHS82 Edge Graphs (G0) Experimental Notes

Status: REFUTED for strict √n (2026-01-31)

EHS82 define the "k-edge graph" G0(α,k,i) (Definition 1.1). These are obtained by
iterating the ordered-edge-graph operator OE(·,<), and have large chromatic number
in various set-theoretic regimes.

We tested a small finite proxy (on 3-subsets, i=1) in:
  `scripts/edge_graph_g0_sqrt_test.py`

Computational refutation (exact MaxCut, sampled induced subgraphs with |S| ≤ 25):
- For n=11 (|V|=165), the script finds a connected induced subgraph with k=18 vertices and
  ebip=6 > Nat.sqrt 18 = 4.

Therefore this naive G0(n,3,1)-style proxy does not satisfy the strict constant-1 √n bound.

No axioms in this file; this is a notes-only Lean module for tracking the approach.
-/

import Erdos.Problem074_experimental

namespace Erdos.Problem074.EdgeGraph

universe u

/-- The $500 question (square-root bound), stated as a `Prop`. -/
abbrev erdos_74_sqrt : Prop :=
  Erdos.Problem074.erdos_74_sqrt.{u}

end Erdos.Problem074.EdgeGraph
