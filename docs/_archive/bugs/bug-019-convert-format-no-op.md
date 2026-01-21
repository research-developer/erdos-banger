# BUG-019: `erdos convert --format` Is a No-op (text/json)

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-21
**Fixed:** 2026-01-21
**Commit:** b2dcdfe

---

## Description

`erdos convert` advertises `--format [markdown|text|json]`, but the implementation previously did not actually change the output for `text` or `json`. This was user-visible and violated the archived SPEC-019 CLI contract.

## Steps to Reproduce

```bash
uv run erdos convert some.pdf --format text
uv run erdos convert some.pdf --format json
```

## Expected Behavior

- `--format text` should emit plain text (no Markdown formatting), or at minimum document that it emits Markdown-as-text.
- `--format json` should emit a JSON document representing conversion output (text + metadata), suitable for piping.

## Actual Behavior

The command returned the same `output_text` regardless of `--format`.

## Root Cause

In `src/erdos/commands/convert.py`, the `OutputFormat.TEXT` and `OutputFormat.JSON` branches were effectively unimplemented, so no formatting/serialization occurred.

## Fix Implemented

- `--format text`: best-effort Markdown → plain text transformation (deterministic stripping for basic constructs).
- `--format json`: writes a plain JSON payload to stdout (distinct from the global `--json` CLIOutput envelope).

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

1. [x] `uv run erdos convert <pdf> --format text` produces text output meaningfully different from markdown.
2. [x] `uv run erdos convert <pdf> --format json` produces valid JSON on stdout (no extra progress text in stdout).
3. [x] Integration tests cover `--format text` and `--format json`.

## References

- SPEC-019 convert CLI options: `docs/_archive/specs/spec-019-pdf-conversion.md` (Section 3.2)
