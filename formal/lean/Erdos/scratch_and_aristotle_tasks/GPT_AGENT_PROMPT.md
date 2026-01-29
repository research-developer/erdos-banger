# GPT Agent Task: Eliminate All `native_decide` from Lean 4 Proof

## MISSION
Eliminate ALL remaining 11 `native_decide` calls from a Lean 4 proof of Erdős Problem 848. The proof is mathematically valid (0 errors, 0 sorries) but uses `native_decide` which is **banned in Mathlib** (adds `Lean.ofReduceBool` axiom). Goal: 0 `native_decide` for community acceptance.

## CONTEXT

### What is this proof?
- **Erdős Problem 848**: Proves bounds on sets where all pairwise products +1 are non-squarefree
- **3900+ lines** of Lean 4 code, formalizing Sawhney-Sellke 2025 resolution
- **Currently compiles clean**: 0 errors, 0 sorries
- **Progress so far**: Reduced from 43 → 11 `native_decide` (74% done)

### Why does this matter?
- Mathlib has a linter that BANS `native_decide`
- Terence Tao's PFR proof has 0 `native_decide`
- Critics on the PR (formal-conjectures repo) flagged this as a concern
- Getting to 0 `native_decide` = proof meets gold standard

## YOUR WORKING FILES

```
/Users/ray/Desktop/CLARITY-DIGITAL-TWIN/erdos-banger/formal/lean/
├── Erdos/
│   ├── Problem848_GPT.lean          # YOUR SANDBOX - edit this freely
│   ├── Problem848_Refactor.lean     # Reference (don't edit)
│   ├── Problem848.lean              # Original (DO NOT TOUCH)
│   ├── Problem848_FINAL.lean        # Backup (DO NOT TOUCH)
│   └── scratch_and_aristotle_tasks/ # Scratch files for testing
│       ├── test_not_squarefree.lean # Working examples
│       └── test_prime127.lean       # Working examples
```

## COMPILE COMMAND (RUN FREQUENTLY!)

```bash
cd /Users/ray/Desktop/CLARITY-DIGITAL-TWIN/erdos-banger/formal/lean
source ~/.elan/env
lake build Erdos.Problem848_GPT
```

**CRITICAL**: Compile after EVERY change. If it fails, revert immediately.

## THE 11 REMAINING `native_decide` CALLS

### TIER A: Finite Set Equality (5 calls) - HARD but tractable

| Line | Lemma | What it proves |
|------|-------|----------------|
| 733 | `diag_cand_50` | `DiagonalCandidates 50 = {7, 18, 32, 38, 41, 43}` |
| 735 | `diag_cand_100` | `DiagonalCandidates 100 = {7, 18, 32, 38, 41, 43, 57, 68, 70, 82, 93, 99}` |
| 738 | `no_triple_works_50` | No triple in {0..49} has the NonSquarefreeProductProp |
| 742 | `no_triple_in_candidates` | No 3-element subset of {7,18,32,38,41,43} works |
| 747 | `no_five_in_candidates_100` | No 5-element subset of the 12-element set works |

**Why `decide` fails**: These depend on `Squarefree` which uses `Nat.minSqFac` with `Option` pattern matching. The kernel gets stuck.

### TIER B: Precomputed Rational Bounds (6 calls) - VERY HARD

| Line | Lemma | What it proves |
|------|-------|----------------|
| 992 | `diagPrimesCoarse_sum_eq` | ∑(1/p²) for diagonal primes = precomputed rational |
| 996 | `offPrimesCoarse_sum_eq` | ∑(1/p²) for off-diagonal primes = precomputed rational |
| 1000 | `no5PrimesCoarse_sum_eq` | ∑(1/p²) for p≠5 primes = precomputed rational |
| 1012 | `diagPrimeSumCoarse_bound` | Numerical inequality with ~2000-digit rationals |
| 1033 | `offPrimeSumCoarse_bound` | Numerical inequality with ~2000-digit rationals |
| 1054 | `no5PrimeSumCoarse_bound` | Numerical inequality with ~2000-digit rationals |

**Why `decide` fails**: Kernel computation hits heartbeat/recursion limits on huge numbers.

## PROVEN PATTERNS THAT WORK

### Pattern 1: Proving a number is NOT squarefree
Show that some prime² divides it:

```lean
lemma not_squarefree_1025 : ¬ Squarefree 1025 := by
  intro h
  have hdiv : 5^2 ∣ 1025 := by norm_num
  have := h 5 hdiv
  norm_num at this
```

### Pattern 2: Proving a number IS squarefree (if prime)
```lean
import Mathlib.Tactic.NormNum.Prime

lemma squarefree_127 : Squarefree 127 := by
  have h : Nat.Prime 127 := by norm_num
  exact h.squarefree
```

### Pattern 3: Case split on finite set membership
```lean
lemma pair_32_43_works : NonSquarefreeProductProp ({32, 43} : Finset ℕ) := by
  intro a ha b hb
  simp only [Finset.mem_insert, Finset.mem_singleton] at ha hb
  rcases ha with rfl | rfl <;> rcases hb with rfl | rfl
  · -- case a=32, b=32
    simp only [show 32 * 32 + 1 = 1025 by norm_num]
    exact not_squarefree_1025
  -- ... etc for each case
```

## STRATEGY SUGGESTIONS

### For Tier A (Finite Sets):

1. **Start with `diag_cand_50`** - "only" 50 numbers to check
2. For each n ∈ {0..49}, prove either:
   - `Squarefree (n * n + 1)` (n NOT in DiagonalCandidates), OR
   - `¬ Squarefree (n * n + 1)` (n IS in DiagonalCandidates)
3. Use helper lemmas, don't inline everything
4. Consider: Can you generate these proofs programmatically?

**Key insight**: The candidates are {7, 18, 32, 38, 41, 43}. So you need:
- 6 proofs that n*n+1 is NOT squarefree (for n in the set)
- 44 proofs that n*n+1 IS squarefree (for n not in the set)

**Research needed**:
- Is there a Mathlib tactic that helps with squarefree proofs?
- Can `norm_num` extensions handle this?
- Search for "Squarefree" "decide" "native_decide" issues in Lean 4 / Mathlib

### For Tier B (Precomputed Bounds):

These are harder. Options:
1. **Interval arithmetic**: Prove bounds using rational interval enclosures
2. **Certified computation**: Use Mathlib's `NNRat` or similar
3. **Restructure the proof**: Maybe the bounds can be derived differently?
4. **External verification**: Keep `native_decide` but add extensive documentation (last resort)

**Research needed**:
- How do other Mathlib proofs handle large numeric bounds?
- Look at Polynomial Freiman-Ruzsa (PFR) proof techniques
- Search Zulip/Mathlib discussions for "native_decide" "large computation"

## USEFUL MATHLIB IMPORTS

```lean
import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Nat.Squarefree
import Mathlib.Tactic.NormNum.Prime
import Mathlib.Tactic.IntervalCases
import Mathlib.Tactic.FinCases
```

## WEB SEARCH SUGGESTIONS

1. "Lean 4 Mathlib Squarefree decide native_decide"
2. "Lean 4 eliminate native_decide finite computation"
3. "Mathlib large rational computation norm_num"
4. "Lean 4 interval arithmetic bounds"
5. "Mathlib Squarefree minSqFac decidable"
6. "Lean 4 fin_cases tactic exhaustive"

## DELIVERABLES

1. **Problem848_GPT.lean** that compiles with 0 `native_decide`
2. **Helper lemmas** in scratch files for testing individual pieces
3. **Documentation** of any techniques discovered

## CONSTRAINTS

- **Lean version**: 4.27.0 (see `lean-toolchain`)
- **Mathlib**: Current version in lakefile
- **DO NOT** edit Problem848.lean, Problem848_FINAL.lean, or Problem848_Refactor.lean
- **DO** create scratch files in `scratch_and_aristotle_tasks/` for testing

## SUCCESS CRITERIA

```bash
grep -c "native_decide" Problem848_GPT.lean
# Output: 0

lake build Erdos.Problem848_GPT
# Output: Build completed successfully
```

## FINAL NOTE

This is a real mathematical proof that will be submitted to the formal-conjectures repository. Quality matters. If you discover that some `native_decide` truly cannot be eliminated without major proof restructuring, document why clearly. But try hard first - the patterns above have already eliminated 32 of 43 calls.

Good luck!
