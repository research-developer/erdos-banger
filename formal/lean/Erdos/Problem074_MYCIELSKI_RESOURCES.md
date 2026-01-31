# Problem 074 - Mycielski Graphs Approach

## ⚠️ STATUS: REFUTED ⚠️

**The Mycielski approach DOES NOT WORK for the √n bound.**

A concrete counterexample already occurs at **M₄** (the Grötzsch graph):
- **n = 11 vertices, m = 20 edges**
- **MaxCut = 16**
- **ebip = 20 - 16 = 4 edge deletions needed**
- **Nat.sqrt 11 = 3**
- **4 > 3 → VIOLATES √n bound**

Even worse: **M₅** has `n=23, m=71, MaxCut=55, ebip=16, Nat.sqrt 23=4`.

**Reproducible proof:** `scripts/mycielski_sqrt_test.py`

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

Run:

```bash
python3 scripts/mycielski_sqrt_test.py
```

---

## Takeaway

Mycielski graphs are triangle-free with unbounded chromatic number, but they are not
“close enough” to bipartite in the absolute-error sense needed for `f(n)=√n`.

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
