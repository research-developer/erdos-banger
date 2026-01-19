# Spec 019: PDF Conversion

> Extends the ingest pipeline to convert PDF papers to searchable text, preserving mathematical notation.

**Status:** Ready (v2.0+)
**Target:** v2.0+
**Prerequisites (SSOT):**
- Ingest command: `docs/specs/spec-010-ingest-command.md`
- Search index: `docs/_archive/specs/spec-006-search-index.md`

**License Decision (2026-01-19):** GPL accepted for optional `[pdf]` extra.
- Marker selected as primary PDF converter
- Rationale: GPL is acceptable only as an opt-in extra; distributing builds that include it must comply with GPL obligations (core remains permissive)
- See `docs/specs/master-vision.md` Section 7 "Licensing Summary" for policy

---

## 0) Scope (v2.0+)

### In scope

1. **PDF to text conversion** with math preservation
2. **Converter integration** as optional dependency
3. **Fallback converters** for when primary unavailable
4. **Math notation handling** (LaTeX, MathML, Unicode)
5. **LLM-enhanced extraction** (optional, for highest accuracy)

### Out of scope

- OCR for scanned PDFs (require text-based PDFs)
- Image extraction and analysis
- Citation graph extraction
- Automatic reference resolution
- High-fidelity table/figure extraction

### Why PDF Conversion Matters

While arXiv provides LaTeX source for most math papers, many older papers and non-arXiv publications are only available as PDFs. To index and search this content, we need reliable PDF-to-text conversion that preserves mathematical notation.

---

## 1) Converter Comparison (Updated 2026-01)

| Converter | License | Math Quality | Speed | LLM Mode | Status |
|-----------|---------|--------------|-------|----------|--------|
| **Marker** | GPL | Excellent | 11.3s | ✅ Yes | Primary `[pdf]` extra (opt-in GPL) |
| **Docling** | MIT | Excellent | Medium | ✅ Yes | Typer version conflict |
| **PyMuPDF4LLM** | AGPL | Great | 0.14s | ❌ No | License prohibited |
| **pdfplumber** | MIT | Poor | Fast | ❌ No | Fallback only |

### License Policy (SSOT)

From `docs/specs/master-vision.md`: No GPL/AGPL components in core dependencies.

**Decision (2026-01-19):** GPL is acceptable for optional extras. Marker is the default converter for the `[pdf]` extra.

**Alternatives (if you cannot/will not use GPL):**
1. **Wait for Docling** - MIT license, typer fix expected
2. **Use pdfplumber** - MIT but poor math quality (fallback only)

---

## 2) Marker Integration (Primary)

[Marker](https://github.com/datalab-to/marker) is the highest quality option for math PDF conversion.

### Installation

```bash
uv sync --extra pdf
```

In `pyproject.toml`:

```toml
[project.optional-dependencies]
pdf = [
    "marker-pdf>=1.0.0",
]
```

**License note:** Marker code is GPL. Model weights use AI Pubs Open Rail-M (free for research, personal use, startups <$2M revenue).

### Environment Variables

```bash
# .env file - Marker LLM configuration

# Option 1: Google Gemini (default for --use_llm)
GOOGLE_API_KEY=your-gemini-key

# Option 2: Claude (preferred for erdos-banger users)
# Use via: --llm_service marker.services.claude.ClaudeService
# (Uses existing ANTHROPIC_API_KEY)

# Option 3: OpenAI
# Use via: --llm_service marker.services.openai.OpenAIService
# (Uses existing OPENAI_API_KEY)

# Option 4: Ollama (local, no API key needed)
# Use via: --llm_service marker.services.ollama.OllamaService
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Torch device (auto-detected, but can override)
# TORCH_DEVICE=cuda
# TORCH_DEVICE=mps  # Apple Silicon
```

### LLM Service Options

Marker supports multiple LLM backends for enhanced accuracy:

| Service | Config Flag | API Key Env Var |
|---------|-------------|-----------------|
| **Gemini** (default) | `--llm_service marker.services.gemini.GoogleGeminiService` | `GOOGLE_API_KEY` |
| **Claude** | `--llm_service marker.services.claude.ClaudeService` | `ANTHROPIC_API_KEY` |
| **OpenAI** | `--llm_service marker.services.openai.OpenAIService` | `OPENAI_API_KEY` |
| **Ollama** | `--llm_service marker.services.ollama.OllamaService` | None (local) |
| **Vertex AI** | `--llm_service marker.services.vertex.GoogleVertexService` | `GOOGLE_APPLICATION_CREDENTIALS` |

### CLI Usage

```bash
# Basic conversion
marker_single input.pdf output.md

# With LLM enhancement (highest quality for math)
marker_single input.pdf output.md --use_llm

# With Claude as LLM backend
marker_single input.pdf output.md --use_llm \
  --llm_service marker.services.claude.ClaudeService

# Force OCR (for bad text extraction)
marker_single input.pdf output.md --force_ocr

# Maximum quality (LLM + inline math redo)
marker_single input.pdf output.md --use_llm --redo_inline_math
```

### Python API

```python
from pathlib import Path
from marker.converters.pdf import PdfConverter
from marker.config.parser import ConfigParser

def convert_pdf_with_marker(
    pdf_path: Path,
    use_llm: bool = False,
    llm_service: str | None = None,
) -> str:
    """Convert PDF to markdown using Marker.

    Args:
        pdf_path: Path to input PDF
        use_llm: Enable LLM-enhanced extraction
        llm_service: LLM service class path (e.g., 'marker.services.claude.ClaudeService')

    Returns:
        Markdown text with preserved math notation
    """
    config = ConfigParser()

    if use_llm:
        config.use_llm = True
        if llm_service:
            config.llm_service = llm_service

    converter = PdfConverter(config=config)
    result = converter(str(pdf_path))

    return result.markdown
```

---

## 3) CLI Interface

### 3.1 `erdos ingest` (Extended)

When PDF conversion is available:

```text
erdos ingest PROBLEM_ID [OPTIONS]
```

**New Options**

- `--pdf`: Enable PDF conversion for non-arXiv references
- `--pdf-converter TEXT`: Converter to use (`marker`, `pdfplumber`)
- `--use-llm`: Enable LLM-enhanced PDF extraction
- `--no-pdf`: Skip PDFs entirely (metadata only)

### 3.2 `erdos convert` (New Command)

Standalone PDF conversion for testing:

```text
erdos convert PDF_PATH [OPTIONS]
```

**Options**

- `--output, -o PATH`: Output file (default: stdout)
- `--format TEXT`: Output format (`markdown`, `text`, `json`)
- `--converter TEXT`: Converter to use
- `--use-llm`: Enable LLM enhancement
- `--llm-service TEXT`: LLM backend (gemini, claude, openai, ollama)

### Examples

```bash
# Ingest with PDF support
uv run erdos ingest 42 --pdf

# Convert with LLM enhancement
uv run erdos convert paper.pdf --use-llm --llm-service claude

# Maximum quality conversion
uv run erdos convert paper.pdf --use-llm --format markdown > paper.md

# Verify math is preserved
uv run erdos convert paper.pdf | grep '\\sum'
```

---

## 4) Fallback Strategy

When primary converter unavailable:

### Tier 1: arXiv Source (Preferred)

If paper is on arXiv, use LaTeX source instead of PDF. This is always higher quality.

### Tier 2: Primary Converter (Marker or Docling)

Use configured converter with optional LLM enhancement.

### Tier 3: pdfplumber (Fast, Low Quality)

```python
from pathlib import Path
import pdfplumber

def convert_pdfplumber(pdf_path: Path) -> str:
    with pdfplumber.open(str(pdf_path)) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)
```

**Limitation:** Math rendered as Unicode garbage or missing.

### Tier 4: Metadata Only

Store reference metadata without full text. Log warning.

---

## 5) Implementation

### 5.1 New Module: `src/erdos/core/pdf_converter.py`

Responsibilities:

1. Detect available converters
2. Convert PDF to markdown/text
3. Support LLM enhancement
4. Handle math notation
5. Abstract over converter differences

### 5.2 Extend: `src/erdos/core/ingest.py`

Add PDF conversion step after download:

```python
if reference.has_pdf and pdf_conversion_enabled:
    text = pdf_converter.convert(pdf_path, use_llm=use_llm)
    create_extract(reference, text)
```

**Cache/extract layout (SSOT, v2.0):**
- Cached PDFs: `literature/cache/pdf/{reference_id}/paper.pdf`
- Extracted text: `literature/extracts/pdf/{reference_id}/fulltext.md`

### 5.3 New Command: `src/erdos/commands/convert.py`

Standalone conversion command for testing and manual use.

---

## 6) Verification

### Unit Tests

- `tests/unit/test_pdf_converter.py`
  - Converter detection works
  - LLM service selection works
  - Math expressions preserved (with fixture PDF)
  - Fallback to pdfplumber when primary unavailable

### Integration Tests

- `tests/integration/test_pdf_ingest.py`
  - `erdos ingest` with `--pdf` converts PDFs
  - Extracted text appears in correct location
  - `--use-llm` flag works with configured service

### Acceptance Criteria

```bash
uv run ruff check .
uv run mypy src/
uv run pytest -m "not requires_lean and not requires_network"
```

---

## 7) Known Limitations

### License Constraints

- **Marker**: GPL code; allowed only as opt-in `[pdf]` extra (not a core dependency)
- **PyMuPDF**: AGPL, prohibited by policy
- **Docling**: MIT but typer conflict (waiting on upstream fix)

### PDF Quality Variance

- Scanned PDFs: Not supported (no OCR in scope)
- Complex layouts: May lose structure
- Embedded fonts: May cause Unicode issues

### LLM Costs

Using `--use-llm` incurs API costs. For batch processing, consider Ollama (local, free).

---

## References

- Marker (repo): `https://github.com/datalab-to/marker`
- Marker (PyPI): `https://pypi.org/project/marker-pdf/`
- Docling (repo): `https://github.com/docling-project/docling`
- pdfplumber (PyPI): `https://pypi.org/project/pdfplumber/`
- Master vision license policy: `docs/specs/master-vision.md`

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-18 | Initial spec (blocked) |
| 0.2.0 | 2026-01-19 | Adopted Marker as primary `[pdf]` extra, added LLM integration details, documented GPL exception |
