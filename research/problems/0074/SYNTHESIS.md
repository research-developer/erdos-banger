# Synthesis: Problem 0074

## Problem Statement

Let $f(n) \to \infty$ (possibly very slowly). Is there a graph of infinite chromatic number such that every finite subgraph on $n$ vertices can be made bipartite by deleting at most $f(n)$ edges?

**Status:** Open
**Prize:** $500

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

## Key Reference

- **EHS82:** Erdos, Hajnal, Szemeredi. "On almost bipartite large chromatic graphs" (1982), pp. 117-123
  - Definition 3.1 defines `maxSubgraphEdgeDistToBipartite`
  - Contains the foundational approach to this problem

## Ingested Literature

- Erdos & Hajnal, "Chromatic number of finite and infinite graphs and hypergraphs" (1985)
  - DOI: 10.1016/0012-365x(85)90148-7

## Research Questions

1. What is the current best known bound for $f(n)$?
2. Can we construct an explicit graph with the desired property for $f(n) = n^\epsilon$?
3. What techniques from EHS82 can be formalized?

## Next Steps

- [ ] Study the 1982 Erdos-Hajnal-Szemeredi paper construction
- [ ] Search for more recent progress on this problem
- [ ] Understand the relationship between chromatic number and bipartite substructure
- [ ] Attempt to fill in `sorry` using Claude Code subscription workflow
