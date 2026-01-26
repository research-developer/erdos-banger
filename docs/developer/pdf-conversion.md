# PDF Conversion

The `erdos convert` command and `erdos ingest --pdf` optionally run PDF → text/markdown conversion to support downstream search and research workflows.

## Install

PDF conversion tooling is opt-in:

```bash
uv sync --extra pdf
```

## Usage

```bash
# Convert a PDF to text/markdown
uv run erdos convert path/to/paper.pdf

# Ingest and attempt PDF conversion for non-arXiv references
uv run erdos ingest 6 --pdf
```

## License Note

The `[pdf]` extra installs `marker-pdf`, which is GPL-licensed.

- Installing it locally is opt-in.
- Distributing builds that include GPL components may trigger GPL obligations.

If you cannot or do not want to use the `[pdf]` extra, run ingestion in metadata-only mode (`uv run erdos ingest --no-pdf`) or skip PDF handling entirely (`uv run erdos ingest --no-download` / `--no-network`).

