# Problem 074 - Twincut Graph Approach Resources

## Status: CANDIDATE - Not Yet Tested

This document covers the **twincut graph approach** to Erdős Problem #74 ($500 prize).

**Previous attempts:**
- `Problem074_RESOURCES.md` - Rödl/Kneser (LINEAR case, DONE but no prize)
- `Problem074_BURLING_RESOURCES.md` - Burling graphs (REFUTED - disjoint cycle packing)

---

## Problem Statement

**Erdős Problem #74** (Open, $500 prize)

Let $f(n) \to \infty$ (possibly very slowly). Is there a graph of infinite chromatic number such that every finite subgraph on $n$ vertices can be made bipartite by deleting at most $f(n)$ edges?

**Target:** $f(n) = \sqrt{n}$ (sublinear)

---

## Why Burling Failed

The Burling NEXT-B construction creates **disjoint copies** of previous graphs:
- G₃ contains 2 disjoint C₅'s
- G₄ contains 9+ copies of G₃ → 18+ disjoint C₅'s
- Can pack t vertex-disjoint odd cycles → need t edge deletions → fails √n

**Key insight:** Any successful construction must **prevent packing many disjoint odd cycles**.

---

## What Twincut Graphs Are

From **arXiv:2304.04296** (Bonnet, Bourneuf, Duron, Geniet, Thomassé, Trotignon 2023):

> "A tamed family of triangle-free graphs with unbounded chromatic number"

### Key Properties

| Property | Value | Why It Matters |
|----------|-------|----------------|
| **Triangle-free** | ✅ Yes | Same as Burling |
| **χ unbounded** | ✅ χ(Gₖ) = k | Same as Burling |
| **Hereditary** | ✅ Yes | Good for induction |
| **Structural constraint** | Every graph has twins OR vertex cutset ≤ 2 | **CRITICAL** |

### The Critical Difference

**Burling:** Recursive construction creates disjoint copies → many disjoint odd cycles

**Twincut:** Every non-trivial graph either:
1. Contains a pair of non-adjacent twins, OR
2. Has an edgeless vertex cutset of size at most 2

The **small vertex cutset** property might prevent disjoint odd cycle packing!
- If the graph can only be separated by ≤2 vertices
- Odd cycles must "pass through" these bottlenecks
- Cycles are forced to overlap/share edges

---

## Why Twincut Might Work

### The Anti-Packing Hypothesis

For √n bound, we need: ≤ √n vertex-disjoint odd cycles in any n-vertex subgraph.

If twincut graphs have vertex cutsets of size ≤2:
- The graph is "almost 2-connected"
- Odd cycles can't be isolated in disjoint components
- Cycles must share vertices/edges near the cutset

This is exactly the "bottleneck structure" that was hoped for in Burling but didn't exist.

### Edge-Critical Property

The authors also prove: **every twincut graph is edge-critical**.

This means removing any edge decreases the chromatic number. This tight structure might help with the edge-deletion bound.

---

## Research Questions

1. **Does the cutset property prevent disjoint odd cycle packing?**
   - If G has cutset ≤2, can we bound vertex-disjoint odd cycles?
   - Conjecture: ≤ O(√n) disjoint odd cycles in n-vertex twincut subgraph

2. **Explicit construction of twincut graphs**
   - Need adjacency lists for G₃, G₄ to test computationally
   - Paper should have explicit construction

3. **Comparison to Burling**
   - Both triangle-free, both χ-unbounded
   - Twincut has cutset constraint, Burling has disjoint copies
   - Twincut might avoid the fatal flaw

---

## Key References

| Source | URL | Content |
|--------|-----|---------|
| arXiv:2304.04296 | https://arxiv.org/abs/2304.04296 | Twincut graphs (main paper) |
| Bonnet-Thomassé 2023 | Same | Detailed construction |

### Authors
- Edouard Bonnet
- Romain Bourneuf
- Julien Duron
- Colin Geniet
- Stéphan Thomassé
- Nicolas Trotignon

---

## Action Plan

### Phase 1: Understand the Construction
- [ ] Read arXiv:2304.04296 in detail
- [ ] Extract explicit construction of G₁, G₂, G₃, G₄
- [ ] Understand the "twin" and "cutset" properties

### Phase 2: Computational Testing
- [ ] Implement twincut graph generator in Python
- [ ] Test √n bound on small examples (n ≤ 20)
- [ ] Compare to Burling counterexample

### Phase 3: Theoretical Analysis
- [ ] Prove/disprove: cutset ≤ 2 → bounded disjoint odd cycles
- [ ] If promising: attempt Lean formalization
- [ ] If fails: document and find next candidate

---

## Lean Files

| File | Purpose | Status |
|------|---------|--------|
| `Problem074_twincut.lean` | Clean template | ✅ Created, compiles |
| `Problem074_twincut_experimental.lean` | **ACTIVE** work | ✅ Created, 2 sorries |

### What's in the Lean files
- Twins definition (`areTwins`, `hasTwins`)
- Edgeless cutset definition
- Vertex cutset definition
- Axiomatized: `twincut_triangle_free`, `twincut_chromatic_number`, `twincut_structure`
- Main theorem: `twincut_sublinear_attempt` (sorry - needs computational testing first)

---

## Session Log

### 2026-01-30
- Created this resource file after Burling approach was refuted
- Identified twincut graphs as next candidate from Exa/web search
- Key hypothesis: small cutset → forced cycle overlap → √n bound might hold
- Created `Problem074_twincut.lean` and `Problem074_twincut_experimental.lean`
- Both compile (2 sorries expected)
