"""Unit tests for ingest fetch coordination helpers."""

from __future__ import annotations

from erdos.core.ingest.fetch import MetadataSource, build_provider_from_source
from erdos.core.providers.fallback import FallbackProvider
from erdos.core.providers.openalex import OpenAlexProvider


def test_build_provider_openalex_respects_mailto_and_timeout() -> None:
    provider = build_provider_from_source(
        MetadataSource.OPENALEX,
        mailto="cli@example.com",
        timeout=12.5,
    )

    assert isinstance(provider, FallbackProvider)
    openalex = provider.doi_chain[0]
    assert isinstance(openalex, OpenAlexProvider)
    assert openalex.client_config.email == "cli@example.com"
    assert openalex.client_config.timeout == 12.5
