# Synthesis: Problem 0074

## Problem Statement

Let $f(n) \to \infty$ (possibly very slowly). Is there a graph of infinite chromatic number such that every finite subgraph on $n$ vertices can be made bipartite by deleting at most $f(n)$ edges?

**Status:** Open
**Prize:** $500

## Critical Finding: Related but Different Problems

⚠️ **IMPORTANT**: There are TWO closely related formulations in the literature:

| Formulation | Statement | Status |
|-------------|-----------|--------|
| **Problem #74 (edge deletion)** | Can we make n-vertex subgraphs bipartite by deleting ≤ f(n) edges? | **OPEN** |
| **EHS Question (chromatic growth)** | Can chromatic number of n-vertex subgraphs grow arbitrarily slowly? | **SOLVED** (Lambie-Hanson 2019) |

**Lambie-Hanson (arXiv:1902.08177)** solved the chromatic growth question in ZFC:
> For every function $f:\mathbb{N} \rightarrow \mathbb{N}$, there is a graph $G$ with $\chi(G) = \aleph_1$ such that for every $k \geq 3$, every subgraph with fewer than $f(k)$ vertices has chromatic number $< k$.

The edge deletion formulation (Problem #74) remains **OPEN**. Making a graph bipartite (χ ≤ 2) by edge deletion is stronger than having slowly growing chromatic number.

**Key insight**: Lambie-Hanson's techniques (club guessing, Specker graphs) may still be relevant to Problem #74.

## Lean Formalization Structure

Location: `formal/lean/Upstream/FormalConjectures/ErdosProblems/74.lean`

### Key Definitions

1. **`edgeDistancesToBipartite`** - Set of edge counts that make a subgraph bipartite
2. **`minEdgeDistToBipartite`** - Minimum edges to delete (infimum of above set)
3. **`subgraphEdgeDistsToBipartite`** - Set of minimum distances for subgraphs of size n
4. **`maxSubgraphEdgeDistToBipartite`** - Maximum over all n-vertex subgraphs (Definition 3.1 in EHS82)

### Supporting Lemmas (PROVED)

1. **`edgeDistancesToBipartite_nonempty`** - The set is always non-empty (trivial: delete all edges)
2. **`subgraphEdgeDistsToBipartite_bddAbove`** - Bounded above by $\binom{n}{2}$

### Main Theorems (OPEN)

1. **`erdos_74`** - Main conjecture about infinite chromatic graphs with slow-growing $f(n)$
2. **`erdos_74.variants.sqrt`** - Variant asking specifically about $f(n) = \sqrt{n}$

## Ingested Literature (Clean LaTeX Extracts)

### Primary Sources

| arXiv | Title | Authors | Year | Relevance |
|-------|-------|---------|------|-----------|
| **1902.08177** | On the growth rate of chromatic numbers of finite subgraphs | Lambie-Hanson | 2019 | **Solved chromatic growth question** - techniques may apply |
| **1306.5167** | The history of degenerate (bipartite) extremal graph problems | Füredi, Simonovits | 2013 | Survey of bipartite extremal problems |
| **2203.13833** | When removing an independent set is optimal for reducing chromatic number | Cambie, Haslegrave, Kang | 2022 | Chromatic reduction techniques |

### Older Papers (Scanned PDFs, not extracted)

- **EHS82**: Erdős, Hajnal, Szemerédi. "On almost bipartite large chromatic graphs" (1982) - KEY PAPER
- **Erdős-Hajnal 1985**: "Chromatic number of finite and infinite graphs and hypergraphs" - DOI: 10.1016/0012-365x(85)90148-7

## Key Partial Results (from erdosproblems.com)

- **Rödl (1982)**: Such a graph exists when $f(n) = \epsilon n$ for any fixed $\epsilon > 0$
- **Open**: Even the case $f(n) = \sqrt{n}$ remains unresolved
- **Negative**: The statement fails for graphs with chromatic number $\aleph_1$

## Research Questions

1. What techniques from Lambie-Hanson can be adapted to the edge-deletion formulation?
2. Why does the statement fail for $\chi(G) = \aleph_1$ but possibly hold for countably infinite chromatic number?
3. Can Rödl's $f(n) = \epsilon n$ result be improved toward $\sqrt{n}$?
4. What is the relationship between chromatic number growth and edge-deletion distance to bipartite?

## Next Steps

- [x] Discover modern literature via Exa
- [x] Ingest arXiv papers with clean LaTeX
- [x] Identify relationship between formulations
- [ ] Study Lambie-Hanson's club guessing technique in detail
- [ ] Understand Rödl's 1982 construction
- [ ] Determine if chromatic growth → edge deletion reduction is possible
- [ ] Attempt to formalize partial results in Lean
