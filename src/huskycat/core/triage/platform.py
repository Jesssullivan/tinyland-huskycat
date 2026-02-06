"""Platform detection and base adapter for forge APIs."""

import logging
import re
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PlatformType(Enum):
    """Supported forge platforms."""

    GITLAB = "gitlab"
    GITHUB = "github"
    CODEBERG = "codeberg"
    UNKNOWN = "unknown"


@dataclass
class IssueRef:
    """Reference to an issue on a forge."""

    number: int
    platform: PlatformType
    project: str = ""  # owner/repo or group/project


@dataclass
class MRRef:
    """Reference to a merge/pull request."""

    number: int
    platform: PlatformType
    project: str = ""
    source_branch: str = ""


@dataclass
class TriageAction:
    """An action to perform on a forge."""

    action_type: str  # "add_label", "set_iteration", "set_milestone"
    target_type: str  # "issue", "mr", "pr"
    target_number: int
    params: Dict = field(default_factory=dict)
    success: bool = False
    message: str = ""


def detect_platform(repo_path: Optional[str] = None) -> PlatformType:
    """Detect the forge platform from git remote URLs.

    Args:
        repo_path: Path to git repo (uses cwd if None)

    Returns:
        Detected PlatformType
    """
    try:
        cmd = ["git", "remote", "-v"]
        if repo_path:
            cmd = ["git", "-C", repo_path, "remote", "-v"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=5
        )
        if result.returncode != 0:
            return PlatformType.UNKNOWN

        remote_output = result.stdout.lower()

        # Check patterns (order matters - most specific first)
        if "codeberg.org" in remote_output:
            return PlatformType.CODEBERG
        if "gitlab" in remote_output:
            return PlatformType.GITLAB
        if "github" in remote_output:
            return PlatformType.GITHUB

        return PlatformType.UNKNOWN
    except Exception as e:
        logger.debug(f"Platform detection failed: {e}")
        return PlatformType.UNKNOWN


def get_remote_project(repo_path: Optional[str] = None) -> str:
    """Extract owner/repo from git remote URL.

    Returns:
        String like 'owner/repo' or 'group/subgroup/project'
    """
    try:
        cmd = ["git", "remote", "get-url", "origin"]
        if repo_path:
            cmd = ["git", "-C", repo_path, "remote", "get-url", "origin"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=5
        )
        if result.returncode != 0:
            return ""

        url = result.stdout.strip()

        # SSH format: git@host:owner/repo.git
        ssh_match = re.match(r"git@[^:]+:(.+?)(?:\.git)?$", url)
        if ssh_match:
            return ssh_match.group(1)

        # HTTPS format: https://host/owner/repo.git
        https_match = re.match(r"https?://[^/]+/(.+?)(?:\.git)?$", url)
        if https_match:
            return https_match.group(1)

        return ""
    except Exception as e:
        logger.debug(f"Remote project extraction failed: {e}")
        return ""


class PlatformAdapter(ABC):
    """Abstract base for forge platform adapters."""

    def __init__(self, project: str = ""):
        self.project = project

    @property
    @abstractmethod
    def platform_type(self) -> PlatformType:
        """The platform this adapter handles."""

    @abstractmethod
    def add_labels(
        self, target_type: str, number: int, labels: List[str]
    ) -> TriageAction:
        """Add labels to an issue or MR/PR.

        Args:
            target_type: 'issue' or 'mr'/'pr'
            number: Issue/MR number
            labels: Labels to add
        """

    @abstractmethod
    def set_iteration(
        self, target_type: str, number: int, iteration: str
    ) -> TriageAction:
        """Set iteration/sprint on an issue or MR.

        Args:
            target_type: 'issue' or 'mr'
            number: Issue/MR number
            iteration: Iteration identifier
        """

    @abstractmethod
    def find_mr_by_branch(self, branch: str) -> Optional[MRRef]:
        """Find an open MR/PR for the given branch.

        Args:
            branch: Source branch name

        Returns:
            MRRef if found, None otherwise
        """

    @abstractmethod
    def check_cli_available(self) -> bool:
        """Check if the platform CLI tool is available."""
