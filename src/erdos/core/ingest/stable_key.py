"""Stable key generation for reference deduplication."""

from typing import Protocol


class HasIdentifiers(Protocol):
    """Protocol for objects with DOI and arXiv identifiers.

    Used by get_stable_key to work with both ReferenceEntry and ReferenceRecord.
    """

    @property
    def doi(self) -> str | None:
        """DOI identifier."""
        ...

    @property
    def arxiv_id(self) -> str | None:
        """arXiv identifier."""
        ...


def get_stable_key(obj: HasIdentifiers) -> str:
    """Get stable deduplication key for any object with identifiers.

    This function works with both ReferenceEntry and ReferenceRecord,
    eliminating the need for separate type-specific functions.

    Args:
        obj: Any object with doi and arxiv_id attributes

    Returns:
        Stable key in format "doi:<lowercased-doi>" or "arxiv:<id>",
        or empty string if no identifiers present.

    Examples:
        >>> from erdos.core.models import ReferenceEntry, ReferenceRecord
        >>> ref = ReferenceEntry(key="Test2023", doi="10.1007/BF01940595")
        >>> get_stable_key(ref)
        'doi:10.1007/bf01940595'
        >>> rec = ReferenceRecord(arxiv_id="2203.00001", title="Test", source="arxiv")
        >>> get_stable_key(rec)
        'arxiv:2203.00001'
    """
    if obj.doi:
        return f"doi:{obj.doi.lower()}"
    if obj.arxiv_id:
        return f"arxiv:{obj.arxiv_id}"
    return ""
