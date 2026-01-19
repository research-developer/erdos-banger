# Bug 010: `erdos ingest --no-network` Returns Wrong Exit Code on First Run

**Priority:** P2 (Medium)
**Status:** Fixed
**Found:** 2026-01-19
**Fixed:** 2026-01-19
**Commit:** 49ba46f

## Description

When running `erdos ingest --no-network` with **no existing manifest**, the command must fail with:

- `ExitCode.NETWORK_ERROR` (4)
- a structured `CLIOutput.err(...)` (still printed to stdout in `--json` mode)

Instead, it returned:

- exit code `1` (`ExitCode.ERROR`)
- `error.type="IngestError"`

This broke the Spec 010 exit code contract for the `--no-network` flag.

## Steps to Reproduce

```bash
tmp=$(mktemp -d)
mkdir -p "$tmp/data"
cp tests/fixtures/sample_problems.yaml "$tmp/data/problems.yaml"

ERDOS_DATA_PATH="$tmp/data" ERDOS_REPO_ROOT="$tmp" \
  uv run erdos ingest 6 --no-network --json

rm -rf "$tmp"
```

## Root Cause

`src/erdos/core/ingest.py` classified *all* partial ingestion failures as `IngestError` with `ExitCode.ERROR` after a refactor intended to avoid mislabeling parse/tar errors as network errors. That inadvertently treated `--no-network` policy failures as non-network failures.

## Fix

- Track whether failures are network-related vs non-network-related.
- Return `NetworkError` + `ExitCode.NETWORK_ERROR` when failures are purely network/policy (`--no-network`) related.
- Keep `IngestError` + `ExitCode.ERROR` for non-network failures (parse/tar/extract issues).
- Add an integration test to lock the behavior.

## Related

- Spec 010: `docs/specs/spec-010-ingest-command.md`
- Exit codes: `src/erdos/core/exit_codes.py`
- Implementation: `src/erdos/core/ingest.py`
