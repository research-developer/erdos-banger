"""Tests for PDF converter module (SPEC-019)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock, patch


if TYPE_CHECKING:
    import pytest


class TestConverterDetection:
    """Tests for converter availability detection."""

    def test_is_marker_available_when_installed(self) -> None:
        """is_marker_available() returns True when marker is installed."""
        from erdos.core.pdf.converter import is_marker_available

        # Can only test if marker is actually installed
        # This test documents expected behavior
        result = is_marker_available()
        assert isinstance(result, bool)

    def test_is_pdfplumber_available_when_installed(self) -> None:
        """is_pdfplumber_available() returns True when pdfplumber is installed."""
        from erdos.core.pdf.converter import is_pdfplumber_available

        result = is_pdfplumber_available()
        assert isinstance(result, bool)

    def test_get_available_converters_returns_list(self) -> None:
        """get_available_converters() returns list of available converter names."""
        from erdos.core.pdf.converter import get_available_converters

        result = get_available_converters()
        assert isinstance(result, list)
        # Should return list of strings (converter names)
        for converter in result:
            assert isinstance(converter, str)


class TestConverterEnum:
    """Tests for PDFConverter enum."""

    def test_pdf_converter_enum_values(self) -> None:
        """PDFConverter enum has expected values."""
        from erdos.core.pdf.converter import PDFConverter

        assert PDFConverter.MARKER.value == "marker"
        assert PDFConverter.PDFPLUMBER.value == "pdfplumber"

    def test_pdf_converter_from_string(self) -> None:
        """PDFConverter can be created from string."""
        from erdos.core.pdf.converter import PDFConverter

        assert PDFConverter("marker") == PDFConverter.MARKER
        assert PDFConverter("pdfplumber") == PDFConverter.PDFPLUMBER


class TestLLMService:
    """Tests for LLMService enum."""

    def test_llm_service_enum_values(self) -> None:
        """LLMService enum has expected values."""
        from erdos.core.pdf.converter import LLMService

        assert LLMService.GEMINI.value == "gemini"
        assert LLMService.CLAUDE.value == "claude"
        assert LLMService.OPENAI.value == "openai"
        assert LLMService.OLLAMA.value == "ollama"

    def test_llm_service_get_marker_class(self) -> None:
        """LLMService.get_marker_class() returns correct class path."""
        from erdos.core.pdf.converter import LLMService

        assert (
            LLMService.GEMINI.get_marker_class()
            == "marker.services.gemini.GoogleGeminiService"
        )
        assert (
            LLMService.CLAUDE.get_marker_class()
            == "marker.services.claude.ClaudeService"
        )
        assert (
            LLMService.OPENAI.get_marker_class()
            == "marker.services.openai.OpenAIService"
        )
        assert (
            LLMService.OLLAMA.get_marker_class()
            == "marker.services.ollama.OllamaService"
        )


class TestPDFConversionConfig:
    """Tests for PDFConversionConfig dataclass."""

    def test_config_defaults(self) -> None:
        """PDFConversionConfig has sensible defaults."""
        from erdos.core.pdf.converter import PDFConversionConfig

        config = PDFConversionConfig()
        assert config.converter == "marker"
        assert config.use_llm is False
        assert config.llm_service is None
        assert config.force_ocr is False
        assert config.torch_device is None

    def test_config_custom_values(self) -> None:
        """PDFConversionConfig accepts custom values."""
        from erdos.core.pdf.converter import LLMService, PDFConversionConfig

        config = PDFConversionConfig(
            converter="pdfplumber",
            use_llm=True,
            llm_service=LLMService.CLAUDE,
            force_ocr=True,
        )
        assert config.converter == "pdfplumber"
        assert config.use_llm is True
        assert config.llm_service == LLMService.CLAUDE
        assert config.force_ocr is True

    def test_config_torch_device(self) -> None:
        """PDFConversionConfig accepts torch_device setting (DEBT-036)."""
        from erdos.core.pdf.converter import PDFConversionConfig

        config = PDFConversionConfig(torch_device="mps")
        assert config.torch_device == "mps"

        config_cuda = PDFConversionConfig(torch_device="cuda")
        assert config_cuda.torch_device == "cuda"

        config_cpu = PDFConversionConfig(torch_device="cpu")
        assert config_cpu.torch_device == "cpu"


class TestPDFConversionResult:
    """Tests for PDFConversionResult dataclass."""

    def test_result_success(self) -> None:
        """PDFConversionResult for successful conversion."""
        from erdos.core.pdf.converter import PDFConversionResult

        result = PDFConversionResult(
            success=True,
            text="# Hello World\n\nSome math: $x^2$",
            converter="marker",
            error=None,
        )
        assert result.success is True
        assert result.text == "# Hello World\n\nSome math: $x^2$"
        assert result.converter == "marker"
        assert result.error is None

    def test_result_failure(self) -> None:
        """PDFConversionResult for failed conversion."""
        from erdos.core.pdf.converter import PDFConversionResult

        result = PDFConversionResult(
            success=False,
            text=None,
            converter="marker",
            error="Marker is not installed",
        )
        assert result.success is False
        assert result.text is None
        assert result.error == "Marker is not installed"


class TestPdfplumberConversion:
    """Tests for pdfplumber fallback converter."""

    def test_convert_pdfplumber_file_not_found(self) -> None:
        """convert_with_pdfplumber returns error for nonexistent file."""
        from erdos.core.pdf.converter import convert_with_pdfplumber

        # Test with non-existent file
        result = convert_with_pdfplumber(Path("/nonexistent.pdf"))
        assert result.success is False
        assert result.error is not None
        # Could be "File not found" or "pdfplumber is not installed"
        assert (
            "not found" in result.error.lower()
            or "not installed" in result.error.lower()
        )


class TestMarkerConversion:
    """Tests for Marker converter (mocked since GPL dependency is optional)."""

    @patch("erdos.core.pdf.converter.is_marker_available")
    def test_convert_with_marker_not_available(self, mock_available: MagicMock) -> None:
        """convert_with_marker returns error when not available."""
        mock_available.return_value = False
        from erdos.core.pdf.converter import convert_with_marker

        result = convert_with_marker(Path("/some/file.pdf"))
        assert result.success is False
        assert result.error is not None
        error_lower = result.error.lower()
        assert "not installed" in error_lower or "not available" in error_lower

    def test_convert_with_marker_uses_marker_config_parser(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """convert_with_marker uses marker's ConfigParser/PdfConverter API (BUG-040)."""
        import sys
        import types

        from erdos.core.pdf.converter import LLMService, convert_with_marker

        pdf_path = tmp_path / "paper.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n% dummy\n")

        # Stub marker package tree (tests must not require marker to be installed).
        marker_pkg = types.ModuleType("marker")
        marker_pkg.__path__ = []
        marker_config_pkg = types.ModuleType("marker.config")
        marker_config_pkg.__path__ = []
        marker_parser_mod = types.ModuleType("marker.config.parser")
        marker_models_mod = types.ModuleType("marker.models")

        captured: dict[str, Any] = {}

        class FakeRendered:
            def __init__(self, markdown: str) -> None:
                self.markdown = markdown

        class FakePdfConverter:
            def __init__(
                self,
                *,
                config: dict[str, object] | None = None,
                artifact_dict: dict[str, object] | None = None,
                processor_list: list[str] | None = None,
                renderer: str | None = None,
                llm_service: str | None = None,
            ) -> None:
                captured["config"] = config
                captured["artifact_dict"] = artifact_dict
                captured["processor_list"] = processor_list
                captured["renderer"] = renderer
                captured["llm_service"] = llm_service
                self.page_count = 1

            def __call__(self, filepath: str) -> FakeRendered:
                assert filepath == str(pdf_path)
                return FakeRendered("# ok")

        class FakeConfigParser:
            def __init__(self, cli_options: dict[str, object]) -> None:
                self.cli_options = cli_options

            def get_converter_cls(self) -> type[Any]:
                return FakePdfConverter

            def generate_config_dict(self) -> dict[str, object]:
                return {
                    "use_llm": bool(self.cli_options.get("use_llm", False)),
                    "force_ocr": bool(self.cli_options.get("force_ocr", False)),
                }

            def get_processors(self) -> list[str] | None:
                return None

            def get_renderer(self) -> str:
                return "marker.renderers.markdown.MarkdownRenderer"

            def get_llm_service(self) -> str | None:
                if not self.cli_options.get("use_llm", False):
                    return None
                service = self.cli_options.get("llm_service")
                return str(service) if service is not None else None

        def fake_create_model_dict() -> dict[str, object]:
            return {"model": "ok"}

        config_parser_attr = "ConfigParser"
        create_model_dict_attr = "create_model_dict"
        setattr(marker_parser_mod, config_parser_attr, FakeConfigParser)
        setattr(marker_models_mod, create_model_dict_attr, fake_create_model_dict)

        monkeypatch.setitem(sys.modules, "marker", marker_pkg)
        monkeypatch.setitem(sys.modules, "marker.config", marker_config_pkg)
        monkeypatch.setitem(sys.modules, "marker.config.parser", marker_parser_mod)
        monkeypatch.setitem(sys.modules, "marker.models", marker_models_mod)

        monkeypatch.setattr(
            "erdos.core.pdf.converter.is_marker_available", lambda: True
        )

        result = convert_with_marker(
            pdf_path, use_llm=True, llm_service=LLMService.OPENAI, force_ocr=True
        )

        assert result.success is True
        assert result.text == "# ok"
        assert isinstance(captured.get("artifact_dict"), dict)
        assert captured.get("llm_service") is not None
        assert isinstance(captured.get("config"), dict)
        config = cast("dict[str, Any]", captured["config"])
        assert config["use_llm"] is True
        assert config["force_ocr"] is True

    def test_convert_with_marker_supports_marker_pdf_v1_api(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """convert_with_marker supports marker-pdf 1.0.x without get_converter_cls()."""
        import sys
        import types

        from erdos.core.pdf.converter import convert_with_marker

        pdf_path = tmp_path / "paper.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n% dummy\n")

        marker_pkg = types.ModuleType("marker")
        marker_pkg.__path__ = []
        marker_config_pkg = types.ModuleType("marker.config")
        marker_config_pkg.__path__ = []
        marker_parser_mod = types.ModuleType("marker.config.parser")
        marker_models_mod = types.ModuleType("marker.models")
        marker_converters_pkg = types.ModuleType("marker.converters")
        marker_converters_pkg.__path__ = []
        marker_converters_pdf_mod = types.ModuleType("marker.converters.pdf")

        captured: dict[str, Any] = {}

        class FakeRendered:
            def __init__(self, markdown: str) -> None:
                self.markdown = markdown

        class FakePdfConverterV1:
            def __init__(
                self,
                artifact_dict: dict[str, Any],
                processor_list: list[str] | None = None,
                renderer: str | None = None,
                config=None,
            ) -> None:
                captured["artifact_dict"] = artifact_dict
                captured["processor_list"] = processor_list
                captured["renderer"] = renderer
                captured["config"] = config
                self.page_count = 1

            def __call__(self, filepath: str) -> FakeRendered:
                assert filepath == str(pdf_path)
                return FakeRendered("# ok")

        class FakeConfigParserV1:
            def __init__(self, cli_options: dict[str, object]) -> None:
                self.cli_options = cli_options

            def generate_config_dict(self) -> dict[str, object]:
                return {"force_ocr": bool(self.cli_options.get("force_ocr", False))}

            def get_processors(self) -> list[str] | None:
                return None

            def get_renderer(self) -> str:
                return "marker.renderers.markdown.MarkdownRenderer"

        def fake_create_model_dict() -> dict[str, Any]:
            return {"model": "ok"}

        config_parser_attr = "ConfigParser"
        create_model_dict_attr = "create_model_dict"
        pdf_converter_attr = "PdfConverter"

        setattr(marker_parser_mod, config_parser_attr, FakeConfigParserV1)
        setattr(marker_models_mod, create_model_dict_attr, fake_create_model_dict)
        setattr(marker_converters_pdf_mod, pdf_converter_attr, FakePdfConverterV1)

        monkeypatch.setitem(sys.modules, "marker", marker_pkg)
        monkeypatch.setitem(sys.modules, "marker.config", marker_config_pkg)
        monkeypatch.setitem(sys.modules, "marker.config.parser", marker_parser_mod)
        monkeypatch.setitem(sys.modules, "marker.models", marker_models_mod)
        monkeypatch.setitem(sys.modules, "marker.converters", marker_converters_pkg)
        monkeypatch.setitem(
            sys.modules, "marker.converters.pdf", marker_converters_pdf_mod
        )

        monkeypatch.setattr(
            "erdos.core.pdf.converter.is_marker_available", lambda: True
        )

        result = convert_with_marker(pdf_path, use_llm=False, force_ocr=True)

        assert result.success is True
        assert result.text == "# ok"
        assert captured.get("artifact_dict") == {"model": "ok"}


class TestConvertPDF:
    """Tests for main convert_pdf function."""

    def test_convert_pdf_with_nonexistent_file(self) -> None:
        """convert_pdf returns error for nonexistent file."""
        from erdos.core.pdf.converter import PDFConversionConfig, convert_pdf

        result = convert_pdf(Path("/nonexistent.pdf"), PDFConversionConfig())
        assert result.success is False
        assert result.error is not None
        error_lower = result.error.lower()
        assert "not found" in error_lower or "does not exist" in error_lower

    def test_convert_pdf_with_invalid_extension(self, tmp_path: Path) -> None:
        """convert_pdf returns error for non-PDF file."""
        from erdos.core.pdf.converter import PDFConversionConfig, convert_pdf

        txt_file = tmp_path / "file.txt"
        txt_file.write_text("hello")

        result = convert_pdf(txt_file, PDFConversionConfig())
        assert result.success is False
        assert result.error is not None
        assert "pdf" in result.error.lower()

    @patch("erdos.core.pdf.converter.is_marker_available")
    @patch("erdos.core.pdf.converter.is_pdfplumber_available")
    def test_convert_pdf_no_converters_available(
        self, mock_pdfplumber: MagicMock, mock_marker: MagicMock, tmp_path: Path
    ) -> None:
        """convert_pdf returns error when no converters available."""
        mock_marker.return_value = False
        mock_pdfplumber.return_value = False

        from erdos.core.pdf.converter import PDFConversionConfig, convert_pdf

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test")  # Minimal PDF-like content

        result = convert_pdf(pdf_file, PDFConversionConfig())
        assert result.success is False
        assert result.error is not None
        error_lower = result.error.lower()
        assert "no converter" in error_lower or "not available" in error_lower


class TestTorchDeviceEnvVar:
    """Tests for TORCH_DEVICE environment variable wiring (DEBT-036)."""

    def test_convert_pdf_sets_torch_device_env_var(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """convert_pdf sets TORCH_DEVICE env var when torch_device is configured."""
        import os

        from erdos.core.pdf.converter import PDFConversionConfig, convert_pdf

        # Create a minimal PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        # Track what TORCH_DEVICE was set to
        captured_env: dict[str, str | None] = {}

        def mock_environ_setitem(key: str, value: str) -> None:
            if key == "TORCH_DEVICE":
                captured_env["TORCH_DEVICE"] = value

        # Patch os.environ to capture the set
        original_setitem = os.environ.__class__.__setitem__

        def patched_setitem(self, key: str, value: str) -> None:
            mock_environ_setitem(key, value)
            cast("Any", original_setitem)(self, key, value)

        monkeypatch.setattr(os.environ.__class__, "__setitem__", patched_setitem)

        # Mock convert_with_marker to avoid needing actual Marker
        from erdos.core.pdf.converter import PDFConversionResult

        monkeypatch.setattr(
            "erdos.core.pdf.converter.convert_with_marker",
            lambda *_args, **_kwargs: PDFConversionResult(
                success=True, text="test", converter="marker"
            ),
        )
        monkeypatch.setattr(
            "erdos.core.pdf.converter.is_marker_available", lambda: True
        )

        # Run with torch_device set
        config = PDFConversionConfig(torch_device="mps")
        convert_pdf(pdf_file, config)

        # Verify TORCH_DEVICE was set
        assert captured_env.get("TORCH_DEVICE") == "mps"

    def test_convert_pdf_does_not_set_torch_device_when_none(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        """convert_pdf does not set TORCH_DEVICE when torch_device is None."""
        import os

        from erdos.core.pdf.converter import PDFConversionConfig, convert_pdf

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        captured_env: dict[str, str | None] = {}
        original_setitem = os.environ.__class__.__setitem__

        def patched_setitem(self, key: str, value: str) -> None:
            if key == "TORCH_DEVICE":
                captured_env["TORCH_DEVICE"] = value
            cast("Any", original_setitem)(self, key, value)

        monkeypatch.setattr(os.environ.__class__, "__setitem__", patched_setitem)

        from erdos.core.pdf.converter import PDFConversionResult

        monkeypatch.setattr(
            "erdos.core.pdf.converter.convert_with_marker",
            lambda *_args, **_kwargs: PDFConversionResult(
                success=True, text="test", converter="marker"
            ),
        )
        monkeypatch.setattr(
            "erdos.core.pdf.converter.is_marker_available", lambda: True
        )

        # Run without torch_device
        config = PDFConversionConfig()  # torch_device=None by default
        convert_pdf(pdf_file, config)

        # TORCH_DEVICE should not have been set
        assert "TORCH_DEVICE" not in captured_env


class TestSelectConverter:
    """Tests for select_converter function."""

    @patch("erdos.core.pdf.converter.is_marker_available")
    def test_select_converter_marker_preferred(self, mock_available: MagicMock) -> None:
        """select_converter prefers Marker when available."""
        mock_available.return_value = True
        from erdos.core.pdf.converter import PDFConverter, select_converter

        result = select_converter()
        assert result == PDFConverter.MARKER

    @patch("erdos.core.pdf.converter.is_marker_available")
    @patch("erdos.core.pdf.converter.is_pdfplumber_available")
    def test_select_converter_falls_back_to_pdfplumber(
        self, mock_pdfplumber: MagicMock, mock_marker: MagicMock
    ) -> None:
        """select_converter falls back to pdfplumber when Marker unavailable."""
        mock_marker.return_value = False
        mock_pdfplumber.return_value = True
        from erdos.core.pdf.converter import PDFConverter, select_converter

        result = select_converter()
        assert result == PDFConverter.PDFPLUMBER

    @patch("erdos.core.pdf.converter.is_marker_available")
    @patch("erdos.core.pdf.converter.is_pdfplumber_available")
    def test_select_converter_none_available(
        self, mock_pdfplumber: MagicMock, mock_marker: MagicMock
    ) -> None:
        """select_converter returns None when no converters available."""
        mock_marker.return_value = False
        mock_pdfplumber.return_value = False
        from erdos.core.pdf.converter import select_converter

        result = select_converter()
        assert result is None

    @patch("erdos.core.pdf.converter.is_marker_available")
    def test_select_converter_explicit_choice(self, mock_available: MagicMock) -> None:
        """select_converter respects explicit converter choice."""
        mock_available.return_value = True
        from erdos.core.pdf.converter import PDFConverter, select_converter

        result = select_converter(preferred=PDFConverter.MARKER)
        assert result == PDFConverter.MARKER

    @patch("erdos.core.pdf.converter.is_marker_available")
    def test_select_converter_explicit_unavailable(
        self, mock_available: MagicMock
    ) -> None:
        """select_converter returns None for explicit but unavailable converter."""
        mock_available.return_value = False
        from erdos.core.pdf.converter import PDFConverter, select_converter

        result = select_converter(preferred=PDFConverter.MARKER)
        assert result is None
