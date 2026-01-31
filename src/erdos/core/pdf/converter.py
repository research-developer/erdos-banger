"""PDF conversion module (SPEC-019).

Provides abstraction over PDF-to-text converters with math preservation.

Primary converter: Marker (GPL, optional `[pdf]` extra)
Fallback converter: pdfplumber (MIT, low quality for math)
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, cast


# Module-level lock to protect TORCH_DEVICE environment variable mutations (BUG-047)
_torch_device_lock = threading.Lock()


logger = logging.getLogger(__name__)


class PDFConverter(str, Enum):
    """Available PDF converter backends."""

    MARKER = "marker"
    PDFPLUMBER = "pdfplumber"


class LLMService(str, Enum):
    """LLM services for Marker enhancement."""

    GEMINI = "gemini"
    CLAUDE = "claude"
    OPENAI = "openai"
    OLLAMA = "ollama"

    def get_marker_class(self) -> str:
        """Get the Marker service class path for this LLM."""
        service_map = {
            LLMService.GEMINI: "marker.services.gemini.GoogleGeminiService",
            LLMService.CLAUDE: "marker.services.claude.ClaudeService",
            LLMService.OPENAI: "marker.services.openai.OpenAIService",
            LLMService.OLLAMA: "marker.services.ollama.OllamaService",
        }
        return service_map[self]


@dataclass(frozen=True)
class PDFConversionConfig:
    """Configuration for PDF conversion."""

    converter: str = "marker"
    use_llm: bool = False
    llm_service: LLMService | None = None
    force_ocr: bool = False
    torch_device: str | None = None  # cpu, cuda, mps - sets TORCH_DEVICE env var


@dataclass
class PDFConversionResult:
    """Result of a PDF conversion operation."""

    success: bool
    text: str | None
    converter: str
    error: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


def _marker_cli_options(
    *,
    use_llm: bool,
    llm_service: LLMService | None,
    force_ocr: bool,
) -> dict[str, object]:
    cli_options: dict[str, object] = {"output_format": "markdown"}
    if use_llm:
        cli_options["use_llm"] = True
        if llm_service is not None:
            cli_options["llm_service"] = llm_service.get_marker_class()
    if force_ocr:
        cli_options["force_ocr"] = True
    return cli_options


def _marker_get_converter_cls(config_parser: Any) -> type[Any]:
    if hasattr(config_parser, "get_converter_cls"):
        return cast("type[Any]", config_parser.get_converter_cls())

    # marker-pdf 1.0.x did not expose get_converter_cls() yet.
    from marker.converters.pdf import PdfConverter  # noqa: PLC0415

    return cast("type[Any]", PdfConverter)


def _marker_get_llm_service(config_parser: Any) -> Any | None:
    if hasattr(config_parser, "get_llm_service"):
        return config_parser.get_llm_service()
    return None


def _marker_create_converter(converter_cls: type[Any], kwargs: dict[str, Any]) -> Any:
    try:
        return converter_cls(**kwargs)
    except TypeError as exc:
        # marker-pdf 1.0.x PdfConverter did not accept llm_service.
        if "llm_service" in kwargs and "llm_service" in str(exc):
            without_llm = dict(kwargs)
            without_llm.pop("llm_service", None)
            return converter_cls(**without_llm)
        raise


def _convert_with_marker_success(
    pdf_path: Path,
    *,
    use_llm: bool,
    llm_service: LLMService | None,
    force_ocr: bool,
) -> PDFConversionResult:
    # Import Marker components (optional GPL dependency)
    from marker.config.parser import ConfigParser  # noqa: PLC0415
    from marker.models import create_model_dict  # noqa: PLC0415

    config_parser = ConfigParser(
        cli_options=_marker_cli_options(
            use_llm=use_llm,
            llm_service=llm_service,
            force_ocr=force_ocr,
        )
    )
    converter_cls = _marker_get_converter_cls(config_parser)

    config_dict = config_parser.generate_config_dict()
    processors = config_parser.get_processors()
    renderer = config_parser.get_renderer()
    resolved_llm_service = _marker_get_llm_service(config_parser)

    converter_kwargs: dict[str, Any] = {
        "config": config_dict,
        "artifact_dict": create_model_dict(),
        "processor_list": processors,
        "renderer": renderer,
    }
    if resolved_llm_service is not None:
        converter_kwargs["llm_service"] = resolved_llm_service

    converter = _marker_create_converter(converter_cls, converter_kwargs)
    rendered = converter(str(pdf_path))

    markdown = getattr(rendered, "markdown", None)
    markdown_text = markdown if isinstance(markdown, str) else str(rendered)

    page_count = getattr(converter, "page_count", None)
    logger.debug("Marker extracted %d characters from %s", len(markdown_text), pdf_path)

    return PDFConversionResult(
        success=True,
        text=markdown_text,
        converter="marker",
        metadata={
            "use_llm": str(use_llm),
            "llm_service": str(resolved_llm_service) if resolved_llm_service else "",
            "force_ocr": str(force_ocr),
            "page_count": str(page_count) if page_count is not None else "",
        },
    )


def is_marker_available() -> bool:
    """Check if Marker PDF converter is available."""
    try:
        import marker.converters.pdf  # noqa: F401, PLC0415

        return True
    except Exception as e:  # optional dependency may fail to import for many reasons
        logger.debug("Marker unavailable: %s", e)
        return False


def is_pdfplumber_available() -> bool:
    """Check if pdfplumber is available."""
    try:
        import pdfplumber  # noqa: F401, PLC0415

        return True
    except Exception as e:  # optional dependency may fail to import for many reasons
        logger.debug("pdfplumber unavailable: %s", e)
        return False


def get_available_converters() -> list[str]:
    """Get list of available converter names."""
    converters = []
    if is_marker_available():
        converters.append("marker")
    if is_pdfplumber_available():
        converters.append("pdfplumber")
    return converters


def select_converter(preferred: PDFConverter | None = None) -> PDFConverter | None:
    """Select the best available converter.

    Args:
        preferred: Preferred converter to use if available.

    Returns:
        Selected converter or None if none available.
    """
    if preferred is not None:
        # Check if preferred converter is available
        if preferred == PDFConverter.MARKER and is_marker_available():
            return PDFConverter.MARKER
        if preferred == PDFConverter.PDFPLUMBER and is_pdfplumber_available():
            return PDFConverter.PDFPLUMBER
        return None

    # Auto-select: prefer Marker, fall back to pdfplumber
    if is_marker_available():
        return PDFConverter.MARKER
    if is_pdfplumber_available():
        return PDFConverter.PDFPLUMBER
    return None


def convert_with_pdfplumber(pdf_path: Path) -> PDFConversionResult:
    """Convert PDF using pdfplumber (low quality, fallback).

    Args:
        pdf_path: Path to PDF file.

    Returns:
        PDFConversionResult with extracted text.
    """
    try:
        import pdfplumber  # noqa: PLC0415
    except ImportError:
        return PDFConversionResult(
            success=False,
            text=None,
            converter="pdfplumber",
            error="pdfplumber is not installed",
        )

    if not pdf_path.exists():
        return PDFConversionResult(
            success=False,
            text=None,
            converter="pdfplumber",
            error=f"File not found: {pdf_path}",
        )

    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)

            full_text = "\n\n".join(pages)

            logger.debug(
                "pdfplumber extracted %d characters from %s", len(full_text), pdf_path
            )

            return PDFConversionResult(
                success=True,
                text=full_text,
                converter="pdfplumber",
                metadata={"pages": str(len(pdf.pages))},
            )
    except Exception as e:  # conversion backend may raise a variety of errors
        logger.warning("pdfplumber conversion failed for %s: %s", pdf_path, e)
        return PDFConversionResult(
            success=False,
            text=None,
            converter="pdfplumber",
            error=f"Conversion error: {e}",
        )


def convert_with_marker(
    pdf_path: Path,
    *,
    use_llm: bool = False,
    llm_service: LLMService | None = None,
    force_ocr: bool = False,
) -> PDFConversionResult:
    """Convert PDF using Marker (high quality, GPL).

    Args:
        pdf_path: Path to PDF file.
        use_llm: Enable LLM-enhanced extraction.
        llm_service: LLM service to use for enhancement.
        force_ocr: Force OCR even if text is extractable.

    Returns:
        PDFConversionResult with markdown text.
    """
    if not is_marker_available():
        return PDFConversionResult(
            success=False,
            text=None,
            converter="marker",
            error="Marker is not installed. Install with: uv sync --extra pdf",
        )

    if not pdf_path.exists():
        return PDFConversionResult(
            success=False,
            text=None,
            converter="marker",
            error=f"File not found: {pdf_path}",
        )

    try:
        logger.debug(
            "Converting %s with Marker (use_llm=%s, llm_service=%s, force_ocr=%s)",
            pdf_path,
            use_llm,
            llm_service,
            force_ocr,
        )
        return _convert_with_marker_success(
            pdf_path,
            use_llm=use_llm,
            llm_service=llm_service,
            force_ocr=force_ocr,
        )
    except Exception as e:  # conversion backend may raise a variety of errors
        logger.warning("Marker conversion failed for %s: %s", pdf_path, e)
        return PDFConversionResult(
            success=False,
            text=None,
            converter="marker",
            error=f"Conversion error: {e}",
        )


def convert_pdf(
    pdf_path: Path,
    config: PDFConversionConfig,
) -> PDFConversionResult:
    """Convert a PDF file to text using configured converter.

    Args:
        pdf_path: Path to PDF file.
        config: Conversion configuration.

    Returns:
        PDFConversionResult with extracted text.
    """
    # Validate file exists
    if not pdf_path.exists():
        return PDFConversionResult(
            success=False,
            text=None,
            converter=config.converter,
            error=f"File not found: {pdf_path}",
        )

    # Validate file extension
    if pdf_path.suffix.lower() != ".pdf":
        return PDFConversionResult(
            success=False,
            text=None,
            converter=config.converter,
            error=f"Not a PDF file: {pdf_path.suffix}",
        )

    # Select converter
    try:
        preferred = PDFConverter(config.converter) if config.converter else None
    except ValueError:
        return PDFConversionResult(
            success=False,
            text=None,
            converter=config.converter,
            error=f"Unknown converter: '{config.converter}'. Valid options: marker, pdfplumber",
        )
    converter = select_converter(preferred)

    if converter is None:
        return PDFConversionResult(
            success=False,
            text=None,
            converter=config.converter,
            error="No converter available. Install marker: uv sync --extra pdf",
        )

    # Set TORCH_DEVICE env var if specified (Marker uses this for device selection)
    # Use lock to protect env var mutations in concurrent scenarios (BUG-047)
    with _torch_device_lock:
        # Save original value to restore after conversion
        original_torch_device = os.environ.get("TORCH_DEVICE")
        try:
            if config.torch_device is not None:
                os.environ["TORCH_DEVICE"] = config.torch_device
                logger.debug(
                    "Set TORCH_DEVICE=%s for Marker conversion", config.torch_device
                )

            # Convert using selected converter
            if converter == PDFConverter.MARKER:
                return convert_with_marker(
                    pdf_path,
                    use_llm=config.use_llm,
                    llm_service=config.llm_service,
                    force_ocr=config.force_ocr,
                )
            # PDFConverter.PDFPLUMBER (or any future converter)
            return convert_with_pdfplumber(pdf_path)
        finally:
            # Restore original TORCH_DEVICE value
            if config.torch_device is not None:
                if original_torch_device is None:
                    os.environ.pop("TORCH_DEVICE", None)
                else:
                    os.environ["TORCH_DEVICE"] = original_torch_device
