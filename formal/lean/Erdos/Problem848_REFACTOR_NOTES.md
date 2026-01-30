# Problem 848 Refactor Notes (Presentation + SSOT)

**Date:** 2026-01-29
**Last Updated:** 2026-01-30 (structural refactoring — density bound extraction)
**Status:** 🔄 REFACTOR IN PROGRESS — Extracting repeated density bound patterns
**Scope:** This document is the SSOT for the **Problem 848 Lean formalization**.

---

## ⚠️ CRITICAL GOTCHAS — READ BEFORE EDITING

These are known pitfalls that WILL break the build if you're not careful:

### 1. `simpa` → `simp` is NOT a simple replacement

**WRONG:**
```lean
-- Original (works)
simpa using h0
-- Naive replacement (BREAKS)
simp using h0  -- ERROR: 'using' is not valid with simp
```

**CORRECT patterns:**
```lean
-- Pattern A: simpa using X → simp at X
simpa using h0  →  simp at h0

-- Pattern B: simpa [args] → simp only [args] (then verify goal closes)
simpa [foo]  →  simp only [foo]  -- but test it!

-- Pattern C: simpa at H → simp at H (check if goal still closes)
```

### 2. ZMod field access doesn't work like Fin

**WRONG:**
```lean
-- This works for Fin n:
r₁.isLt  -- gives proof that r₁.val < n

-- This FAILS for ZMod (p^2):
r₁.isLt  -- ERROR: invalid field 'isLt', ZMod is not Fin
```

**Why:** `ZMod n` unfolds to a match expression, not directly to `Fin n`.

### 3. Multiplication order matters in type checking

```lean
-- These are NOT interchangeable in type assertions:
N / (p ^ 2 * 100) + 1  -- NOT equal to
N / (100 * p ^ 2) + 1  -- even though mathematically same
```

### 4. Lake builds by FILENAME, not namespace

```bash
# CORRECT (filename is Problem848_REFACTOR.lean):
lake build Erdos.Problem848_REFACTOR

# WRONG (namespace inside file):
lake build Erdos.Problem848_workbench  # ERROR: no such file
```

### 5. Tactic `decide` limitations

- `decide` on Finset equality can explode or hang
- Use List equality + `List.toFinset` instead
- `(p : Num).Prime` won't reduce; use `(natToNum p).Prime`

---

## Progress Tracking (GPT Agent)

### Phase 1: Linter Cleanup (COMPLETED)

| Metric | Original | Final | Progress |
|--------|----------|-------|----------|
| Build errors | 0 | 0 | ✅ Maintained |
| Build warnings | ~50 | **0** | ✅ **100% fixed** |
| Tabs | >0 | **0** | ✅ **100% fixed** |
| Deprecated APIs | 1 | **0** | ✅ **100% fixed** |
| `simpa` count | 542 | 505 | ✅ 37 safely removed (7%) |
| Time elapsed | — | ~10 hours | Completed |

### Phase 2: Structural Refactoring (IN PROGRESS)

| Metric | Before | Current | Progress |
|--------|--------|---------|----------|
| Total lines | 5594 | **5476** | ✅ **-118 lines (-2.1%)** |
| `card_biUnion_le` calls | 18 | **11** | ✅ 7 deduplicated |
| Helper lemma usages | 0 | **9** | ✅ 1 def + 8 call sites |
| `simpa` count | 505 | **498** | ✅ 7 more removed |

#### Two Distinct Patterns Identified

**Pattern A: Mod 25 density bounds** — ✅ COMPLETE
- Helper: `residue_class_card_bound_of_subset` at line ~3623
- Uses: `off_count_modEq25_le'` (line 3154)
- Status: **8/8 blocks replaced**

**Pattern B: Mod 100 density bounds** — 🔄 IN PROGRESS
- Helper needed: `residue_class_card_bound100_of_subset` (not yet created)
- Uses: `off_count_modEq100_le'` (line 3228)
- Remaining blocks at lines: **5070, 5148, 5295, 5369**
- Status: **0/4 blocks replaced**

**Why two helpers?** The mod 100 pattern has different signature:
```lean
-- Mod 25 (done):
off_count_modEq25_le' N p b t hp hp5        -- t is residue mod 25

-- Mod 100 (needs new helper):
off_count_modEq100_le' N p b t25 t4 hp hp2 hp5  -- t25 mod 25, t4 mod 4, excludes p=2
```

### ✅ BUILD STATUS (as of 2026-01-30 — VERIFIED)

```
lake build Erdos.Problem848_REFACTOR
Build completed successfully (2755 jobs).
```

**Independently verified:**
- 0 errors ✅
- 0 warnings ✅
- 0 tabs ✅
- 0 deprecated APIs ✅
- 0 sorry ✅
- 0 native_decide ✅

**What the agent accomplished:**
- Replaced `Finset.exists_ne_of_one_lt_card` → `Finset.exists_mem_ne`
- Removed all unused simp arguments flagged by linter
- Converted 37 `simpa` → `simp` where safe
- Learned which `simpa` conversions break proofs and avoided them
- Fixed all indentation-broken `by` blocks
- Removed all tab characters

---

## Files Status

| File | Namespace | Build Command | Status | Purpose |
|------|-----------|---------------|--------|---------|
| `Problem848.lean` | `Erdos.Problem848` | `lake build Erdos.Problem848` | ✅ Builds | **Primary** — DO NOT EDIT |
| `Problem848_FINAL.lean` | `Erdos.Problem848_FINAL` | `lake build Erdos.Problem848_FINAL` | ✅ Builds | **Backup** — DO NOT EDIT |
| `Problem848_REFACTOR.lean` | `Erdos.Problem848_workbench` | `lake build Erdos.Problem848_REFACTOR` | 🔄 Cleaning | **Sandbox** — GPT agent workspace |

**⚠️ NAMESPACE MISMATCH:** The REFACTOR file has namespace `Problem848_workbench` but filename `Problem848_REFACTOR.lean`. Lake builds by filename, so use `lake build Erdos.Problem848_REFACTOR`.

### Verification Commands

```bash
# From repo root:
cd formal/lean
source ~/.elan/env

# Build REFACTOR (note: uses FILENAME not namespace)
lake build Erdos.Problem848_REFACTOR

# Build stable files (for comparison)
lake build Erdos.Problem848
lake build Erdos.Problem848_FINAL

# Audit (should all return 0)
rg -c "\\bnative_decide\\b" Erdos/Problem848_REFACTOR.lean    # 0
rg -c "\\bsorry\\b" Erdos/Problem848_REFACTOR.lean            # 0
```

---

## What Actually Solved the "Mathlib bans native_decide" Problem

### 1) Squarefree numerals without `native_decide` (certified computation)

We use:
- `Mathlib.Tactic.Simproc.Factors` (computes `Nat.primeFactorsList` for numerals via a simproc)
- `Nat.squarefree_iff_nodup_primeFactorsList` (reduces squarefreeness to `Nodup` of the factor list)

### 2) Avoid `Finset` equality decision: prove **List equality**, then lift

Core issue: `decide` on `Finset` equality reduces to multiset/permutation machinery (can get stuck or explode).

Fix: compute an ordered `List` and prove **strict list equality** (fast), then lift with `List.toFinset`.

### 3) The "hidden gotcha": `(p : Num).Prime` doesn't reduce for `decide`

`Num.Prime` is designed for kernel computation, but the cast `(p : Num)` (via `Num.ofNat'`) does not unfold enough for `decide` to see the `Num.pos` constructor.

**Working fix:** Define a **kernel-reducible** conversion:

```lean
def natToNum : ℕ → Num
  | 0 => 0
  | n + 1 => natToNum n + 1
```

Then compute primality via `(natToNum p).Prime`, and bridge back to `Nat.Prime p` using `(↑(natToNum p) : ℕ) = p`.

This makes list-based prime enumeration computable by `decide` in the kernel.

---

## Gemini Feedback Analysis (2026-01-29)

External reviewer (Gemini 3.0) provided feedback. Here's the triage:

### ✅ VALID — Should Address in Cleanup Pass

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **Scattered `open scoped`** | Lines 65, 2426-2428 | Move all `open scoped` to top of file after imports |
| **Repeated density logic** | `hA7_bound`/`hA18_bound` at lines 3903, 4402, 4471, 4634, 4702 | Extract to helper lemma to reduce duplication |
| **Linter warnings** | Throughout | Replace `simpa` with `simp` where linter suggests |
| **Deprecated API** | Line 1938 | Replace `Finset.exists_ne_of_one_lt_card` with `Finset.exists_mem_ne` |
| **Unused simp args** | Multiple locations | Remove unused args from simp lists |

### ⚠️ ACCEPTABLE — Reviewer Acknowledged These Are Fine

| Issue | Verdict | Reasoning |
|-------|---------|-----------|
| **N₀ = 10,000,000 constant** | Research-code style, acceptable | Used existentially; could be made abstract but not required |
| **"Python-verified" constants** | Ugly but mathematically sound | Proven via `norm_num` — verified in Lean kernel |
| **Large `decide` on prime lists** | Mitigated | Already using `Num` (binary-encoded) which is much faster than `Nat` unary |

### ❌ NOT APPLICABLE — Misunderstanding or N/A

| Issue | Why N/A |
|-------|---------|
| **"Add norm_num or specialized prime sieve"** | Already using `Num.Prime` + `natToNum` which IS the optimized approach |
| **"Consider field_simp"** | The current approach works; optimization would be for build time only |

---

## maxHeartbeats Audit

Current usage (may need reduction for Mathlib submission):

| Line | Setting | Context |
|------|---------|---------|
| 1615 | 1,000,000 | |
| 2544 | 20,000,000 | Prime list computation |
| 2550 | 40,000,000 | Prime list computation |
| 2582 | 20,000,000 | Prime list computation |
| 2596 | 40,000,000 | Prime list computation |
| 2646 | 20,000,000 | Prime list computation |
| 2655 | 40,000,000 | Prime list computation |
| 3541 | 2,000,000 | `sawhney_main` theorem |
| 4975+ | 1,600,000 | Various density bounds |

**Standard Mathlib:** Prefers ≤ 200,000, tolerates up to ~1,000,000.
**Current:** Uses up to 40,000,000 in heavy computation sections.

**Recommendation:** If submitting to Mathlib, isolate heavy computations into separate lemmas or a dedicated file.

---

## Presentation Cleanup Checklist

Non-behavioral changes for code cleanliness:

### ✅ COMPLETED (by GPT agent) — ALL LINTER WORK DONE

- [x] Move all `open scoped` to file header (after imports) — **DONE**
- [x] Remove tab characters from file — **DONE** (0 tabs)
- [x] Fix indentation-broken `by` blocks — **DONE**
- [x] Replace `simpa` → `simp` where safe — **DONE** (37 converted, rest needed)
- [x] Fix deprecated API (`exists_ne_of_one_lt_card` → `exists_mem_ne`) — **DONE**
- [x] Remove unused simp arguments — **DONE** (all flagged args removed)

### 🔄 REMAINING STRUCTURAL DEBT (In Progress)

These are NOT linter issues — they're structural improvements for Mathlib submission:

| Debt | Current State | Ideal State | Priority | Status |
|------|---------------|-------------|----------|--------|
| **Mod 25 density bounds** | 8 blocks | Extract to helper | HIGH | ✅ **8/8 done** |
| **Mod 100 density bounds** | 4 blocks at lines 5070, 5148, 5295, 5369 | Extract to 2nd helper | HIGH | 🔄 **0/4 done** |
| **maxHeartbeats** | 13 occurrences, up to 40,000,000 | ≤200,000 per Mathlib style | LOW | 🔲 Not started |
| **Monolithic theorem** | `sawhney_main` is 2000+ lines | Break into 10-15 composable lemmas | LOW | 🔲 Not started |
| **Computation isolation** | Heavy prime sums mixed with proof | Separate `PrimeSums.lean` file | LOW | 🔲 Not started |

**Current focus:** Create `residue_class_card_bound100_of_subset` helper for mod 100 pattern, then replace 4 remaining blocks.

### 🔲 TODO — Linter Warnings

#### Unused Simp Arguments (~18 occurrences)

These simp lists have args that don't contribute — remove them:

| Line | Unused Arg | Current Code |
|------|------------|--------------|
| ~1098 | `hcase` | `simp [hcase] at hmod'` |
| ~2589 | `and_assoc` | `simp [..., and_assoc, and_left_comm, and_comm]` |
| ~2603 | `and_assoc` | same pattern |
| ~2674 | `and_comm` | `simp [offPrimesCoarse, ..., and_comm]` |
| ~2773 | `hB` | `simp [hIoc, hB, one_div]` |
| ~3613 | `mul_assoc`, `mul_left_comm` | `simp [div_eq_mul_inv, mul_sum, mul_assoc, mul_left_comm, mul_comm]` |
| ~3888 | `mul_assoc` | same pattern |
| ~4216 | `mul_assoc` | same pattern |
| ~4230 | `mul_assoc` | same pattern |
| ~4565 | `mul_assoc` | same pattern |
| ~4579 | `mul_assoc` | same pattern |
| ~4593 | `mul_assoc` | same pattern |
| ~4795 | `mul_assoc` | same pattern |
| ~4809 | `mul_assoc` | same pattern |
| ~4823 | `mul_assoc` | same pattern |
| ~5475 | `mul_assoc` | same pattern |
| ~5489 | `mul_assoc` | same pattern |

**Pattern:** Many lines have `simp [div_eq_mul_inv, mul_sum, mul_assoc, mul_left_comm, mul_comm]` but only `mul_comm` is used.

#### Deprecated API (1 occurrence)

| Line | Current | Replacement |
|------|---------|-------------|
| 1939 | `Finset.exists_ne_of_one_lt_card` | `Finset.exists_mem_ne` |

#### Useless Tactics (2 occurrences)

| Line | Issue |
|------|-------|
| ~1934 | `'decide' tactic does nothing` — remove trailing `decide` |
| ~1934 | `this tactic is never executed` — unreachable branch |

### 🔄 TODO — Structural (In Progress)

**Density Bound Extraction:**
- [x] Extract mod 25 density bounds — **8/8 DONE** via `residue_class_card_bound_of_subset` (line ~3623)
- [ ] Create `residue_class_card_bound100_of_subset` helper for mod 100 pattern
- [ ] Replace 4 mod 100 blocks (lines 5070, 5148, 5295, 5369) with new helper

**Other Cleanup:**
- [ ] Consider grouping heavy-computation sections with shared `set_option` block
- [ ] Move `open Filter Finset` (line 2428) to header with other opens

**Priority:** MEDIUM — Active refactoring in progress.

---

## Build Performance Notes

- Full build: ~12-15 minutes (first build with cache miss)
- Incremental: ~30 seconds (with warm cache)
- Slowest sections: Prime sum computations in Section 8 (lines 2540-2700)

---

## Expert-Level Structural Assessment

An honest evaluation of the code architecture vs. what an expert Lean developer would do.

### What's Actually Fine (Standard Lean Practice)

| Pattern | Verdict | Notes |
|---------|---------|-------|
| `SawhneyMainAt` → `sawhney_main` → `problem_848_resolved` | ✅ Standard | Define prop, prove it, use it. NOT circular. |
| Exact rational constants (`offPrimeDen`, `diagPrimeDen`) | ✅ Correct | Ugly but necessary for formal math |
| `natToNum` workaround | ✅ Legitimate | Required for kernel reduction |
| List-based prime enumeration | ✅ Smart | Avoids Finset permutation explosion |
| Large `sawhney_main` theorem | ⚠️ Acceptable | Works, but harder to maintain |

### What an Expert Would Do Differently

| Issue | Current State | Expert Approach |
|-------|---------------|-----------------|
| **Proof modularity** | `sawhney_main` is 2000+ lines | Break into 10-15 smaller lemmas that compose |
| **Repeated density bounds** | `hA7_bound`/`hA18_bound` copy-pasted 5+ times | Extract to `density_bound_for_residue_class` helper |
| **Computation isolation** | Heavy prime sums mixed with proof logic | Separate file `PrimeSums.lean` with precomputed values |
| **Blueprint documentation** | None | Human-readable outline linking to code (like Tao's PFR) |
| **Tactic DRY** | Same 10-line tactic blocks repeated | Custom tactic or `repeat`/`all_goals` patterns |

### Identified Spaghetti (Cosmetic, Not Logical)

1. **Case-split explosion in `sawhney_main`** — Many `by_cases` branches with nearly identical logic. Could abstract the common pattern.

2. **Inline `have` chains** — Long sequences of `have h1 ... have h2 ... have h3 ...` that could be standalone lemmas with descriptive names.

3. **Scattered `set_option maxHeartbeats`** — Should be consolidated or heavy lemmas restructured.

### Bottom Line

The code is **working-but-unpolished** — like a prototype vs. production code. Both compile. Both are correct. One is prettier.

For a 4-5 day effort with AI assistance, the structure is genuinely sound. The "spaghetti" is cosmetic, not logical. The proof is valid.

---

## Historical Note (For Reviewers)

The `natToNum` breakthrough was discovered by GPT-5.2 agent during collaborative development.

All three files (`Problem848.lean`, `Problem848_FINAL.lean`, `Problem848_REFACTOR.lean`) contain the same proven formalization with:
- **0 native_decide** (Mathlib compliant)
- **0 sorry** (fully proved)
- **0 axioms** (no additional axioms beyond Lean's type theory)

---

## Documentation Debt (Readability)

Per [Mathlib Documentation Style Guide](https://leanprover-community.github.io/contribute/doc.html) and [Library Style Guidelines](https://leanprover-community.github.io/contribute/style.html):

### 🔲 File-Level Documentation

Mathlib expects a file header with structure:
```lean
/-!
# Problem 848: Erdős-Sárközy Squarefree Products

## Main definitions
- `NonSquarefreeProductProp` - The non-squarefree product property
- `A₇`, `A₁₈` - Candidate extremal sets
- `SawhneyMainAt` - Parameterized stability theorem

## Main statements
- `sawhney_main` - Proof of SawhneyMain (∃ η N₀, stability holds)
- `problem_848_resolved` - Final resolution for N ≥ N₀

## Implementation notes
- Uses `Num.Prime` for kernel-efficient primality
- Exact rational arithmetic via explicit denominators

## References
- Sawhney-Sellke (2025), arXiv:2511.16072
- erdosproblems.com/848

## Tags
number theory, squarefree, Erdős, extremal combinatorics
-/
```

**Status:** NOT DONE — Current file has basic header but not Mathlib-compliant structure.

### 🔲 Definition Docstrings

The `docBlame` linter flags definitions without docstrings. Key definitions needing documentation:

| Definition | Current | Needed |
|------------|---------|--------|
| `δ` (in `sawhney_main`) | Inline comment only | Explain: slack parameter for prime counting error |
| `N₀` | Inline comment only | Explain: threshold from `exists_primeCounting_le_mul_nat` |
| `SawhneyMainAt` | Has docstring ✅ | — |
| `NonSquarefreeProductProp` | Has docstring ✅ | — |
| `offPrimeDen`, `diagPrimeDen` | No docstring | Explain: denominators for exact ∑(1/p²) computation |
| `natToNum` | Has docstring ✅ | — |

### 🔲 Proof Strategy Documentation

Add section comments explaining the proof structure:
```lean
/-! ### Step 1: Establish density slack
    We use the prime counting function bound to get room for error. -/

/-! ### Step 2: Case analysis on A*
    Split into cases based on whether A* is empty, contains evens, etc. -/
```

### Best Practices Reference

From [Mathlib Style Guide](https://leanprover-community.github.io/contribute/style.html):
- Lines ≤ 100 characters
- Docstrings start with full sentence, tactic as subject
- Use `/-!` for module docs, `/--` for definition docs
- Include "Examples:" section in code blocks where helpful

**Priority:** MEDIUM — Not required for correctness, but improves maintainability and reviewer experience.

---

## Next Steps

1. **If submitting to Mathlib:** Address structural debt (maxHeartbeats, extract helpers)
2. **If keeping as standalone proof:** ✅ **DONE** — REFACTOR is production-ready
3. **For publication:** Consider extracting the `natToNum` technique as a reusable pattern
4. **For readability:** Add file header and definition docstrings per Mathlib style

---

## Summary (2026-01-30)

### Phase 1: Linter Cleanup ✅ COMPLETE

| Before | After |
|--------|-------|
| ~50 linter warnings | **0 warnings** |
| 1 deprecated API | **0 deprecated** |
| Tab characters present | **0 tabs** |
| Build: ✅ | Build: ✅ |

**Time spent:** ~10 hours (overnight run)
**Approach:** Iterative small changes with verification after each batch
**Key learning:** `simpa` ≠ `simp` — agent learned this the hard way and recovered

### Phase 2: Structural Refactoring 🔄 IN PROGRESS

| Pattern | Blocks | Replaced | Remaining | Helper |
|---------|--------|----------|-----------|--------|
| Mod 25 | 8 | **8** | 0 ✅ | `residue_class_card_bound_of_subset` |
| Mod 100 | 4 | 0 | **4** | Needs new helper |
| **Total** | 12 | **8** | **4** | — |

| Metric | Start | Current | Target |
|--------|-------|---------|--------|
| Total lines | 5594 | **5476** | ~5200 (est.) |

**Approach:** Extract helpers for each pattern, replace duplicates one-by-one with build verification.

**Current status:**
- Mod 25 pattern: ✅ COMPLETE (8/8)
- Mod 100 pattern: 🔄 Need to create `residue_class_card_bound100_of_subset` helper, then replace 4 blocks at lines 5070, 5148, 5295, 5369
