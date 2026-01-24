"""Unified problem data sync (SPEC-035).

This package provides data synchronization between multiple Erdős problem sources:
- teorth/erdosproblems submodule (status, prize, tags, formalized, oeis)
- erdosproblems.com website (title, statement, references)
- erdosproblems.com forum (proof repository links)
- google-deepmind/formal-conjectures (Lean statements)

Key modules:
- models: Pydantic models for sync cache, extraction, and provenance
- merge: Pure merge logic for combining data sources
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


__all__ = [
    "ProofLink",
    "ProofLinksCache",
    "ProofProvenance",
    "SubmoduleProblemData",
    "SubmoduleSyncStatus",
    "VerificationStatus",
    "VerificationStrength",
    "WebsiteProblemData",
    "WebsiteReferenceData",
    "WebsiteSyncStatus",
    "merge_all_problems",
    "merge_problem_data",
]
