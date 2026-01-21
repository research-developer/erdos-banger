# OpenAlex (Vendor Notes)

OpenAlex is an open catalog of scholarly metadata. `erdos-banger` uses it as a **metadata enrichment** source (titles/authors/venue/abstract, plus citations/concepts).

## API Surface Used

- Base URL: `https://api.openalex.org`
- Work by DOI (preferred): `GET /works/https://doi.org/<doi>`
- Work search: `GET /works?search=<query>&per-page=<n>`
- Filtered works (citations/references): `GET /works?filter=<expr>&per-page=<n>`

Reference docs:
- Filters for works: https://docs.openalex.org/api-entities/works/filter-works
- Work object schema: https://docs.openalex.org/api-entities/works/work-object

## Polite Pool (`mailto`)

OpenAlex recommends including a `mailto` query parameter with a valid email for better service and clearer attribution:
- `GET /works?...&mailto=<you@example.com>`

Docs: https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication

## arXiv IDs in OpenAlex

OpenAlex does **not** expose an `ids.arxiv` field in the work `ids` object. Real payloads typically contain:
- `ids.openalex`
- `ids.doi`
- `ids.mag` (optional)
- `ids.pmid` / `ids.pmcid` (optional)

If an OpenAlex work is an arXiv e-print, the arXiv URL commonly appears in:
- `primary_location.landing_page_url` (e.g., `http://arxiv.org/abs/math/0404188`)

### Deterministic lookup for arXiv: DataCite DOI

arXiv assigns DataCite DOIs of the form `10.48550/arxiv.<arxiv_id>` (legacy IDs become `10.48550/arxiv.<archive>/<YYMMNNN>`). For example:
- `math/0404188` → `10.48550/arxiv.math/0404188`

This allows deterministic OpenAlex lookup via DOI endpoints without needing an `ids.arxiv` filter.

## Testing Guidance

- Keep “live API” tests under `@pytest.mark.requires_network` (never required for CI).
- Prefer deterministic unit tests for URL construction and payload mapping (use stored fixtures / minimal JSON snippets).
