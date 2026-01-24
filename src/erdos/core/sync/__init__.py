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
- submodule: Git submodule operations for teorth/erdosproblems
- forum: Forum proof-link extraction (GitHub/GitLab repo URLs)
"""

from erdos.core.sync.forum import (
    ForumFetchError,
    extract_proof_links_from_html,
    fetch_and_parse_forum,
    fetch_forum_thread,
    parse_forum_html,
    save_proof_links_cache,
)
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
from erdos.core.sync.submodule import (
    SubmoduleCheckError,
    SubmoduleError,
    SubmoduleFetchError,
    SubmoduleNotInitializedError,
    check_submodule_staleness,
    get_submodule_commit,
    get_submodule_path,
    load_submodule_problems,
    parse_problems_yaml,
    update_submodule,
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
    "ForumFetchError",
    "ProofLink",
    "ProofLinksCache",
    "ProofProvenance",
    "SubmoduleCheckError",
    "SubmoduleError",
    "SubmoduleFetchError",
    "SubmoduleNotInitializedError",
    "SubmoduleProblemData",
    "SubmoduleSyncStatus",
    "VerificationStatus",
    "VerificationStrength",
    "WebsiteFetchError",
    "WebsiteParseError",
    "WebsiteProblemData",
    "WebsiteReferenceData",
    "WebsiteSyncStatus",
    "check_submodule_staleness",
    "extract_proof_links_from_html",
    "fetch_and_parse_forum",
    "fetch_and_parse_problem",
    "fetch_forum_thread",
    "fetch_latex_source",
    "fetch_problem_page",
    "get_submodule_commit",
    "get_submodule_path",
    "load_submodule_problems",
    "merge_all_problems",
    "merge_problem_data",
    "parse_forum_html",
    "parse_problem_html",
    "parse_problems_yaml",
    "save_latex_source",
    "save_proof_links_cache",
    "update_submodule",
]
