# Aristotle Outputs (Problem 848)

This folder contains **reference-only** outputs from Aristotle (Harmonic) for Erdős Problem #848.
They were generated against **Lean v4.24.0 / older Mathlib**, so **do not import them** into the
current project. Use them as a hint bank to port ideas/lemmas into the in-tree files under
`formal/lean/Erdos/`.

## Files

- `formal/lean/aristotle/Problem848_jobA_output.lean`
  - Proves a (legacy) `problem_848_N50` style statement.
  - Negates an *over-strong* “Sawhney main” statement parameterized by arbitrary `c > 0`.

- `formal/lean/aristotle/Problem848_jobB_output.lean`
  - Contains an explicit counterexample showing why
    `∀ c > 0, … (|A| ≥ (1/25 - c)N) → …` is false: taking `c = 1` makes the density condition
    trivial and breaks the conclusion.
  - Takeaway: the correct paper-level statement is **existential** (“there exists a small absolute
    constant”), not “for all `c > 0`”.

- `formal/lean/aristotle/Problem848_sieve_query1_aristotle.lean`
  - **Does not compile** as-is with current Mathlib.
  - Contains attempted proofs of sieve building blocks (notably “two roots mod `p^2`” and a
    single-prime density bound). Port selectively.

- `formal/lean/aristotle/Problem848_sieve_query2_output.lean`
  - Negates an earlier `squarefree_fraction_lower_bound` statement that was missing critical
    hypotheses / was stated too uniformly in `N`.
  - Takeaway: the squarefree-fraction claim should be stated in an **asymptotic / ∃N₀** form and
    must include the right congruence hypotheses (see `formal/lean/Erdos/Problem848_sieve_query2.lean`).

## “SSOT” in-tree code

The current sorry-free working development lives in:

- `formal/lean/Erdos/Problem848_experimental.lean`
  - Finite verification checkpoints (`N = 50`, `N = 100`) and glue theorems.
  - The large-`N` analytic theorem is recorded as a `Prop` (`SawhneyMainAt` / `SawhneyMain`) until
    the sieve argument is formalized.

- `formal/lean/Erdos/Problem848_sieve_basics.lean`
  - Key congruence lemma: `p^2 ∣ (a*b+1)` with `p ∤ a` forces a unique residue class for `b (mod p^2)`.
