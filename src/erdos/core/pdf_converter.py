"""Backward-compatible shim for pdf_converter.

This module has been moved to erdos.core.pdf.converter.
This shim exists for backward compatibility and will be removed in a future version.
"""

from erdos.core.pdf.converter import (
    LLMService,
    PDFConversionConfig,
    PDFConversionResult,
    PDFConverter,
    convert_pdf,
    convert_with_marker,
    convert_with_pdfplumber,
    get_available_converters,
    is_marker_available,
    is_pdfplumber_available,
    select_converter,
)


__all__ = [
    "LLMService",
    "PDFConversionConfig",
    "PDFConversionResult",
    "PDFConverter",
    "convert_pdf",
    "convert_with_marker",
    "convert_with_pdfplumber",
    "get_available_converters",
    "is_marker_available",
    "is_pdfplumber_available",
    "select_converter",
]
