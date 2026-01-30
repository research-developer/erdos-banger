# Problem 848 Refactor Notes (Presentation + SSOT)

**Date:** 2026-01-29
**Status:** ✅ BUILDS CLEAN — All 3 files verified identical (modulo namespace)
**Scope:** This document is the SSOT for the **Problem 848 Lean formalization**.

---

## Files Status

| File | Namespace | Status | Purpose |
|------|-----------|--------|---------|
| `Problem848.lean` | `Erdos.Problem848` | ✅ Builds | **Primary** — externally linked |
| `Problem848_FINAL.lean` | `Erdos.Problem848_FINAL` | ✅ Builds | **Backup** — externally linked |
| `Problem848_REFACTOR.lean` | `Erdos.Problem848_workbench` | ✅ Builds | **Sandbox** — for cleanup experiments |

All three files are **byte-identical** except for namespace declarations.

### Verification Commands

```bash
cd /Users/ray/Desktop/CLARITY-DIGITAL-TWIN/erdos-banger/formal/lean
source ~/.elan/env

# Build all three
lake build Erdos.Problem848
lake build Erdos.Problem848_FINAL
lake build Erdos.Problem848_workbench

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

- [ ] Move all `open scoped` to file header (after imports)
- [ ] Replace `simpa` → `simp` where linter suggests (~35 occurrences)
- [ ] Remove unused simp arguments (~15 occurrences)
- [ ] Replace deprecated `Finset.exists_ne_of_one_lt_card` → `Finset.exists_mem_ne`
- [ ] Extract repeated `hA7_bound`/`hA18_bound` patterns to helper lemma
- [ ] Consider grouping heavy-computation sections with shared `set_option` block

**Priority:** LOW — The file builds and proves the theorem. Cleanup is for presentation only.

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

## Next Steps

1. **If submitting to Mathlib:** Apply cleanup checklist, reduce maxHeartbeats
2. **If keeping as standalone proof:** Current state is production-ready
3. **For publication:** Consider extracting the `natToNum` technique as a reusable pattern
