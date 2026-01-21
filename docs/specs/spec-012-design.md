# SPEC-012 Design Document: Loop Command Open Questions

> Resolves all open design decisions for `erdos loop` before implementation.

**Status:** Approved (SSOT for SPEC-012)
**Author:** Claude + Ray
**Created:** 2026-01-18
**Prerequisite for:** spec-012-loop-command.md

---

## Executive Summary

SPEC-012 (Loop Command) was identified as having "vaporware sections" — design decisions deferred to implementation time. This document resolves each decision from first principles, backed by industry research.

**Research Sources:**
- [Aider Edit Formats](https://aider.chat/docs/more/edit-formats.html) - 5+ years of LLM code editing research
- [Aider Unified Diffs](https://aider.chat/docs/unified-diffs.html) - GPT-4 "laziness" reduction
- [Code Surgery Blog](https://fabianhertwig.com/blog/coding-assistants-file-edits/) - Multi-tool comparison
- [Context Rot Research](https://research.trychroma.com/context-rot) - Token budget optimization
- [ICRH Paper](https://arxiv.org/html/2402.06627v3) - Reward hacking in feedback loops
- [Lean Copilot](https://github.com/lean-dojo/LeanCopilot) - Lean 4 + LLM integration patterns

---

## D1: Diff/Patch Output Format

### Question
How do we instruct the LLM to output changes that can be reliably applied?

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **A) Raw unified diff** | Standard format, tools exist | LLMs often produce incorrect line numbers and contexts |
| **B) Search/Replace blocks** | No line numbers; easy to validate against file content | Requires custom parser |
| **C) Whole-file replacement** | Simplest to implement | Expensive; loses context; can't review changes |
| **D) Structured JSON** | Explicit fields; easy validation | Verbose; models may hallucinate field values |

### Decision: **B) Search/Replace Blocks**

**Rationale:**
1. Avoids brittle line-number/patch context errors common in unified diffs.
2. Easy to validate safely: the SEARCH block must match existing file content.
3. Matches a widely used “search/replace block” edit format (see Aider docs).
4. Model-agnostic: works with Claude/GPT/Gemini/local models and wrapper scripts.

### Specification

```text
<<<<<<< SEARCH
[exact content to find, including whitespace]
=======
[replacement content]
>>>>>>> REPLACE
```

**Validation rules:**
1. SEARCH block must exist in the target file (exact match after normalization rules below)
2. SEARCH block must be unique (reject if multiple matches)
3. REPLACE block must be valid Lean 4 syntax (basic bracket/paren balance)
4. Only one SEARCH/REPLACE pair per response (atomic edits)

**Fallback chain:**
1. Exact match
2. Newline-normalized match (`\r\n` → `\n`)
3. Trailing-whitespace-normalized match (strip only trailing whitespace per line)
4. Reject with clear error message (no fuzzy matching in v1.2; safety > convenience)

---

## D2: Token Budget for Prompt Context

### Question
How much context do we include in the LLM prompt?

### Research Findings

From [Context Rot Research](https://research.trychroma.com/context-rot):
- Models do not use long context uniformly; reliability drops as input length grows.
- Keep prompts small and focused for stability and cost control.

### Decision: **Byte-Based Budget with Hard Caps**

This project does **not** add a tokenizer dependency just to count tokens. Enforcement is by UTF-8 byte size (deterministic), with rough token guidance in comments.

| Component | Max Bytes | Priority |
|-----------|------------|----------|
| System prompt | fixed | Required |
| Current Lean file | 16,384 | Required |
| Lean errors | 4,096 | Required |
| Problem statement | 2,048 | Required |
| Retrieved context (RAG) | 8,192 | Optional |
| **Total hard cap** | **32,768** | - |

**Rationale:**
1. Lean files are typically small (< 500 lines)
2. 32 KiB of prompt text is conservative across common model families and avoids “context rot” failure modes.
3. If the Lean file exceeds the cap, use **error-adjacent windowing**: include lines `error_line ± 50`
4. RAG context is optional — loop can work without it in v1.2

### Specification

```python
MAX_FILE_BYTES = 16_384
MAX_ERROR_BYTES = 4_096
MAX_PROBLEM_BYTES = 2_048
MAX_RAG_BYTES = 8_192
MAX_PROMPT_BYTES = 32_768

def budget_context(*, lean_file: str, errors_text: str, problem_text: str, rag_text: str) -> dict[str, str]:
    """Return truncated context strings that fit within the byte budget."""
    # Priority: lean_file > errors > problem > rag
```

---

## D3: Sorry Spam Prevention (Reward Hacking Mitigation)

### Question
How do we prevent the loop from "solving" problems by adding `sorry` placeholders?

### Research Findings

From [ICRH Paper](https://arxiv.org/html/2402.06627v3):
- Scaling model size **worsens** reward hacking
- Prompt specification is **insufficient** to prevent exploitation
- Need **composite reward functions** with explicit penalties
- Detect by simulating multiple feedback cycles

### Decision: **Composite Verification with Sorry Delta Tracking**

**Success is NOT just "compiles without errors."**

Success requires ALL of:
1. Lean compilation succeeds (exit 0)
2. Final file contains **zero** `sorry` keywords
3. Final file contains **zero** `admit` keywords
4. File size did not shrink by > 20% (prevents deletion attacks)

**Guardrail (default):**
- Reject any patch that increases `admit`.
- Reject any patch that increases `sorry` unless `--allow-sorry-increase > 0` is explicitly provided.

### Specification

```python
@dataclass
class LoopVerification:
    compiles: bool
    sorry_count_before: int
    sorry_count_after: int
    admit_count_before: int
    admit_count_after: int
    file_size_before: int
    file_size_after: int

    @property
    def sorry_delta(self) -> int:
        return self.sorry_count_after - self.sorry_count_before

    @property
    def admit_delta(self) -> int:
        return self.admit_count_after - self.admit_count_before

    @property
    def is_success(self) -> bool:
        return (
            self.compiles
            and self.sorry_count_after == 0
            and self.admit_count_after == 0
            and self.file_size_after >= self.file_size_before * 0.8
        )

    @property
    def is_progress(self) -> bool:
        """True if we made forward progress (even if not complete)."""
        return self.compiles and self.sorry_delta < 0
```

**Exit conditions:**
- `SUCCESS`: `is_success`
- `PROGRESS`: `is_progress` (continue loop)
- `STALLED`: No progress for 3 consecutive iterations
- `MAX_ITERATIONS`: Hard limit reached
- `REGRESSION`: file shrank (abort immediately)

---

## D4: Hard Limits (Concrete Values)

### Question
What are the actual numeric limits?

### Decision

| Limit | Value | Rationale |
|-------|-------|-----------|
| `max_iterations` | 10 | Default; user can override with `--max-iter` |
| `max_patch_lines` | 50 | Enforces atomic edits; larger = harder review + higher risk |
| `max_patch_bytes` | 8,192 | Hard cap on patch size (safety) |
| `max_file_bytes_prompt` | 16,384 bytes | Lean file cap in prompt |
| `max_prompt_bytes` | 32,768 bytes | Total prompt cap |
| `stall_threshold` | 3 | Consecutive no-progress iterations before abort |
| `lean_timeout_seconds` | 120 | Default; user can override with `--timeout` |
| `min_file_size_ratio` | 0.8 | Abort if file shrinks by > 20% |
| `allow_sorry_increase` | 0 | Default safety; must be explicitly enabled |

### Specification

```python
# src/erdos/core/loop_config.py

@dataclass(frozen=True)
class LoopConfig:
    max_iterations: int = 10
    max_patch_lines: int = 50
    max_patch_bytes: int = 8192
    max_file_bytes_prompt: int = 16384
    max_prompt_bytes: int = 32768
    stall_threshold: int = 3
    lean_timeout_seconds: int = 120
    min_file_size_ratio: float = 0.8
    allow_sorry_increase: int = 0
    rag_limit: int = 5

    @classmethod
    def from_cli(cls, **overrides) -> "LoopConfig":
        """Create config from CLI options, with validation."""
        return cls(**{k: v for k, v in overrides.items() if v is not None})
```

---

## D5: Prompt Template (SSOT)

### Question
What exact prompt do we send to the LLM?

### Decision: **Deterministic Template with Explicit Constraints**

The prompt must be **deterministic** (same inputs → same prompt) for:
1. Regression testing
2. Debugging failed iterations
3. Prompt tuning experiments

### Specification

```text
You are assisting with formalizing an Erdős problem in Lean 4.

## Current State

File: {file_path}
```lean
{file_content}
```

## Compilation Result

{compilation_status}

{error_section_if_errors}

## Problem Context

- ID: {problem_id}
- Title: {title}
- Statement: {statement}

{rag_section_if_available}

## Your Task

Fix the Lean file so it compiles without errors.

## Constraints (CRITICAL)

1. Output ONLY a single SEARCH/REPLACE block
2. Do NOT add `sorry` or `admit` — these are placeholders, not proofs
3. Do NOT delete theorems or lemmas — fix them
4. Keep changes minimal and focused on the reported error

## Output Format

<<<<<<< SEARCH
[exact lines to find]
=======
[replacement lines]
>>>>>>> REPLACE

If no fix is possible, respond with exactly: NO_FIX_POSSIBLE
```

**RAG section template (only included if retrieval returns chunks):**

```text
## Retrieved Context (cite as [n])

[1] ({chunk.source_type}) {chunk.chunk_id}
{chunk.text}

[2] ...
```

**Error section template (only included if errors exist):**

```text
## Errors

{error_count} error(s) found:

{for each error}
### Error {n} at line {line}
```
{error_message}
```
{/for}
```

---

## D6: Patch Validation Logic

### Question
How do we validate LLM output before applying?

### Decision: **Strict Validation Pipeline**

```python
def validate_patch(response: str, target_file: Path, config: LoopConfig) -> PatchResult:
    """
    Validate LLM response and return applicable patch or rejection reason.

    Returns:
        PatchResult with either:
        - success=True, search_text, replace_text
        - success=False, rejection_reason
    """

    # 1. Check for explicit "no fix" response
    if response.strip() == "NO_FIX_POSSIBLE":
        return PatchResult.no_fix()

    # 2. Parse SEARCH/REPLACE block
    match = SEARCH_REPLACE_PATTERN.search(response)
    if not match:
        return PatchResult.reject("No valid SEARCH/REPLACE block found")

    search_text = match.group("search")
    replace_text = match.group("replace")

    # 3. Size validation
    if len(replace_text.encode()) > config.max_patch_bytes:
        return PatchResult.reject(f"Patch exceeds {config.max_patch_bytes} bytes")

    if replace_text.count("\n") > config.max_patch_lines:
        return PatchResult.reject(f"Patch exceeds {config.max_patch_lines} lines")

    # 4. Path validation (security)
    if not target_file.resolve().is_relative_to(FORMAL_LEAN_DIR):
        return PatchResult.reject("Target file outside formal/lean/Erdos/")

    # 5. Find match in target file
    file_content = target_file.read_text()
    match_result = find_match(search_text, file_content)

    if not match_result.found:
        return PatchResult.reject(f"SEARCH block not found: {match_result.reason}")

    if match_result.ambiguous:
        return PatchResult.reject("SEARCH block matches multiple locations")

    # 6. Check for placeholder injection (sorry/admit)
    search_sorries = count_keyword(search_text, "sorry")
    replace_sorries = count_keyword(replace_text, "sorry")
    search_admits = count_keyword(search_text, "admit")
    replace_admits = count_keyword(replace_text, "admit")

    if replace_admits > search_admits:
        return PatchResult.reject("Patch adds admit — rejected")

    if (replace_sorries - search_sorries) > config.allow_sorry_increase:
        return PatchResult.reject(
            "Patch adds sorry — rejected (use --allow-sorry-increase to override)"
        )

    # 7. Syntax sanity check (bracket balance)
    if not is_bracket_balanced(replace_text):
        return PatchResult.reject("Replacement has unbalanced brackets")

    return PatchResult.ok(
        search_text=search_text,
        replace_text=replace_text,
        match_location=match_result.location,
    )
```

**Regex for parsing:**

```python
SEARCH_REPLACE_PATTERN = re.compile(
    r"<<<<<<< SEARCH\n(?P<search>.*?)\n=======\n(?P<replace>.*?)\n>>>>>>> REPLACE",
    re.DOTALL
)
```

---

## D7: Matching Strategy

### Question
How do we handle minor LLM drift in the SEARCH block?

### Decision: **Strict Matching Only (v1.2)**

Fuzzy matching is intentionally deferred. For a tool that edits files on disk, “sometimes apply the wrong patch” is worse than “reject and ask again.”

```python
def find_match(search_text: str, file_content: str) -> MatchResult:
    """
    Find search_text in file_content with fallback strategies.
    """
    # Pass 1: Exact match
    if search_text in file_content:
        locations = find_all_occurrences(search_text, file_content)
        if len(locations) == 1:
            return MatchResult.exact(locations[0])
        return MatchResult.ambiguous(len(locations))

    # Pass 2: Newline-normalized match (\r\n -> \n)
    normalized_search = search_text.replace("\r\n", "\n")
    normalized_file = file_content.replace("\r\n", "\n")
    if normalized_search in normalized_file:
        return MatchResult.newline_normalized()

    return MatchResult.not_found()
```

---

## D8: User Confirmation UX

### Question
How do we present patches for user approval?

### Decision: **Colored Diff Preview with Clear Actions**

```text
╭─────────────────────────────────────────────────────────────╮
│ Proposed Change (iteration 3/10)                            │
├─────────────────────────────────────────────────────────────┤
│ File: formal/lean/Erdos/Problem006.lean                     │
│ Lines: 42-47                                                │
├─────────────────────────────────────────────────────────────┤
│ - theorem prime_sum : ∀ n, ∃ p q, Prime p ∧ Prime q ∧ ...  │
│ + theorem prime_sum : ∀ n > 2, ∃ p q, Prime p ∧ Prime q... │
│ -   sorry                                                   │
│ + by                                                        │
│ +   intro n hn                                              │
│ +   exact goldbach_weak n hn                                │
╰─────────────────────────────────────────────────────────────╯

Apply this change? [y]es / [n]o / [s]kip iteration / [q]uit loop
```

**Modes:**
- Interactive (default): Prompt for each change
- `--yes`: Auto-apply without prompting
- `--no-apply`: Show proposed changes but never write

---

## Implementation Checklist

Before implementing SPEC-012, verify:

- [ ] All D1-D8 decisions are approved by senior review
- [ ] `src/erdos/core/loop_config.py` created with `LoopConfig`
- [ ] `src/erdos/core/patch_validator.py` created with validation pipeline
- [ ] `src/erdos/core/loop_verifier.py` created with sorry tracking
- [ ] Prompt template stored in `src/erdos/templates/loop_prompt.j2`
- [ ] Unit tests for patch validation (100% coverage on rejection cases)
- [ ] Integration test with mock LLM returning valid/invalid patches

---

## Resolved Open Questions (Senior Review Decisions)

1. **Structured JSON tool output (D1 Alternative):** No for v1.2. The loop accepts only the SEARCH/REPLACE block format (or `NO_FIX_POSSIBLE`). Tool-use capable models must be wrapped externally to emit this format.

2. **Temporary `sorry` increases (D3 Edge Case):** Yes, but explicit and bounded. Add `--allow-sorry-increase INT` (default `0`). In `--yes` mode, any value >0 must be provided explicitly. `admit` is never allowed to increase.

3. **Patch size hard limit (D4 Tuning):** Default `max_patch_lines=50` (was 100). This forces atomic edits and reduces the blast radius of a bad patch.

4. **RAG integration after ingest (D5):** Inline (no separate design doc). If the SQLite index contains reference chunks, include up to `rag_limit` chunks (default 5) as a `## Retrieved Context` section in the prompt. If index has no reference content, omit the section entirely.

5. **CI `--json` output (D8):** Emit a single final `CLIOutput` JSON on stdout. `data` must include an `iterations` list with per-iteration summaries (iteration number, whether a patch was applied, Lean check summary, and sorry/admit counts) plus a `run_log_path` pointing to a `.jsonl` file containing full prompts/patches for debugging. No progress text on stdout.

---

## References

- [Aider Edit Formats](https://aider.chat/docs/more/edit-formats.html)
- [Aider Unified Diffs](https://aider.chat/docs/unified-diffs.html)
- [Code Surgery: How AI Assistants Make Precise Edits](https://fabianhertwig.com/blog/coding-assistants-file-edits/)
- [Context Rot: How Increasing Input Tokens Impacts LLM Performance](https://research.trychroma.com/context-rot)
- [Feedback Loops Drive In-Context Reward Hacking](https://arxiv.org/html/2402.06627v3)
- [Lean Copilot](https://github.com/lean-dojo/LeanCopilot)
- [DeepSeek-Prover-V2](https://www.infoq.com/news/2025/05/deepseek-prover-v2-formal-proof/)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-18 | Initial draft with D1-D8 decisions |
