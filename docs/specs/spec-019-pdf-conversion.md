# Spec 019: PDF Conversion

> Extends the ingest pipeline to convert PDF papers to searchable text, preserving mathematical notation.

**Status:** Blocked
**Target:** v2.0+
**Prerequisites (SSOT):**
- Ingest command: `docs/specs/spec-010-ingest-command.md`
- Search index: `docs/_archive/specs/spec-006-search-index.md`

**Blocker:** Docling (preferred library) pins `typer<0.20.0`, which conflicts with our `typer>=0.21.1` baseline. This spec is deferred until the dependency conflict is resolved.

---

## 0) Scope (v2.0+)

### In scope

1. **PDF to text conversion** with math preservation
2. **Docling integration** as optional dependency
3. **Fallback converters** for when Docling unavailable
4. **Math notation handling** (LaTeX, MathML, Unicode)
5. **Structured extraction** (sections, figures, tables)

### Out of scope

- OCR for scanned PDFs (require text-based PDFs)
- Image extraction and analysis
- Citation graph extraction
- Automatic reference resolution

### Why PDF Conversion Matters

While arXiv provides LaTeX source for most math papers, many older papers and non-arXiv publications are only available as PDFs. To index and search this content, we need reliable PDF-to-text conversion that preserves mathematical notation.

---

## 1) CLI Interface

### 1.1 `erdos ingest` (Extended)

When PDF conversion is available:

```text
erdos ingest PROBLEM_ID [OPTIONS]
```

**New Options**

- `--pdf`: Enable PDF conversion for non-arXiv references
- `--pdf-converter TEXT`: Converter to use (`docling`, `pymupdf`, `pdfplumber`)
- `--no-pdf`: Skip PDFs entirely (metadata only)

### 1.2 `erdos convert` (New Command)

Standalone PDF conversion for testing:

```text
erdos convert PDF_PATH [OPTIONS]
```

**Options**

- `--output, -o PATH`: Output file (default: stdout)
- `--format TEXT`: Output format (`markdown`, `text`, `json`)
- `--converter TEXT`: Converter to use

### Examples

```bash
# Ingest with PDF support
uv run erdos ingest 42 --pdf

# Convert a single PDF
uv run erdos convert paper.pdf --format markdown > paper.md

# Test converter
uv run erdos convert paper.pdf --converter docling
```

---

## 2) Converter Comparison

| Converter | License | Math Support | Quality | Speed |
|-----------|---------|--------------|---------|-------|
| **Docling** | MIT | Excellent (LaTeX) | High | Medium |
| PyMuPDF | AGPL | Poor | Medium | Fast |
| pdfplumber | MIT | Poor | Medium | Fast |
| pdf2image + Tesseract | Apache | None (OCR) | Low | Slow |

**Decision:** Docling is the preferred converter due to superior math handling. Others are fallbacks for edge cases.

---

## 3) Docling Integration

### Installation

```bash
pip install erdos-banger[pdf]
```

In `pyproject.toml`:

```toml
[project.optional-dependencies]
pdf = [
    "docling>=0.1.0",
]
```

**Note:** As of 2026-01, Docling requires `typer<0.20.0`. This spec is blocked until:
1. Docling updates to support `typer>=0.21.1`, OR
2. We find an alternative converter with equivalent math support

### Conversion Pipeline

```python
from docling.document_converter import DocumentConverter

def convert_pdf(pdf_path: Path) -> str:
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    return result.document.export_to_markdown()
```

### Math Preservation

Docling extracts math as:
- LaTeX: `$x^2 + y^2 = z^2$`
- Display math: `$$\sum_{i=1}^n i = \frac{n(n+1)}{2}$$`

These are preserved in markdown output and indexed for search.

---

## 4) Output Schema

### Markdown Output

```markdown
# Paper Title

**Authors:** Alice Smith, Bob Jones
**DOI:** 10.1234/example

## Abstract

This paper proves that $p(n) \sim \frac{1}{4n\sqrt{3}} e^{\pi\sqrt{2n/3}}$.

## 1. Introduction

The partition function $p(n)$ counts the number of ways...

## 2. Main Result

**Theorem 2.1.** For all $n \geq 1$,
$$p(n) = \frac{1}{\pi\sqrt{2}} \sum_{k=1}^{\infty} A_k(n) \sqrt{k} \frac{d}{dn}\left(\frac{\sinh(\frac{\pi}{k}\sqrt{\frac{2}{3}(n-\frac{1}{24})})}{\sqrt{n-\frac{1}{24}}}\right)$$
```

### JSON Output

```json
{
  "schema_version": 1,
  "source": "paper.pdf",
  "converter": "docling",
  "title": "Paper Title",
  "authors": ["Alice Smith", "Bob Jones"],
  "sections": [
    {
      "heading": "Abstract",
      "level": 1,
      "content": "This paper proves that...",
      "math_expressions": ["$p(n) \\sim ..."]
    }
  ],
  "math_blocks": [
    {"type": "inline", "latex": "p(n)", "location": {"page": 1, "line": 12}},
    {"type": "display", "latex": "\\sum_{i=1}^n ...", "location": {"page": 2, "line": 5}}
  ]
}
```

---

## 5) Fallback Strategy

When Docling is unavailable:

### Tier 1: arXiv Source (Preferred)

If paper is on arXiv, use LaTeX source instead of PDF.

### Tier 2: PyMuPDF (Fast, Low Quality)

```python
import fitz  # PyMuPDF

def convert_pymupdf(pdf_path: Path) -> str:
    doc = fitz.open(str(pdf_path))
    text = ""
    for page in doc:
        text += page.get_text()
    return text
```

**Limitation:** Math rendered as Unicode garbage or missing.

### Tier 3: Metadata Only

Store reference metadata without full text. Log warning.

---

## 6) Implementation

### 6.1 New Module: `src/erdos/core/pdf_converter.py`

Responsibilities:

1. Detect available converters
2. Convert PDF to markdown/text
3. Extract structured metadata
4. Handle math notation

### 6.2 Extend: `src/erdos/core/ingest.py`

Add PDF conversion step after download:

```python
if reference.has_pdf and pdf_conversion_enabled:
    text = pdf_converter.convert(pdf_path)
    create_extract(reference, text)
```

### 6.3 New Command: `src/erdos/commands/convert.py`

Standalone conversion command for testing and manual use.

---

## 7) Verification: This Spec is Testable

### Vertical Slice Test

```bash
# Install PDF support
pip install erdos-banger[pdf]

# Convert test PDF
uv run erdos convert tests/fixtures/sample_paper.pdf --format markdown

# Verify math is preserved
uv run erdos convert tests/fixtures/sample_paper.pdf | grep '\\sum'
```

### Unit Tests

- `tests/unit/test_pdf_converter.py`
  - Docling conversion produces markdown
  - Math expressions preserved
  - Fallback to PyMuPDF when Docling unavailable

### Integration Tests

- `tests/integration/test_pdf_ingest.py`
  - `erdos ingest` with `--pdf` converts PDFs
  - Extracted text appears in search index
  - Math notation searchable

### Acceptance Criteria

```bash
uv run ruff check .
uv run mypy src/
uv run pytest -m "not requires_lean and not requires_network"
```

---

## 8) Known Limitations

### Docling Dependency Conflict

As of 2026-01-18:
- erdos-banger requires `typer>=0.21.1`
- Docling requires `typer<0.20.0`

**Resolution paths:**
1. Wait for Docling to update Typer dependency
2. Fork Docling with updated dependency
3. Use alternative converter

### PDF Quality Variance

- Scanned PDFs: Not supported (no OCR)
- Complex layouts: May lose structure
- Embedded fonts: May cause Unicode issues

### Math Extraction Accuracy

- Simple inline math: ~95% accurate
- Complex display math: ~80% accurate
- Hand-drawn diagrams: Not extracted

---

## References

- Docling: `https://github.com/DS4SD/docling`
- PyMuPDF: `https://pymupdf.readthedocs.io/`
- Master vision PDF strategy: `docs/specs/master-qualifications.md` (Section 4)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-18 | Initial spec (blocked) |
