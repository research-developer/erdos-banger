# Data Directory

This repo supports two related datasets:

## 1) Local enriched dataset (v1 contract)

- Path: `data/problems_enriched.yaml` (gitignored)
- Purpose: provides **title** + **statement** + optional references/notes alongside metadata.
- Used by: `erdos list`, `erdos show`, `erdos search --build-index`, and `erdos lean formalize`.

Quick local setup (sample data):
```bash
cp tests/fixtures/sample_problems.yaml data/problems_enriched.yaml
```

## 2) Upstream metadata-only dataset (submodule)

- Path: `data/erdosproblems/` (git submodule)
- Source: https://github.com/teorth/erdosproblems
- Upstream file: `data/erdosproblems/data/problems.yaml`
- Purpose: canonical **metadata** (status, prize, tags, OEIS IDs, formalization status).

To fetch the submodule after cloning:
```bash
git submodule update --init --recursive
```

Note: the upstream YAML is **metadata-only** and is not directly compatible with the enriched v1 loader contract.
