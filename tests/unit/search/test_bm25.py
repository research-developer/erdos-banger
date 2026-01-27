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
