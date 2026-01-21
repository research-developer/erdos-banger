# BUG-019: `erdos convert --format` Is a No-op (text/json)

**Priority:** P2
**Status:** Open
**Found:** 2026-01-21

---

## Description

`erdos convert` advertises `--format [markdown|text|json]`, but the implementation does not actually change the output for `text` or `json`. This is user-visible and violates the archived SPEC-019 CLI contract.

## Steps to Reproduce

```bash
uv run erdos convert some.pdf --format text
uv run erdos convert some.pdf --format json
```

## Expected Behavior

- `--format text` should emit plain text (no Markdown formatting), or at minimum document that it emits Markdown-as-text.
- `--format json` should emit a JSON document representing conversion output (text + metadata), suitable for piping.

## Actual Behavior

The command returns the same `output_text` regardless of `--format`.

## Root Cause

In `src/erdos/commands/convert.py`, the `OutputFormat.TEXT` and `OutputFormat.JSON` branches contain `pass`, so no formatting/serialization occurs:

```python
if output_format == OutputFormat.TEXT:
    pass
elif output_format == OutputFormat.JSON:
    pass
```

## Fix Options (3)

### Option A (Recommended): Implement `--format` semantics fully

- `markdown`: current behavior (emit markdown)
- `text`: strip Markdown constructs (minimal, deterministic stripping; document limitations)
- `json`: write a JSON object containing `{converter, text, metadata, char_count, ...}` to stdout (or to `--output` when specified)

### Option B: Remove `--format json` and rely on global `--json`

This reduces surface area, but breaks the documented `erdos convert --format json` interface in SPEC-019 and makes file output semantics less clear.

### Option C: Make `--format` only affect `--output` files

Always print human output to terminal, but if `--output` is provided, write the specified format to file. This is less surprising for CLI UX, but still needs clear documentation.

## Acceptance Criteria

1. [ ] `uv run erdos convert <pdf> --format text` produces text output meaningfully different from markdown (or explicitly documented behavior).
2. [ ] `uv run erdos convert <pdf> --format json` produces valid JSON on stdout (no extra progress text in stdout).
3. [ ] Add/adjust tests in `tests/integration/test_pdf_convert.py` to cover `--format text` and `--format json`.
4. [ ] Update any docs/spec references if semantics change.

## References

- SPEC-019 convert CLI options: `docs/_archive/specs/spec-019-pdf-conversion.md` (Section 3.2)
