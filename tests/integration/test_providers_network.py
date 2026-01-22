"""Integration tests for MetadataProvider with real APIs (SPEC-022).

These tests make actual network requests to external APIs.
Run with: uv run pytest -m requires_network tests/integration/test_providers_network.py
"""

import pytest

from erdos.core.providers import (
    ArxivProvider,
    CrossrefProvider,
    FallbackProvider,
    OpenAlexProvider,
)


@pytest.mark.requires_network
class TestOpenAlexProviderIntegration:
    """Integration tests for OpenAlexProvider with real API."""

    def test_get_by_doi_real(self) -> None:
        """Test real DOI lookup via OpenAlex."""
        provider = OpenAlexProvider.from_env()
        # Use a stable, well-known DOI (Nature paper about CRISPR)
        result = provider.get_by_doi("10.1038/nature12373")

        assert result is not None
        assert result.doi == "10.1038/nature12373"
        # Title contains "programmable" or relates to CRISPR
        assert result.title is not None

    def test_get_by_doi_not_found(self) -> None:
        """Test DOI not found returns None."""
        provider = OpenAlexProvider.from_env()
        result = provider.get_by_doi("10.1234/nonexistent-doi-that-does-not-exist")

        assert result is None

    def test_get_by_arxiv_real(self) -> None:
        """Test real arXiv lookup via OpenAlex."""
        provider = OpenAlexProvider.from_env()
        # Use a well-known arXiv paper (Attention Is All You Need)
        result = provider.get_by_arxiv("1706.03762")

        assert result is not None
        assert result.arxiv_id == "1706.03762"

    def test_search_real(self) -> None:
        """Test real search via OpenAlex."""
        provider = OpenAlexProvider.from_env()
        results = provider.search("prime gap erdos", limit=5)

        assert isinstance(results, list)
        # We expect at least some results for this query
        # (but don't assert > 0 in case API changes)


@pytest.mark.requires_network
class TestCrossrefProviderIntegration:
    """Integration tests for CrossrefProvider with real API (DOILookupProvider only)."""

    def test_get_by_doi_real(self) -> None:
        """Test real DOI lookup via Crossref."""
        provider = CrossrefProvider.from_env()
        # Use a stable DOI
        result = provider.get_by_doi("10.1038/nature12373")

        assert result is not None
        assert result.doi == "10.1038/nature12373"
        assert result.title is not None

    def test_get_by_doi_not_found(self) -> None:
        """Test DOI not found returns None."""
        provider = CrossrefProvider.from_env()
        result = provider.get_by_doi("10.1234/nonexistent-doi-that-does-not-exist")

        assert result is None

    def test_isp_compliance(self) -> None:
        """CrossrefProvider should only implement DOI lookup (ISP compliance)."""
        provider = CrossrefProvider.from_env()

        # Should have get_by_doi
        assert hasattr(provider, "get_by_doi")

        # Should NOT have get_by_arxiv or search (ISP compliance)
        assert not hasattr(provider, "get_by_arxiv")
        assert not hasattr(provider, "search")


@pytest.mark.requires_network
class TestArxivProviderIntegration:
    """Integration tests for ArxivProvider with real API (ArxivLookupProvider only)."""

    def test_get_by_arxiv_real(self) -> None:
        """Test real arXiv lookup via arXiv API."""
        provider = ArxivProvider(timeout=30.0)
        # Use a well-known arXiv paper
        result = provider.get_by_arxiv("1706.03762")

        assert result is not None
        assert "1706.03762" in (result.arxiv_id or "")

    def test_isp_compliance(self) -> None:
        """ArxivProvider should only implement arXiv lookup (ISP compliance)."""
        provider = ArxivProvider(timeout=30.0)

        # Should have get_by_arxiv
        assert hasattr(provider, "get_by_arxiv")

        # Should NOT have get_by_doi or search (ISP compliance)
        assert not hasattr(provider, "get_by_doi")
        assert not hasattr(provider, "search")


@pytest.mark.requires_network
class TestFallbackProviderIntegration:
    """Integration tests for FallbackProvider with real APIs (ISP-compliant version)."""

    def test_openalex_to_crossref_fallback_doi(self) -> None:
        """Test DOI fallback chain finds DOI via primary provider."""
        openalex = OpenAlexProvider.from_env()
        crossref = CrossrefProvider.from_env()

        provider = FallbackProvider(
            doi_chain=[openalex, crossref],
            arxiv_chain=[openalex],
            search_chain=[openalex],
        )

        result = provider.get_by_doi("10.1038/nature12373")

        assert result is not None
        assert result.doi == "10.1038/nature12373"

    def test_openalex_to_arxiv_fallback_arxiv(self) -> None:
        """Test arXiv fallback chain finds arXiv via providers."""
        openalex = OpenAlexProvider.from_env()
        arxiv = ArxivProvider(timeout=30.0)

        provider = FallbackProvider(
            doi_chain=[openalex],
            arxiv_chain=[openalex, arxiv],
            search_chain=[openalex],
        )

        result = provider.get_by_arxiv("1706.03762")

        assert result is not None
        # Should find via OpenAlex or arXiv

    def test_provider_name_shows_chains(self) -> None:
        """Test provider name reflects the capability chains."""
        openalex = OpenAlexProvider.from_env()
        crossref = CrossrefProvider.from_env()
        arxiv = ArxivProvider(timeout=30.0)

        provider = FallbackProvider(
            doi_chain=[openalex, crossref],
            arxiv_chain=[openalex, arxiv],
            search_chain=[openalex],
        )

        # Should show capability-specific chains
        assert "doi:" in provider.provider_name
        assert "arxiv:" in provider.provider_name
        assert "search:" in provider.provider_name
        assert "openalex" in provider.provider_name
        assert "crossref" in provider.provider_name
