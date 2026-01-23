"""Unit tests for MetadataProvider implementations (SPEC-022)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from erdos.core.models import ReferenceRecord


class MockDOIProvider:
    """Mock DOILookupProvider for testing DOI fallback chains."""

    def __init__(
        self,
        name: str,
        results: dict[str, ReferenceRecord] | None = None,
    ) -> None:
        self._name = name
        self._results: dict[str, ReferenceRecord] = results or {}
        self._call_log: list[tuple[str, tuple[str, ...]]] = []

    @property
    def provider_name(self) -> str:
        return self._name

    def get_by_doi(self, doi: str) -> ReferenceRecord | None:
        self._call_log.append(("get_by_doi", (doi,)))
        return self._results.get(doi)


class MockArxivProvider:
    """Mock ArxivLookupProvider for testing arXiv fallback chains."""

    def __init__(
        self,
        name: str,
        results: dict[str, ReferenceRecord] | None = None,
    ) -> None:
        self._name = name
        self._results: dict[str, ReferenceRecord] = results or {}
        self._call_log: list[tuple[str, tuple[str, ...]]] = []

    @property
    def provider_name(self) -> str:
        return self._name

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord | None:
        self._call_log.append(("get_by_arxiv", (arxiv_id,)))
        return self._results.get(arxiv_id)


class MockSearchProvider:
    """Mock SearchableMetadataProvider for testing search fallback chains."""

    def __init__(
        self,
        name: str,
        results: dict[str, list[ReferenceRecord]] | None = None,
    ) -> None:
        self._name = name
        self._results: dict[str, list[ReferenceRecord]] = results or {}
        self._call_log: list[tuple[str, tuple[str, ...]]] = []

    @property
    def provider_name(self) -> str:
        return self._name

    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]:
        self._call_log.append(("search", (query, str(limit))))
        return self._results.get(query, [])


class TestMetadataProviderProtocol:
    """Tests for MetadataProvider protocol definitions."""

    def test_protocol_exists_in_ports(self) -> None:
        """MetadataProvider protocol should be defined in ports.py."""
        from erdos.core.ports import MetadataProvider

        assert hasattr(MetadataProvider, "provider_name")
        assert hasattr(MetadataProvider, "get_by_doi")
        assert hasattr(MetadataProvider, "get_by_arxiv")
        assert hasattr(MetadataProvider, "search")

    def test_segregated_protocols_exist(self) -> None:
        """ISP-compliant protocols should be defined in ports.py."""
        from erdos.core.ports import (
            ArxivLookupProvider,
            DOILookupProvider,
            SearchableMetadataProvider,
        )

        # DOILookupProvider
        assert hasattr(DOILookupProvider, "provider_name")
        assert hasattr(DOILookupProvider, "get_by_doi")

        # ArxivLookupProvider
        assert hasattr(ArxivLookupProvider, "provider_name")
        assert hasattr(ArxivLookupProvider, "get_by_arxiv")

        # SearchableMetadataProvider
        assert hasattr(SearchableMetadataProvider, "provider_name")
        assert hasattr(SearchableMetadataProvider, "search")

    def test_mock_providers_satisfy_protocols(self) -> None:
        """Mock providers should satisfy their respective protocols."""
        doi_mock = MockDOIProvider("test")
        assert hasattr(doi_mock, "provider_name")
        assert hasattr(doi_mock, "get_by_doi")
        assert doi_mock.provider_name == "test"

        arxiv_mock = MockArxivProvider("test")
        assert hasattr(arxiv_mock, "provider_name")
        assert hasattr(arxiv_mock, "get_by_arxiv")

        search_mock = MockSearchProvider("test")
        assert hasattr(search_mock, "provider_name")
        assert hasattr(search_mock, "search")


class TestFallbackProvider:
    """Tests for FallbackProvider chain logic (ISP-compliant version)."""

    def test_requires_at_least_one_chain(self) -> None:
        """FallbackProvider should require at least one non-empty chain."""
        from erdos.core.providers import FallbackProvider

        with pytest.raises(ValueError, match="at least one provider"):
            FallbackProvider(doi_chain=[], arxiv_chain=[], search_chain=[])

    def test_uses_primary_doi_when_successful(self) -> None:
        """Primary DOI provider result is returned if found."""
        from erdos.core.providers import FallbackProvider

        record = ReferenceRecord(title="Test Paper", doi="10.1234/test")
        primary = MockDOIProvider("primary", {"10.1234/test": record})
        fallback = MockDOIProvider("fallback")

        provider = FallbackProvider(
            doi_chain=[primary, fallback],
            arxiv_chain=[],
            search_chain=[],
        )
        result = provider.get_by_doi("10.1234/test")

        assert result == record
        # Fallback should not be called
        assert len(fallback._call_log) == 0

    def test_falls_back_doi_when_primary_returns_none(self) -> None:
        """DOI fallback is used when primary returns None."""
        from erdos.core.providers import FallbackProvider

        record = ReferenceRecord(title="Test Paper", doi="10.1234/test")
        primary = MockDOIProvider("primary")  # Returns None
        fallback = MockDOIProvider("fallback", {"10.1234/test": record})

        provider = FallbackProvider(
            doi_chain=[primary, fallback],
            arxiv_chain=[],
            search_chain=[],
        )
        result = provider.get_by_doi("10.1234/test")

        assert result == record
        # Both should be called
        assert len(primary._call_log) == 1
        assert len(fallback._call_log) == 1

    def test_falls_back_doi_when_primary_raises_expected_error(self) -> None:
        """DOI fallback is used when primary raises an expected exception type."""
        import requests

        from erdos.core.providers import FallbackProvider

        record = ReferenceRecord(title="Test Paper", doi="10.1234/test")

        primary = MagicMock()
        primary.provider_name = "primary"
        # RequestException is an expected error type per port contract
        primary.get_by_doi.side_effect = requests.RequestException("API error")

        fallback = MockDOIProvider("fallback", {"10.1234/test": record})

        provider = FallbackProvider(
            doi_chain=[primary, fallback],
            arxiv_chain=[],
            search_chain=[],
        )
        result = provider.get_by_doi("10.1234/test")

        assert result == record

    def test_propagates_unexpected_exceptions_doi(self) -> None:
        """Unexpected exceptions (programming errors) should propagate, not be caught."""
        from erdos.core.providers import FallbackProvider

        primary = MagicMock()
        primary.provider_name = "primary"
        # RuntimeError is NOT an expected error type - should propagate
        primary.get_by_doi.side_effect = RuntimeError("Programming bug")

        fallback = MockDOIProvider("fallback")

        provider = FallbackProvider(
            doi_chain=[primary, fallback],
            arxiv_chain=[],
            search_chain=[],
        )

        with pytest.raises(RuntimeError, match="Programming bug"):
            provider.get_by_doi("10.1234/test")

    def test_propagates_unexpected_exceptions_arxiv(self) -> None:
        """Unexpected exceptions for arXiv lookups should propagate."""
        from erdos.core.providers import FallbackProvider

        primary = MagicMock()
        primary.provider_name = "primary"
        primary.get_by_arxiv.side_effect = TypeError("Unexpected type bug")

        fallback = MockArxivProvider("fallback")

        provider = FallbackProvider(
            doi_chain=[],
            arxiv_chain=[primary, fallback],
            search_chain=[],
        )

        with pytest.raises(TypeError, match="Unexpected type bug"):
            provider.get_by_arxiv("2103.03874")

    def test_propagates_unexpected_exceptions_search(self) -> None:
        """Unexpected exceptions for search should propagate."""
        from erdos.core.providers import FallbackProvider

        primary = MagicMock()
        primary.provider_name = "primary"
        primary.search.side_effect = AttributeError("Missing attribute")

        fallback = MockSearchProvider("fallback")

        provider = FallbackProvider(
            doi_chain=[],
            arxiv_chain=[],
            search_chain=[primary, fallback],
        )

        with pytest.raises(AttributeError, match="Missing attribute"):
            provider.search("erdos", limit=10)

    def test_falls_back_doi_on_value_error(self) -> None:
        """ValueError (invalid identifier) should trigger fallback per contract."""
        from erdos.core.providers import FallbackProvider

        record = ReferenceRecord(title="Test Paper", doi="10.1234/test")

        primary = MagicMock()
        primary.provider_name = "primary"
        primary.get_by_doi.side_effect = ValueError("Invalid DOI format")

        fallback = MockDOIProvider("fallback", {"10.1234/test": record})

        provider = FallbackProvider(
            doi_chain=[primary, fallback],
            arxiv_chain=[],
            search_chain=[],
        )
        result = provider.get_by_doi("10.1234/test")

        assert result == record

    def test_returns_none_when_all_doi_providers_fail(self) -> None:
        """None is returned when all DOI providers return None."""
        from erdos.core.providers import FallbackProvider

        primary = MockDOIProvider("primary")
        fallback = MockDOIProvider("fallback")

        provider = FallbackProvider(
            doi_chain=[primary, fallback],
            arxiv_chain=[],
            search_chain=[],
        )
        result = provider.get_by_doi("10.1234/nonexistent")

        assert result is None

    def test_provider_name_shows_capability_chains(self) -> None:
        """Provider name reflects the capability-specific chains."""
        from erdos.core.providers import FallbackProvider

        doi1 = MockDOIProvider("openalex")
        doi2 = MockDOIProvider("crossref")
        arxiv = MockArxivProvider("arxiv")
        search = MockSearchProvider("openalex_search")

        provider = FallbackProvider(
            doi_chain=[doi1, doi2],
            arxiv_chain=[arxiv],
            search_chain=[search],
        )

        assert "doi:openalex -> crossref" in provider.provider_name
        assert "arxiv:arxiv" in provider.provider_name
        assert "search:openalex_search" in provider.provider_name

    def test_get_by_arxiv_fallback(self) -> None:
        """Fallback works for arXiv lookups."""
        from erdos.core.providers import FallbackProvider

        record = ReferenceRecord(title="arXiv Paper", arxiv_id="2103.03874")
        primary = MockArxivProvider("primary")
        fallback = MockArxivProvider("fallback", {"2103.03874": record})

        provider = FallbackProvider(
            doi_chain=[],
            arxiv_chain=[primary, fallback],
            search_chain=[],
        )
        result = provider.get_by_arxiv("2103.03874")

        assert result == record

    def test_search_fallback(self) -> None:
        """Fallback works for search queries."""
        from erdos.core.providers import FallbackProvider

        records = [
            ReferenceRecord(title="Paper 1", doi="10.1234/1"),
            ReferenceRecord(title="Paper 2", doi="10.1234/2"),
        ]
        primary = MockSearchProvider("primary")  # Returns empty list
        fallback = MockSearchProvider("fallback", {"erdos": records})

        provider = FallbackProvider(
            doi_chain=[],
            arxiv_chain=[],
            search_chain=[primary, fallback],
        )
        result = provider.search("erdos", limit=10)

        assert result == records


class TestOpenAlexProvider:
    """Tests for OpenAlexProvider wrapper."""

    def test_provider_name(self) -> None:
        """OpenAlexProvider should have 'openalex' as provider name."""
        from erdos.core.providers import OpenAlexProvider

        # Create with a mock client to avoid network
        provider = OpenAlexProvider._create_with_client(MagicMock())
        assert provider.provider_name == "openalex"

    def test_get_by_doi_delegates_to_client(self) -> None:
        """get_by_doi should delegate to the wrapped OpenAlexClient."""
        from erdos.core.providers import OpenAlexProvider

        mock_client = MagicMock()
        expected = ReferenceRecord(title="Test", doi="10.1234/test")
        mock_client.get_by_doi.return_value = expected

        provider = OpenAlexProvider._create_with_client(mock_client)
        result = provider.get_by_doi("10.1234/test")

        assert result == expected
        mock_client.get_by_doi.assert_called_once_with("10.1234/test")

    def test_get_by_doi_returns_none_on_404(self) -> None:
        """get_by_doi should return None on 404, not raise."""
        import requests

        from erdos.core.providers import OpenAlexProvider

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = requests.HTTPError(response=mock_response)
        mock_client.get_by_doi.side_effect = http_error

        provider = OpenAlexProvider._create_with_client(mock_client)
        result = provider.get_by_doi("10.1234/notfound")

        assert result is None

    def test_get_by_arxiv_delegates_to_client(self) -> None:
        """get_by_arxiv should delegate to the wrapped OpenAlexClient."""
        from erdos.core.providers import OpenAlexProvider

        mock_client = MagicMock()
        expected = ReferenceRecord(title="arXiv paper", arxiv_id="2103.03874")
        mock_client.get_by_arxiv.return_value = expected

        provider = OpenAlexProvider._create_with_client(mock_client)
        result = provider.get_by_arxiv("2103.03874")

        assert result == expected
        mock_client.get_by_arxiv.assert_called_once_with("2103.03874")

    def test_get_by_arxiv_returns_none_on_value_error(self) -> None:
        """get_by_arxiv should return None when client raises ValueError."""
        from erdos.core.providers import OpenAlexProvider

        mock_client = MagicMock()
        mock_client.get_by_arxiv.side_effect = ValueError("Not found")

        provider = OpenAlexProvider._create_with_client(mock_client)
        result = provider.get_by_arxiv("2103.03874")

        assert result is None

    def test_search_delegates_to_client(self) -> None:
        """search should delegate to the wrapped OpenAlexClient."""
        from erdos.core.providers import OpenAlexProvider

        mock_client = MagicMock()
        expected = [ReferenceRecord(title="Paper", doi="10.1234/test")]
        mock_client.search.return_value = expected

        provider = OpenAlexProvider._create_with_client(mock_client)
        result = provider.search("erdos", limit=10)

        assert result == expected
        mock_client.search.assert_called_once_with("erdos", limit=10)


class TestCrossrefProvider:
    """Tests for CrossrefProvider wrapper (DOILookupProvider only)."""

    def test_provider_name(self) -> None:
        """CrossrefProvider should have 'crossref' as provider name."""
        from erdos.core.providers import CrossrefProvider

        provider = CrossrefProvider(mailto="test@example.com")
        assert provider.provider_name == "crossref"

    def test_only_implements_doi_lookup(self) -> None:
        """CrossrefProvider should only implement get_by_doi (ISP compliance)."""
        from erdos.core.providers import CrossrefProvider

        provider = CrossrefProvider(mailto="test@example.com")

        # Should have get_by_doi
        assert hasattr(provider, "get_by_doi")

        # Should NOT have get_by_arxiv or search (ISP compliance)
        assert not hasattr(provider, "get_by_arxiv")
        assert not hasattr(provider, "search")


class TestArxivProvider:
    """Tests for ArxivProvider wrapper (ArxivLookupProvider only)."""

    def test_provider_name(self) -> None:
        """ArxivProvider should have 'arxiv' as provider name."""
        from erdos.core.providers import ArxivProvider

        provider = ArxivProvider(timeout=30.0)
        assert provider.provider_name == "arxiv"

    def test_only_implements_arxiv_lookup(self) -> None:
        """ArxivProvider should only implement get_by_arxiv (ISP compliance)."""
        from erdos.core.providers import ArxivProvider

        provider = ArxivProvider(timeout=30.0)

        # Should have get_by_arxiv
        assert hasattr(provider, "get_by_arxiv")

        # Should NOT have get_by_doi or search (ISP compliance)
        assert not hasattr(provider, "get_by_doi")
        assert not hasattr(provider, "search")


class TestBuildProviderFromSource:
    """Tests for build_provider_from_source factory function."""

    def test_creates_fallback_chain(self) -> None:
        """build_provider_from_source should create a FallbackProvider with chains."""
        from erdos.core.ingest import MetadataSource, build_provider_from_source
        from erdos.core.providers import FallbackProvider

        provider = build_provider_from_source(
            MetadataSource.OPENALEX, mailto="test@example.com", timeout=30.0
        )

        assert isinstance(provider, FallbackProvider)
        # Check that all capability chains are represented
        assert "doi:" in provider.provider_name
        assert "arxiv:" in provider.provider_name
        assert "search:" in provider.provider_name
        # Check expected providers
        assert "openalex" in provider.provider_name
        assert "crossref" in provider.provider_name
        assert "arxiv" in provider.provider_name
