"""Research workspace (v3).

Filesystem-based, git-tracked research state:
- Per-problem workspace under `research/problems/{id:04d}/`
- Scratchpad + synthesis markdown
- Merge-safe structured records (one YAML file per record)
"""

from erdos.core.research.note import append_scratchpad_entry
from erdos.core.research.paths import (
    get_problem_dir,
    get_research_root,
    get_workspace_version,
)
from erdos.core.research.status import get_problem_status
from erdos.core.research.store_fs import (
    FSResearchStore,
    fmt_problem_workspace,
    validate_problem_workspace,
)
from erdos.core.research.synthesis import synthesize_problem
from erdos.core.research.workspace import ensure_problem_workspace


__all__ = [
    "FSResearchStore",
    "append_scratchpad_entry",
    "ensure_problem_workspace",
    "fmt_problem_workspace",
    "get_problem_dir",
    "get_problem_status",
    "get_research_root",
    "get_workspace_version",
    "synthesize_problem",
    "validate_problem_workspace",
]
