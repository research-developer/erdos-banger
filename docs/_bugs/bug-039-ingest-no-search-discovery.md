# BUG-039: Ingest Cannot Discover Papers - Only Fetches Pre-Defined References

**Date:** 2026-01-26
**Severity:** P2 (downgraded - core workflow fixed, discovery is feature work)
**Status:** Phase 1 Fixed (manual add works), Phases 2-3 are feature requests
**Component:** `erdos ingest`, `erdos refs`

## Summary

The `erdos ingest` command originally could only fetch papers already in the problem's reference list. This blocked the research workflow.

**Phase 1 (FIXED):** Manual add now works:
```bash
uv run erdos refs add 848 --arxiv 2511.16072  # ✅ WORKS
uv run erdos ingest 848 --force               # ✅ WORKS
```

**Phases 2-3 (NOT IMPLEMENTED - feature requests):**
1. ❌ Search for related papers by topic (`--search`)
2. ❌ Auto-discover papers via Exa/S2/zbMATH (`--discover`)

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

Manual add is now supported in the CLI. Workflow:

```bash
# 1) Add a discovered identifier to the local dataset
uv run erdos refs add 848 --arxiv 2511.16072

# 2) Ingest as usual (fetch metadata + download/extract)
uv run erdos ingest 848 --force
```

Discovery/search is still manual (Exa/S2/zbMATH), but you no longer need to hand-edit the dataset or manifest.

If you want to bypass the ingest pipeline entirely, you can still manually download and extract:

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

## Implementation Status

1. ✅ **DONE:** `erdos refs add <problem_id> --arxiv <id>` command (commit `f9b8441`)
2. ❌ **NOT STARTED:** `erdos ingest <problem_id> --search "<query>"` for topic-based discovery
3. ❌ **NOT STARTED:** Exa API integration for semantic paper search
4. ❌ **NOT STARTED:** `--discover` flag to auto-search based on problem statement keywords

See DEBT-110 for remaining feature work (Phases 2-3).

## Related

- SYNTHESIS.md lists 5 key leads for Problem 848 that cannot be ingested:
  - arXiv:2511.16072 (GPT-5 paper)
  - arXiv:2507.01928 (related Problem 844)
  - Sawhney's standalone PDF
  - Montgomery-Vaughan 1973
  - Erdős Problems Forum thread
