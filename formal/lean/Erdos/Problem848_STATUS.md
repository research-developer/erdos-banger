# Problem 848 — Lean Status (Erdos-banger)

This note is a **living inventory** of what is *actually proved* (no `sorry`) for Erdős Problem #848,
and what remains to complete a paper-level formalization.

## Core file

- `formal/lean/Erdos/Problem848_experimental.lean`
  - **Proved (core definitions)**
    - `NonSquarefreeProductProp`, `A₇`, `A₁₈`, `DiagonalCandidates`
  - **Proved (mod 25 / candidate constructions)**
    - `mod25_divisibility`, `mod25_divisibility_18`
    - `A₇_has_property`, `A₁₈_has_property`
  - **Proved (finite verification checkpoints)**
    - `problem_848_N50`, `problem_848_statement_50`, `problem_848_verified_50`
    - `problem_848_N100`, `problem_848_statement_100`
  - **Proved (counting residues)**
    - `A₇_card`, `A₁₈_card`, `A₁₈_card_le_A₇`
  - **Stated (not proved here; recorded as `Prop`)**
    - `SawhneyMainAt`, `SawhneyMain`
  - **Proved (glue, conditional on Sawhney)**
    - `problem_848_large_of_sawhney`
    - `problem_848_resolved_up_to_finite_check_of_sawhney`

## Sieve building blocks

- `formal/lean/Erdos/Problem848_sieve_basics.lean`
  - Proved: `dvd_pow_two_mul_add_one_iff_zmod_eq_neg_inv`
    (turns `p^2 ∣ (a*b+1)` into a unique residue-class constraint on `b (mod p^2)` when `p ∤ a`).

- `formal/lean/Erdos/Problem848_sieve_query1.lean`
  - Proved: `prime_sq_divides_implies_one_mod_four`
  - Stated as `Prop` (to be proved / ported): `TwoRootsModPSquared`, `DensitySinglePrime`

- `formal/lean/Erdos/Problem848_sieve_query2.lean`
  - Proved: `cross_residue_not_div_25`, `must_have_other_prime_square`
  - Stated as `Prop` (research-level): `SquarefreeFractionLowerBoundAt`,
    `SquarefreeFractionLowerBoundAt_asymptotic`

## More finite checks

- `formal/lean/Erdos/Problem848_sieve_query3.lean`
  - Proved (by `native_decide`): `problem_848_N200`

- `formal/lean/Erdos/Problem848_sieve_query4.lean`
  - Proved: `problem_848_N500` **conditional on** `No21InCandidates500` (a `Prop` placeholder).

## Paper-level target

- `formal/lean/Erdos/Problem848_sawhney_main.lean`
  - `SawhneyMainGoal : Prop` — alias for the missing analytic theorem.

## What’s missing for an end-to-end proof

1. A **Lean proof** of `SawhneyMain` (the analytic/sieve argument from Sawhney 2025), likely via:
   - CRT + inclusion–exclusion over residue classes mod `p^2`,
   - controlling the truncation/error terms (`o(1)` / explicit bounds),
   - and discharging the numeric inequalities in the casework.
2. An **effective** bound on `N₀` (or a verified finite certificate up to that `N₀`) if the goal is
   `∀ N, Problem848Statement N` rather than “resolved up to finite check”.
