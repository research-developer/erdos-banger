"""Unified problem data sync (SPEC-035).

This package provides data synchronization between multiple Erdős problem sources:
- teorth/erdosproblems submodule (status, prize, tags, formalized, oeis)
- erdosproblems.com website (title, statement, references)
- erdosproblems.com forum (proof repository links)
- google-deepmind/formal-conjectures (Lean statements)

Key modules:
- models: Pydantic models for sync cache, extraction, and provenance
- merge: Pure merge logic for combining data sources
- website: Website data extraction (fetch + parse)
"""

from erdos.core.sync.merge import merge_all_problems, merge_problem_data
from erdos.core.sync.models import (
    ProofLink,
    ProofLinksCache,
    ProofProvenance,
    SubmoduleProblemData,
    SubmoduleSyncStatus,
    VerificationStatus,
    VerificationStrength,
    WebsiteProblemData,
    WebsiteReferenceData,
    WebsiteSyncStatus,
)
from erdos.core.sync.website import (
    WebsiteFetchError,
    WebsiteParseError,
    fetch_and_parse_problem,
    fetch_latex_source,
    fetch_problem_page,
    parse_problem_html,
    save_latex_source,
)


__all__ = [
    "ProofLink",
    "ProofLinksCache",
    "ProofProvenance",
    "SubmoduleProblemData",
    "SubmoduleSyncStatus",
    "VerificationStatus",
    "VerificationStrength",
    "WebsiteFetchError",
    "WebsiteParseError",
    "WebsiteProblemData",
    "WebsiteReferenceData",
    "WebsiteSyncStatus",
    "fetch_and_parse_problem",
    "fetch_latex_source",
    "fetch_problem_page",
    "merge_all_problems",
    "merge_problem_data",
    "parse_problem_html",
    "save_latex_source",
]
