/-
Problem 074 - Specker Graphs (EHS82) Experimental Notes

Status: EXPERIMENTAL (2026-01-31)

Goal: Explore whether Specker graphs (Erdős–Hajnal–Szemerédi 1982, Def. 1.2)
could satisfy the strict square-root bound in Erdős Problem #74:

  maxSubgraphEdgeDistToBipartite G n ≤ Nat.sqrt n

Computational evidence (exact MaxCut, |S| ≤ 25):
- `scripts/specker_graph_sqrt_test.py` tests the smallest nontrivial Specker graph family `G1(n,3,1)`.
- This family is **refuted** for the strict constant-1 √n bound:
  - For n=13 (|V|=286), the script includes a deterministic k=20 induced subset with
    ebip=5 > Nat.sqrt 20 = 4.

Remaining question (still open, and not addressed here):
- Whether other Specker parameters (k>3, other i) or other set-system graphs can do better.

No axioms in this file. This is a notes-only Lean module for tracking the approach.
-/

import Erdos.Problem074_experimental

namespace Erdos.Problem074.Specker

universe u

/-- The $500 question (square-root bound), stated as a `Prop`. -/
abbrev erdos_74_sqrt : Prop :=
  Erdos.Problem074.erdos_74_sqrt.{u}

end Erdos.Problem074.Specker
