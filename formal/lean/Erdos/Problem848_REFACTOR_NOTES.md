# Problem 848 Refactor Notes (Presentation + SSOT)

**Date:** 2026-01-29
**Status:** Builds clean; independent verification in progress
**Scope:** This document is the SSOT for the **`Problem848_GPT.lean` sandbox** refactor.

## Files (What to Touch / Not Touch)

- ✅ `formal/lean/Erdos/Problem848_GPT.lean` — sandbox (edited during this refactor sprint)
- ❌ `formal/lean/Erdos/Problem848_Refactor.lean` — reference (do not edit)
- ❌ `formal/lean/Erdos/Problem848_FINAL.lean` / `formal/lean/Erdos/Problem848_Claude.lean` — historical variants (may still contain `native_decide`; out of scope for this sprint)

## Current State (Verified Locally)

- `formal/lean/Erdos/Problem848_GPT.lean` is **5570 lines**.
- `lake build Erdos.Problem848_GPT` succeeds (no errors, no sorries).
- `native_decide` count in `Problem848_GPT.lean`: **0**.

### Build / Audit Commands

```bash
cd /Users/ray/Desktop/CLARITY-DIGITAL-TWIN/erdos-banger/formal/lean
source ~/.elan/env
lake build Erdos.Problem848_GPT

cd /Users/ray/Desktop/CLARITY-DIGITAL-TWIN/erdos-banger
rg -n "\\bnative_decide\\b" formal/lean/Erdos/Problem848_GPT.lean
rg -n "\\bsorry\\b" formal/lean/Erdos/Problem848_GPT.lean
```

**Note:** Full builds can be slow (~10–15 minutes) due to very large `simp`/`norm_num` goals in the coarse prime-sum section.

---

## What Actually Solved the “Mathlib bans native_decide” Problem

### 1) Squarefree numerals without `native_decide` (certified computation)

We use:

- `Mathlib.Tactic.Simproc.Factors` (computes `Nat.primeFactorsList` for numerals via a simproc)
- `Nat.squarefree_iff_nodup_primeFactorsList` (reduces squarefreeness to `Nodup` of the factor list)

Pattern:

```lean
import Mathlib.Tactic.Simproc.Factors

-- Squarefree n ↔ Nodup (primeFactorsList n); simp computes primeFactorsList for numerals.
-- Example (conceptual):
-- refine (Nat.squarefree_iff_nodup_primeFactorsList (by decide : (n:ℕ) ≠ 0)).2 ?_
-- simp
```

This avoids the “kernel can’t compute `Nat.minSqFac`” failure mode, without adding axioms.

### 2) Avoid `Finset` equality decision: prove **List equality**, then lift

Core issue: `decide` on `Finset` equality reduces to multiset/permutation machinery (can get stuck or explode).

Fix: compute an ordered `List` and prove **strict list equality** (fast), then lift with `List.toFinset`.

In `Problem848_GPT.lean` this is used for `diagPrimesCoarse` / `no5PrimesCoarse` at the coarse cutoff:

- explicit lists: `diagPrimesCoarse_listL`, `no5PrimesCoarse_listL`
- computed lists: `diagPrimesCoarse_computed_list`, `no5PrimesCoarse_computed_list`
- lift: `congrArg List.toFinset` + simp

### 3) The “hidden gotcha”: `(p : Num).Prime` doesn’t reduce for `decide`

`Num.Prime` is designed for kernel computation, but the cast `(p : Num)` (via `Num.ofNat'`) does not unfold enough for `decide` to see the `Num.pos` constructor.

Working fix: define a **kernel-reducible** conversion:

```lean
def natToNum : ℕ → Num
  | 0 => 0
  | n + 1 => natToNum n + 1
```

Then compute primality via `(natToNum p).Prime`, and bridge back to `Nat.Prime p` using `(↑(natToNum p) : ℕ) = p`.

This makes list-based prime enumeration computable by `decide` in the kernel.

---

## Prime Sums (Why the Build Is Slow)

The coarse prime-sum equalities/inequalities are closed by expanding to a gigantic explicit sum (via `simp`) and finishing with `norm_num`.

This is correct, but expensive for the kernel and requires large `maxSteps` / `maxHeartbeats` in a few lemmas.

**Future improvement ideas (do not change Lean file right now):**

- Replace “expand-then-`norm_num`” with `field_simp` (or `simp only [field]`) to clear denominators once and reduce to integer arithmetic.
- Isolate the coarse-sum verification into a separate file or section with tightly scoped options so the rest of the file compiles faster.

---

## Presentation Cleanup (No Lean Changes Yet)

The file builds but emits many linter warnings (e.g. “try `simp` instead of `simpa`”, unused simp args, deprecations).

Recommended **non-behavioral** cleanup pass later:

1. Replace unnecessary `simpa` with `simp` where suggested.
2. Remove unused simp args from simp lists.
3. Replace deprecated `Finset.exists_ne_of_one_lt_card` with `Finset.exists_mem_ne`.
4. Consolidate repeated `set_option maxRecDepth` / `maxHeartbeats` blocks into a single “heavy computation” region (or a helper file) for readability.

---

## Historical Note (For Reviewers)

Other files in `formal/lean/Erdos/` may still contain `native_decide` (e.g. older FINAL/Claude variants).

The Mathlib-compliant target for this sprint is the sandbox:

- `formal/lean/Erdos/Problem848_GPT.lean` (`native_decide` = 0)
