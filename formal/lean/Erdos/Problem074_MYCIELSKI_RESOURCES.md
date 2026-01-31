# Problem 074 - Mycielski Graphs Approach

## Status: 🧪 CANDIDATE (Low Priority)

**Hypothesis:** Mycielski graphs might satisfy sublinear edge-deletion bounds due to their recursive structure.

**Expected Outcome:** LIKELY TO FAIL - probably linear (too dense)

---

## What Are Mycielski Graphs?

The Mycielski construction produces triangle-free graphs with arbitrarily large chromatic number.

### Construction

- **M₁** = K₁ (single vertex)
- **M₂** = K₂ (single edge)
- **M₃** = C₅ (5-cycle, χ = 3)
- **M₄** = Grötzsch graph (11 vertices, χ = 4)
- **Mₖ₊₁** from **Mₖ**:
  1. Take Mₖ with vertices v₁, ..., vₙ
  2. Add n new vertices u₁, ..., uₙ (shadow vertices)
  3. Add one special vertex w
  4. Connect uᵢ to N(vᵢ) (neighbors of vᵢ)
  5. Connect w to all uᵢ

### Properties

| Property | Value |
|----------|-------|
| **χ(Mₖ)** | k |
| **Triangle-free** | Yes |
| **Vertices** | 3·2^(k-2) - 1 |
| **Edges** | Θ(n^1.585) where n = |V| |

---

## Why It Might Work

1. **Triangle-free**: Only odd cycles ≥5 block bipartiteness
2. **Recursive structure**: Similar to Burling
3. **Classic construction**: Well-studied, good formalization potential

## Why It Probably Won't Work

1. **Edge density**: O(n^1.585) edges means dense enough that MAX-CUT likely only captures O(n) edges below total
2. **No geometric structure**: Unlike Burling (box intersection) or Twincut (vertex cutsets), Mycielski is purely combinatorial
3. **Known to be "bad"**: Listed as "likely too dense" in main resources

---

## Computational Test

Before formalizing, compute:

```python
for k in [3, 4, 5, 6]:
    M = mycielski_graph(k)
    n = M.number_of_vertices()
    for size in range(3, min(n+1, 50)):
        max_ebip = 0
        for A in induced_subgraphs(M, size):
            ebip = edges(A) - max_cut(A)
            max_ebip = max(max_ebip, ebip)
        print(f"M_{k}, n={size}: ebip={max_ebip}, √n={sqrt(size):.2f}, ratio={max_ebip/sqrt(size):.2f}")
```

**If ratio → constant as n grows**: Linear in √n - promising!
**If ratio → ∞**: Fails √n bound - move on.

---

## Priority: LOW

Given that:
- Mycielski is "obviously dense"
- Literature suggests linear edge-deletion
- Other approaches remain unexplored

**Recommendation:** Test computationally first before any formalization effort.

---

## References

| Source | Content |
|--------|---------|
| Mycielski 1955 | Original construction |
| West "Introduction to Graph Theory" | Standard reference |
| Mathlib `Combinatorics.SimpleGraph.Mycielski` | May exist or be easy to add |

---

## Related Files

- `Problem074_RESOURCES.md` - Main tracking
- `Problem074_BURLING_RESOURCES.md` - Burling (REFUTED)
- `Problem074_TWINCUT_RESOURCES.md` - Twincut (REFUTED)
