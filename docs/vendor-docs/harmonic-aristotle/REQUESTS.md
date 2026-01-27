# Aristotle Request Tracking

This file is a lightweight “do not forget” log for Aristotle jobs we’ve submitted, since the vendor UI queue status and any local polling logs are otherwise easy to lose.

## Active Jobs (2026-01-26)

### Job A — Problem 848 (3 theorems)

- **Description:** Prove three theorems about a number theory problem: `problem_848_N50`, `sawhney_main`, and `problem_848`.
- **Input file:** `formal/lean/Erdos/Problem848.lean` (note: this file re-exports `Erdos.Problem848_experimental` and may have changed since submission).
- **Aristotle project ID:** `09934619-efc0-46c7-8cc9-8114aea1db5e`
- **Observed status (UI):**
  - Created `2026-01-26 13:10:43` (local)
  - Updated `2026-01-26 18:48:47` (local), progress `69%` (no output file yet)

### Job B — Problem 848 (max-size, vague prompt)

- **Description:** Prove theorems about the maximum size of sets where `ab+1` is not squarefree.
- **Observed status (UI):**
  - Created `2026-01-26 13:01:38` (local)
  - Updated `2026-01-26 18:49:08` (local), progress `70%` (no output file yet)
- **Aristotle project ID:** unknown (not captured in repo; check vendor UI when it completes).

### Job C — Sieve Query 1 (density lemmas)

- **Description:** Prove theorems about the density of diagonal candidates.
- **Input file:** `formal/lean/Erdos/Problem848_sieve_query1.lean`
- **Sorries to solve:** `two_roots_mod_p_squared`, `density_single_prime`
- **Observed status (UI):** Queued (Created 2026-01-26 17:20:46)

### Job D — Sieve Query 2 (squarefree fraction)

- **Description:** Prove a lower bound on squarefree fraction.
- **Input file:** `formal/lean/Erdos/Problem848_sieve_query2.lean`
- **Sorries to solve:** `squarefree_fraction_lower_bound`
- **Observed status (UI):** Queued (Created 2026-01-26 17:20:46)

## Completed / Not Needed

- `formal/lean/Erdos/Problem848_sieve_query3.lean` — Fully solved locally (N=200 verification). Do not send.
