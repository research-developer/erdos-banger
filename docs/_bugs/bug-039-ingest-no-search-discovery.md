# BUG-039: Ingest Cannot Discover Papers - Only Fetches Pre-Defined References

**Date:** 2026-01-26
**Severity:** P1 (High - blocks research workflow)
**Status:** Open
**Component:** `erdos ingest`, `erdos refs`

## Summary

The `erdos ingest` command can only fetch papers that are already defined in the problem's reference list with valid identifiers (DOI, arXiv ID). It cannot:
1. Search for related papers by topic
2. Add papers discovered via Semantic Scholar, OpenAlex, or Exa
3. Manually add a specific arXiv paper to a problem

This fundamentally breaks the research workflow for problems with incomplete reference metadata.

## Reproduction

```bash
# Problem 848 has one reference with no metadata
$ uv run erdos refs problem 848
┏━━━━━━━┳━━━━━━━━━━┳━━━━━━┳━━━━━━━┓
┃ Key   ┃ Citation ┃ DOI  ┃ arXiv ┃
┡━━━━━━━╇━━━━━━━━━━╇━━━━━━╇━━━━━━━┩
│ Er92b │          │      │       │
└───────┴──────────┴──────┴───────┘

# Ingest finds nothing to fetch
$ uv run erdos ingest 848 --force
Ingesting references for Problem 848...
✓ Ingestion complete for Problem 848
  References processed: 1
  Entries written: 0
  Skipped: 1
```

## Root Cause

The ingest pipeline assumes rich reference metadata exists upstream. For Problem 848:
- The only reference `Er92b` has no DOI, arXiv ID, URL, or citation text
- No fallback mechanism to search for papers by problem topic
- No command to add papers manually

## Expected Behavior

Research workflow should support:
1. **Topic search**: `erdos ingest 848 --search "squarefree products"` to find related papers
2. **Manual add**: `erdos refs add 848 --arxiv 2511.16072` to add specific papers
3. **Discovery mode**: Use Exa/OpenAlex to find papers mentioning the problem

## Workaround

Currently none within the CLI. Must manually download and extract:

### For arXiv papers (PREFERRED - no PDF conversion needed):
```bash
# Download source tarball
curl -sL "https://arxiv.org/e-print/2511.16072" -o literature/cache/arxiv/2511.16072.tar.gz

# Extract LaTeX source
mkdir -p literature/cache/arxiv/extracted/2511.16072
tar -xzf literature/cache/arxiv/2511.16072.tar.gz -C literature/cache/arxiv/extracted/2511.16072

# Find and read .tex files directly
find literature/cache/arxiv/extracted/2511.16072 -name "*.tex"
```

### For non-arXiv papers (requires PDF conversion):
1. Search arXiv/Google Scholar for papers
2. Download PDFs manually to `literature/papers/0848/`
3. Convert with `uv run marker_single <file.pdf> --output_dir /tmp/output`
4. Update `literature/manifests/0848.yaml` by hand

**Note:** arXiv source is cleaner than PDF→marker conversion. See DEBT-112.

## Impact

- **Problem 848**: Known key papers (Sawhney, GPT-5 paper) cannot be ingested
- **Many problems**: Any problem with incomplete upstream references
- **Research velocity**: Manual paper discovery defeats CLI purpose

## Proposed Fix

1. Add `erdos refs add <problem_id> --arxiv <id>` command
2. Add `erdos ingest <problem_id> --search "<query>"` for topic-based discovery
3. Integrate Exa API for semantic paper search
4. Add `--discover` flag to auto-search based on problem statement keywords

## Related

- SYNTHESIS.md lists 5 key leads for Problem 848 that cannot be ingested:
  - arXiv:2511.16072 (GPT-5 paper)
  - arXiv:2507.01928 (related Problem 844)
  - Sawhney's standalone PDF
  - Montgomery-Vaughan 1973
  - Erdős Problems Forum thread
