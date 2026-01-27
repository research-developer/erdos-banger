"""Unit tests for BM25/FTS5 query escaping helpers."""

from erdos.core.search.bm25 import safe_fts5_query


def test_safe_fts5_query_normalizes_boolean_operators() -> None:
    assert safe_fts5_query("apple and banana") == "apple AND banana"
    assert safe_fts5_query("primes or integer") == "primes OR integer"


def test_safe_fts5_query_plain_mode_drops_stopwords() -> None:
    assert (
        safe_fts5_query("apple and banana", allow_advanced_syntax=False)
        == '"apple" OR "banana"'
    )


def test_safe_fts5_query_preserves_phrases() -> None:
    assert safe_fts5_query('"exact phrase"') == '"exact phrase"'


def test_safe_fts5_query_preserves_prefix() -> None:
    assert safe_fts5_query("prim*") == "prim*"


def test_safe_fts5_query_replaces_hyphens_in_advanced_mode() -> None:
    assert safe_fts5_query("sum-free AND sets") == "sum free AND sets"
    assert (
        safe_fts5_query("sum-free AND sets", allow_advanced_syntax=False)
        == '"sum" OR "free" OR "sets"'
    )


def test_safe_fts5_query_empty_returns_empty_match() -> None:
    assert safe_fts5_query("   ", allow_advanced_syntax=False) == '""'
    assert safe_fts5_query("and or not", allow_advanced_syntax=False) == '""'
