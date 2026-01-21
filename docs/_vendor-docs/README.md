# Vendor Docs (Reference Notes)

This directory contains **reference notes** about third-party APIs, CLIs, and services that `erdos-banger` may integrate with.

Guidelines:

- **Do not commit secrets.** Keep API keys in local `.env` (gitignored).
- Prefer **links + summaries** over copying large vendor documentation verbatim.
- If a vendor provides an OpenAPI spec under a compatible license, store a **pinned copy** and record the source URL + retrieval date.

## Vendors

- `harmonic-aristotle/` — Harmonic Aristotle (Lean theorem proving service + `aristotlelib` / `aristotle` CLI)
