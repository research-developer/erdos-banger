# Problem Candidates

Tracking which Erdos problems we're considering working on and why.

Last updated: 2026-01-27

---

## Top Candidates (Open + Formalized)

### Tier 1: Best for AI-assisted work

| # | Prize | Topic | Why Consider |
|---|-------|-------|--------------|
| **848** | $0 | Number theory, squarefree | Labeled decidable; “effective N₀ + finite check” shape. Modular (±7 mod 25) and certificate-friendly (SAT/DRAT + Lean). |
| **74** | $500 | Graph theory, chromatic | Constructive, graph algos are AI-friendly. Related solved: #57, #58, #63 |
| **564** | $500 | Ramsey hypergraphs | Well-studied area, combinatorial. Related solved: #645 (Lean proof available) |
| **20** | $1,000 | Sunflower lemma | Pure combinatorics, finite structures. Related: #1026 (AI-solved) |

### Tier 2: Geometry (computational potential)

| # | Prize | Topic | Why Consider |
|---|-------|-------|--------------|
| **89** | $500 | Distinct distances | Guth-Katz adjacent, computational aspects |
| **90** | $500 | Unit distances | Related to 89 |
| **92** | $500 | Equidistant points | Related to 89, 90 |

### Tier 3: High prize but hard

| # | Prize | Topic | Why Consider |
|---|-------|-------|--------------|
| **142** | $10,000 | AP density | Szemeredi territory - very hard but huge payoff |
| **3** | $5,000 | Erdos-Turan conjecture | Famous, would be major result |

---

## Counterexample Candidates (Disproved - Lean-Friendly)

These are **disproved** problems where the proof is a finite counterexample. Ideal for Lean formalization because:
- No asymptotics or density arguments
- No heavy theorems (sieve, analytic NT)
- Pure computation + exhaustive verification
- `norm_num`/`decide`/`native_decide` friendly

Local verification: `uv run python scripts/verify_counterexample_candidates.py`

### Tier A: Single Counterexample (Easiest)

| # | Status | Topic | Counterexample | Lean Feasibility |
|---|--------|-------|----------------|------------------|
| **399** | disproved | factorials, powers | `10! = 48^4 - 36^4` | ⭐⭐⭐ One equality, `norm_num` can verify |
| **649** | disproved | prime factors | `p=2, q=7` fails: `2^k ≢ -1 (mod 7)` | ⭐⭐⭐ Mod arithmetic cycle check |

### Tier B: Finite Search Space

| # | Status | Topic | Counterexample | Lean Feasibility |
|---|--------|-------|----------------|------------------|
| **231** | disproved | abelian squares | 15-char string on 4 symbols: `121312141213121` | ⭐⭐ Need ~50 LOC infrastructure for Parikh vectors |
| **794** | disproved | hypergraphs | 9 vertices; 28 edges: all triples with one vertex in each of `{1,2,3}`, `{4,5,6}`, `{7,8,9}` plus `{1,2,3}` | ⭐⭐ Exhaustive check over 126+126 subsets |

### Tier C: Already Formalized (Study Template)

| # | Status | Topic | Why Study |
|---|--------|-------|-----------|
| **645** | proved (Lean) | Ramsey, AP | Discrete forcing argument, good pattern for combinatorial proofs (`formal/lean/Upstream/FormalConjectures/ErdosProblems/645.lean`) |

---

## Solved Problems to Study First

These are solved problems that share techniques with our candidates:

| Solved | Status | Relates To | Shared Tags |
|--------|--------|------------|-------------|
| #57, #58, #63 | proved | #74 | graph theory, chromatic, cycles |
| #645 | proved (Lean) | #564, #592, counterexample tier | ramsey theory, discrete forcing |
| #198 | disproved (Lean) | #30, #39, #41 | sidon sets |
| #728 | proved (Lean) | general | AI-solved Jan 2026, factorial |
| #1026 | solved (Lean) | #20 | AI-solved Dec 2025, combinatorics |
| #399 | disproved | counterexample tier | factorials, powers, `norm_num` friendly |

---

## Decision Log

### 2026-01-25

- Synced 33 problems to local database
- Imported 26 Lean formalizations
- Identified #74, #564, #20 as top candidates
- Strategy: Study solved relatives before attempting open problems

### 2026-01-26

- Picked #848 (Erdős–Sárközy) as the first "2026 AI + human collab" target
- Rationale: explicit-threshold grind + finite verification with checkable certificates
- Added "Counterexample Candidates" section with 5 disproved problems (#399, #649, #231, #794, #645)
- Strategy shift: "disproved by finite counterexample" problems are ideal for Lean because they avoid asymptotics and heavy theorems

---

## Next Steps

1. [x] Pick one problem to focus on (#848)
2. [ ] Read the related solved proofs
3. [ ] Understand the Lean formalization
4. [ ] Attempt partial progress or full proof
