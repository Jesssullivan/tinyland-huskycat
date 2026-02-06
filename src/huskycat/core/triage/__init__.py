"""Auto-triage engine for git post-hooks.

Detects issues/MRs from branch names and commit messages,
auto-labels based on file paths and branch prefixes,
and sets iterations to the current week.

Supports GitLab, GitHub, and Codeberg (Gitea) platforms.
"""

from .engine import TriageEngine, TriageConfig, TriageResult
from .platform import PlatformAdapter, PlatformType, detect_platform

__all__ = [
    "TriageEngine",
    "TriageConfig",
    "TriageResult",
    "PlatformAdapter",
    "PlatformType",
    "detect_platform",
]
