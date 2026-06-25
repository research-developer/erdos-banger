# Erdős Attack — Tools, Methods & Formulas

A reference for the RationAll arsenal as applied to the Erdős-problems effort (Linear project
*Solve Erdos Problems*, issues MATH‑1…MATH‑24). Every formula here is from the verified
`rationall-math-reference` skill or a result established in the 2026‑06‑24 triage session.

---

## 0. The governing discipline — the zero‑float invariant

> **No floats pass through the computation pipeline.** State is integers, `fractions.Fraction`,
> or algebraic ring elements. Floats appear only at the final display boundary.

Every search, sieve, and certificate below is exact. This is what lets a "no counterexample found"
be trustworthy and a kernel certificate be sound.

---

## 1. The three edges (the tools)

### 1.1 decide‑and‑certify — category ↔ magma‑law ↔ Lean bridge

A deterministic engine (MCP server, backed by `Rationall-solver`) that decides implications between
**magma equational laws** over *all* magmas and emits a **kernel‑checkable Lean 4 certificate**
(TRUE) or a **finite counter‑model** (FALSE), in ~1 ms. Catalogue: **4,694 laws** (the Equational
Theories Project), ~99.995% covered. Substrate underneath: a **Klein‑four (V₄), 2,3‑smooth balanced
senary** engine — the same algebra as the RationAll rings.

Features (the tool surface): `recognize` (classify into a certifiable fragment), `certify_or_abstain`
(certify a magma implication, or recognize a single decidable Lean goal, or abstain),
`decide_implication` (full verdict + cert/counter‑model), `batch_decide`, `lookup_law`.

**Worked example (verified this session).** Associativity (law 4512) does **not** imply commutativity
(law 43): refuted by the right‑projection magma on `Fin 2`, table `[[0,1],[0,1]]` (`op a b = b`), with
a Lean cert emitted in **0.9 ms**; re‑checked pure‑kernel, axioms `[propext]`.

**Reach and limits (honest boundary, mapped on #647).**
- Abstains correctly on number‑theoretic universals (`∀n … τ …`) — *out of the certifiable fragment*.
- Recognizes **concrete closed** decidable goals (`47² % 24 = 1` → `by decide`).
- For a **universal** modular lemma (`∀ p prime>3, (p²−1)%24=0`) it over‑proposed `by omega` — but
  `omega` is *linear* and cannot handle `p²` or primality, so that tactic would **fail** the kernel.
  The `"verified": "construction-only"` field is load‑bearing: proposals are not certificates.
  Lesson: substantive NT lemmas need a real Mathlib proof, not the engine.

### 1.2 FlowAngle — exact computation of enumerable irrationals & transcendentals

The dodecagonal architecture computes algebraic/transcendental constants exactly, as ring elements or
Lerch values, never as floats. Anchored on the **conjugate fundamental unit of `Z[√3]`**:

```
ε̄ = 2 − √3 ≈ 0.26795      ε = 2 + √3 ≈ 3.73205
ε · ε̄ = 1                 N(ε̄) = 2² − 3·(−1)² = 1     (on the unit hyperbola)
tan(π/12) = 2 − √3 = ε̄    arctan(ε̄) = π/12
```

**The π decomposition (flow = gravity):**
```
π = 12 · ε̄ · flow,     flow = Σ_{k≥0} (−1)^k · ε̄^(2k) / (2k+1)
π = 6 · ε̄ · Φ_L(−ε̄², 1, ½)          (Lerch transcendent form)
arctanh(ε̄) = ¼ ln 3                  (hyperbolic distance on the Poincaré disk)
```
The flow is the value of the 2‑D harmonic Green's function at the point fixed by the ring's unit —
proven four independent ways (`notebooks/flow_gravity_proof.py`).

**Supporting exact machinery:** the **trace map** `Tr(a+b√d) = 2a` projects ring irrationals to ℤ
without materializing a surd; the **Chebyshev recurrence** `T_k(c₁) = 2c₁T_{k−1} − T_{k−2}`
(`c₁ = 2cos(2π/n)`) generates rotations with zero drift; `rationall.sieve.recognize(x)` matches a float
back to its algebraic value. Relevance to Erdős: the irrationality cluster (MATH‑17…21:
`∑1/(t^n−1)`, `∑p_n/2^n`, `∑1/lcm`, `∑1/(n!−1)`, `∑1/(2^n−1)`) — all exact partial sums and continued
fractions, with Lerch/Lambert framing for the transcendence side.

### 1.3 Dozenal RNS super‑digit + bracketing prime sieve — exact prime structure

The twin primes **(11, 13) bracket the dozen 12**, two ways:
- **Additively:** `11 + 13 = 24` (the n=24 conjugate‑rotor period). `12 = [0,1,1]` in balanced ternary;
  zeroless straddle gives `13 = [+1,1,1]`, `11 = [−1,1,1]`.
- **Multiplicatively:** `11 · 13 = 143 = 12² − 1` — a Residue Number System. Because `143 ≡ −1 (mod 144)`,
  `S mod 144 = (S mod 143) − ⌊S/143⌋` (an **end‑around borrow**); the carry `C₁₄₃ ∈ {0,1,2}` is read from
  a redundant lane, not a magnitude compare.

`dozenal_rns_superdigit.py`: info lanes (11, 13), redundant lanes (17, 19) ⇒ exact base‑144 add/sub,
carry‑free SIMD ×, and **single‑lane RRNS error correction** (distance‑3: corrects 1 lane XOR detects 2).
The info residues are *free* syndromes — **casting out elevens** (base‑12 digit sum mod 11) and **thirteens**
(alternating digit sum mod 13). Exhaustively verified zero‑float (41472/41472 add & sub, 8008/8008 single‑lane
correction). The **conjugate gate** `σ: √3 → −√3`, `(a,b) ↦ (a,−b)`, is *proven* to be the operator swapping
`13 ↔ 11` while fixing the dozen — and it is the same gate as the free norm‑integrity check. Relevance:
twin/safe‑prime structure (#647 open core), prime sieves (MATH‑15/18), covering systems.

---

## 2. The exact‑arithmetic foundation (Z[√d] rings)

The workhorse ring `Z[√3] = {a + b√3}` (and generally `Z[√d]`):
```
mult:   (a₁,b₁)·(a₂,b₂) = (a₁a₂ + 3 b₁b₂,  a₁b₂ + a₂b₁)
norm:   N(a,b) = a² − 3b²            (∈ ℤ, multiplicative: N(xy)=N(x)N(y))
conj:   σ(a,b) = (a,−b)              (Galois automorphism √3 ↦ −√3)
inv:    1/(a+b√3) = (a−b√3)/(a²−3b²) (exact, via the norm)
```
**Multiplicativity of the norm is the self‑checking invariant** — if a product's norm ≠ the product of
norms, a bit flipped. The universal ring is `Z[√2,√3]` (n=12, the dozenal default); the algebraic tower
nests `Z ⊂ Z[√3],Z[√2] ⊂ Z[√2,√3]`, Galois group V₄.

**Concrete exact methods used in the Erdős searches:**
- **Divisor‑count sieve:** `for i in 1..N: τ[i::i] += 1` (NumPy int64) — exact `τ(m)` for all `m ≤ N`.
- **Prefix‑max:** `np.maximum.accumulate(m + τ)` realizes `max_{m≤k}(m+τ(m))` (used for #647 slack).
- **Exact rationals:** `fractions.Fraction` for unit‑fraction / prime‑reciprocal problems (MATH‑5, 22).
- **Snellius O(1/n⁴):** `s_in² = 2−c₁`, `s_out² = 2/(2−c₁)`, `S_n = (2 s_in + s_out)/3` (exact ring inversion).

---

## 3. The certify+Lean workbench (built this session — `certkit`, PR #2)

An **agent‑orchestrated** pipeline that turns a finite witness/counter‑model into a self‑contained
**core‑Lean `decide` proof** and re‑checks it with the Lean kernel:

```
problem ─► recognize/route ─► { certify‑MCP counter‑model → emit_countermodel
                              | exact sieve → emit_bounded_decide }
                                    └────► erdos lean check  ◄── SOLE trust anchor
                                              └─► record cert + #print axioms
```

`certkit/` modules: `lawlean.py` (flat magma law → `∀ … : Fin n, …` Lean prop), `emit_countermodel.py`
(counter‑model → `decide` proof), `emit_bounded_decide.py` (bounded NT fact → `decide`/`native_decide`),
`sieve647.py` (exact oracle).

**Witness‑pure trust model.** Prefer pure `decide` (kernel re‑runs it, **no extra axioms**); use
`native_decide` only when forced — it adds `Lean.ofReduceBool` (+`Lean.trustCompiler`) — and **always emit
`#print axioms`** so the trusted base is visible. The two golden certs make the delta concrete:
`assoc ⊭ comm` (axioms `[propext]`) and bounded #647 (`P647Bounded` no axioms / `P647BoundedNative`
`[ofReduceBool, trustCompiler]`).

**Toolchain gotcha (recorded):** `erdos lean check FILE --path certkit/lean` is the pass/fail **gate** but
**drops `#print axioms`** output; read axioms with `cd certkit/lean && lake env lean FILE`.

---

## 4. Problem‑classification method — the "decisive zone"

The dataset's status states are the **arithmetic‑hierarchy** classification of each formalized statement,
and they tell you where an exact engine is *decisive*:
- **`verifiable`** (Σ₁, "∃ witness") — if *true*, a finite search **finds it and settles it**.
- **`falsifiable`** (Π₁, "∀ n, P(n)") — if *false*, a finite search **finds the counterexample**.
- **`decidable`** (Δ) — an algorithm settles it outright.

**The trap:** most are *believed‑true* → already searched to huge bounds → we can only *extend*, not finish.
The decisive search only pays when the believed answer matches the finite direction (or when a structural
reduction + bounded cert + Mathlib proof closes it). The attack **lanes** (MATH backlog):
**A** closable‑niche NT (reduction + bounded cert + Mathlib), **B** exact computational search,
**C** FlowAngle irrationality, **D** primary‑pseudoperfect/Giuga, **E** famous falsifiable (extend/disprove).

---

## 5. Results & formulas established this session

### 5.1 #647 — the divisor‑window (MATH‑1)
Let `τ` = divisor count. Reformulate with **`slack(n) = max_{m<n}(τ(m) − (n−m))`** so that
`max_{m<n}(m+τ(m)) = n + slack(n)`, and "n is a solution" ⟺ `slack(n) ≤ 2`.

**Evidence (exact sieve, to 5×10⁷):** no solution `n>24`; the only `slack ≤ 3` cases are `{35,36,48,120}`
(all ≤ 120); `slack ≥ 5` for every `120 < n ≤ 5×10⁷`.

**Partial theorem (elementary, verified).** For `n>24` with `n−1` **not prime**, `∃ m<n` with `m+τ(m) ≥ n+3`:
- `τ(n−1) ≥ 4` ⇒ take `m = n−1`.
- else `n−1 = p²` (`p ≥ 5`); take `m = p²−1`. **`24 ∣ p²−1`** (odd ⇒ `p²≡1 (mod 8)`; `p∤3` ⇒ `p²≡1 (mod 3)`),
  and `24∣k ⇒ τ(k) ≥ τ(24) = 8`, so `m+τ(m) ≥ (n−2)+8 = n+6`.

**Open core = safe primes.** `n−1 = p` prime reduces to `p − 1 = 2q` (`q` prime), i.e. **`p` a safe prime /
`q` Sophie Germain** — exactly why #647 resists elementary closure (and a hook into the twin‑prime lattice).
Lean lemmas L1–L4 (incl. the `(ZMod 24)ˣ` squares‑to‑1 `decide`) are the MATH‑1 background proof.

### 5.2 #307 — primary pseudoperfect numbers (MATH‑22)
Searching prime sets `P, Q` with `(∑_{p∈P}1/p)(∑_{q∈Q}1/q) = 1`, the closest near‑miss
`∑1/p` over `{2,3,11,23,31} = 47057/47058 = 1 − 1/47058` is the **5th primary pseudoperfect number**
(OEIS **A054377**: 2, 6, 42, 1806, 47058 — prime sets of the identity **`1/N + ∑_{p|N} 1/p = 1`**;
`47058 = 2·3·11·23·31`). This is **structural, not a decimal artifact** — the product is an exact rational,
base‑invariant. Reciprocals `N/(N−1)` sit just above 1 and are unreachable as prime‑reciprocal sums ⇒ a
**Giuga/Znám‑type obstruction**, the lead toward a (dis)proof.

---

## 6. Infrastructure

- **`erdos` CLI** (`~/git/erdos-banger`): `sync website <id>` (statements → `problems_enriched.yaml`; direct
  web fetch is 403‑blocked), `lean check/formalize/import/prove`, `loop` (LLM↔kernel), `core/formal_conjectures`
  (DeepMind upstream Lean statements). The Mathlib‑backed Erdos project lives in `formal/lean/`.
- **Linear** (orthonoetic *Solve Erdos Problems*, team Math): backlog **MATH‑1…MATH‑24** filed via the raw
  GraphQL API (`issueCreate`, idempotent), one issue per target with statement + angle + lane.
- **Subagent‑driven workflow:** brainstorm → spec → plan → per‑task implementer + reviewer → whole‑branch
  review → finish; background agents for long/independent tracks (the MATH‑1 Mathlib proof; the issue filing),
  each verified firsthand before "done".
