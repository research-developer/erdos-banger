# Crossref (Vendor Notes)

Crossref provides DOI metadata via a public REST API. `erdos-banger` uses it to enrich references when a DOI is known.

## API Surface Used

- Base URL: `https://api.crossref.org`
- Work by DOI: `GET /works/<doi>`

Docs: https://www.crossref.org/documentation/retrieve-metadata/rest-api/

## Polite Requests (Contact + User-Agent)

Crossref requests that clients identify themselves and include a contact email, typically via:
- `mailto=<you@example.com>` query parameter (polite pool)
- A descriptive `User-Agent` header including project name/version + contact URL/email

Keep behavior conservative:
- retry transient failures with backoff
- avoid tight loops / bursts
- cache responses where appropriate (don’t refetch unchanged metadata)

## Testing Guidance

- Prefer unit tests with stored JSON fixtures for parsing.
- For HTTP behavior, mock at the `requests.get()` boundary (don’t mock parsing).
