/-
Problem 074 - Cayley Graph Experiments (Z/2Z)^d

Status: REFUTED for strict √n in random sweeps (2026-01-31)

We tested Cayley graphs on the elementary abelian 2-group (Z/2Z)^d:
  - vertices are bitstrings / integers 0..2^d-1
  - edges connect x to x xor g for generators g in S

Script:
  `scripts/cayley_z2_sqrt_test.py`

Computational refutation (Monte Carlo, exact MaxCut on sampled induced subgraphs, |S| ≤ 20):
- For d=6 (|V|=64), a random generator set S of size 7 produced a strict √n violation:
    k=18 subset with ebip=7 > Nat.sqrt 18 = 4.

This strongly suggests that "naively chosen" symmetric Cayley graphs are not close enough to bipartite
in the absolute-error sense required by Problem 74.

No axioms in this file; notes-only.
-/

import Erdos.Problem074_experimental

namespace Erdos.Problem074.Cayley

universe u

/-- The $500 question (square-root bound), stated as a `Prop`. -/
abbrev erdos_74_sqrt : Prop :=
  Erdos.Problem074.erdos_74_sqrt.{u}

end Erdos.Problem074.Cayley
