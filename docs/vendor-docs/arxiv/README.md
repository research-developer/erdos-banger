# arXiv (Vendor Notes)

`erdos-banger` uses arXiv for:
1) **metadata** (title/authors/abstract) via the export API (Atom XML)
2) **fulltext extraction** via the e-print tarball endpoint (for TeX sources)

## API Surface Used

### Metadata (export API)

- Endpoint: `GET https://export.arxiv.org/api/query`
- Query param: `id_list=<arxiv_id_without_version>`

Docs: https://info.arxiv.org/help/api/user-manual.html

### Source tarball (e-print)

- Endpoint: `GET https://arxiv.org/e-print/<arxiv_id_without_version>`
- Returns: a tarball (often `.tar.gz`) containing source files

## Rate Limits / Terms of Use

arXiv explicitly requests:
- **no more than one request every 3 seconds**
- **no more than one connection at a time**

Docs: https://info.arxiv.org/help/api/tou.html

## Testing Guidance

- Keep deterministic fixtures:
  - Atom XML fixtures for metadata parsing.
  - Small synthetic tarballs for TeX extraction logic.
- Avoid live-network tests in CI. If needed, keep them behind `@pytest.mark.requires_network`.
