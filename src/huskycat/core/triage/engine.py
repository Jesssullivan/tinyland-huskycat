"""Core triage engine for auto-labeling and iteration assignment."""

import datetime
import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from .platform import (
    IssueRef,
    MRRef,
    PlatformAdapter,
    PlatformType,
    TriageAction,
    detect_platform,
    get_remote_project,
)

logger = logging.getLogger(__name__)

# Branch name patterns for issue extraction
BRANCH_ISSUE_PATTERNS = [
    # feat/GH-123-description or fix/GL-456
    re.compile(r"(?:fix|feat|chore|docs|refactor|test|ci|perf)/(?:GH-|GL-|#)?(\d+)"),
    # sid/42-feature-name (three-tier workflow)
    re.compile(r"sid/(\d+)[-/]"),
    # mr-123 or mr/123
    re.compile(r"mr[-/](\d+)"),
    # anything-123-description (generic)
    re.compile(r"[-/](\d+)[-/]"),
    # Jira-style: PROJ-123
    re.compile(r"([A-Z]+-\d+)"),
]

# Commit message patterns for issue references
COMMIT_ISSUE_PATTERNS = [
    # Closes #123, Fixes #456, Refs #789
    re.compile(r"(?:closes?|fixes?|resolves?|refs?)\s+#(\d+)", re.IGNORECASE),
    # Direct #123 reference
    re.compile(r"(?:^|\s)#(\d+)(?:\s|$)"),
]

# Branch prefix to label mapping
BRANCH_PREFIX_LABELS: Dict[str, str] = {
    "feat/": "feature",
    "feature/": "feature",
    "fix/": "bug",
    "bugfix/": "bug",
    "hotfix/": "bug",
    "docs/": "documentation",
    "doc/": "documentation",
    "chore/": "chore",
    "refactor/": "refactor",
    "test/": "testing",
    "ci/": "ci/cd",
    "perf/": "performance",
    "style/": "style",
}

# File path to label mapping (default rules)
DEFAULT_PATH_LABELS: Dict[str, List[str]] = {
    "src/**/*.py": ["python", "backend"],
    "**/*.py": ["python"],
    "**/*.js": ["javascript"],
    "**/*.ts": ["typescript"],
    "**/*.tsx": ["typescript", "frontend"],
    "**/*.jsx": ["javascript", "frontend"],
    "**/*.nix": ["nix", "infrastructure"],
    "*.nix": ["nix", "infrastructure"],
    "docs/**": ["documentation"],
    "**/*.md": ["documentation"],
    ".gitlab-ci.yml": ["ci/cd"],
    ".gitlab/**": ["ci/cd"],
    ".github/**": ["ci/cd"],
    "ContainerFile": ["docker", "infrastructure"],
    "Dockerfile": ["docker", "infrastructure"],
    "docker-compose*": ["docker", "infrastructure"],
    "tests/**": ["testing"],
    "**/*test*.py": ["testing"],
    "flake.nix": ["nix", "infrastructure"],
    "flake.lock": ["nix"],
    "*.tf": ["terraform", "infrastructure"],
    "*.yml": ["configuration"],
    "*.yaml": ["configuration"],
    "justfile": ["build-system"],
    "Makefile": ["build-system"],
    "package.json": ["build-system"],
    "pyproject.toml": ["build-system"],
}


@dataclass
class TriageConfig:
    """Configuration for the triage engine."""

    enabled: bool = True
    auto_label: bool = True
    auto_iteration: bool = True
    platforms: List[str] = field(default_factory=lambda: ["gitlab", "github", "codeberg"])
    path_labels: Dict[str, List[str]] = field(default_factory=lambda: dict(DEFAULT_PATH_LABELS))
    branch_prefix_labels: Dict[str, str] = field(
        default_factory=lambda: dict(BRANCH_PREFIX_LABELS)
    )
    iteration_format: str = "%Y-W%V"  # ISO week format
    dry_run: bool = False

    @classmethod
    def from_dict(cls, data: Dict) -> "TriageConfig":
        """Create config from dictionary (e.g., from .huskycat.yaml)."""
        triage_data = data.get("triage", data)
        return cls(
            enabled=triage_data.get("enabled", True),
            auto_label=triage_data.get("auto_label", True),
            auto_iteration=triage_data.get("auto_iteration", True),
            platforms=triage_data.get("platforms", ["gitlab", "github", "codeberg"]),
            path_labels=triage_data.get("path_labels", dict(DEFAULT_PATH_LABELS)),
            branch_prefix_labels=triage_data.get(
                "branch_prefix_labels", dict(BRANCH_PREFIX_LABELS)
            ),
            iteration_format=triage_data.get("iteration_format", "%Y-W%V"),
            dry_run=triage_data.get("dry_run", False),
        )


@dataclass
class TriageResult:
    """Result of a triage operation."""

    issue_ref: Optional[IssueRef] = None
    mr_ref: Optional[MRRef] = None
    labels_inferred: List[str] = field(default_factory=list)
    iteration: str = ""
    actions: List[TriageAction] = field(default_factory=list)
    dry_run: bool = False

    @property
    def success(self) -> bool:
        """Check if all actions succeeded."""
        if not self.actions:
            return True
        return all(a.success for a in self.actions)

    def summary(self) -> str:
        """Human-readable summary of triage results."""
        parts = []
        if self.issue_ref:
            parts.append(f"Issue: #{self.issue_ref.number}")
        if self.mr_ref:
            parts.append(f"MR: !{self.mr_ref.number}")
        if self.labels_inferred:
            parts.append(f"Labels: {', '.join(self.labels_inferred)}")
        if self.iteration:
            parts.append(f"Iteration: {self.iteration}")
        if self.dry_run:
            parts.append("[DRY RUN]")
        return " | ".join(parts) if parts else "No triage actions needed"


class TriageEngine:
    """Core engine for auto-triage of git commits.

    Detects issues/MRs from branch names, infers labels from
    file changes and branch prefixes, and sets iterations.
    """

    def __init__(
        self,
        config: Optional[TriageConfig] = None,
        repo_path: Optional[str] = None,
    ):
        self.config = config or TriageConfig()
        self.repo_path = repo_path
        self._platform: Optional[PlatformType] = None
        self._adapter: Optional[PlatformAdapter] = None
        self._project: str = ""

    @property
    def platform(self) -> PlatformType:
        if self._platform is None:
            self._platform = detect_platform(self.repo_path)
        return self._platform

    @property
    def adapter(self) -> Optional[PlatformAdapter]:
        if self._adapter is None:
            self._adapter = self._create_adapter()
        return self._adapter

    def _create_adapter(self) -> Optional[PlatformAdapter]:
        """Create the appropriate platform adapter."""
        self._project = get_remote_project(self.repo_path)
        platform = self.platform

        if platform == PlatformType.GITLAB:
            from .gitlab import GitLabAdapter

            return GitLabAdapter(self._project)
        elif platform == PlatformType.GITHUB:
            from .github import GitHubAdapter

            return GitHubAdapter(self._project)
        elif platform == PlatformType.CODEBERG:
            from .codeberg import CodebergAdapter

            return CodebergAdapter(self._project)

        return None

    def run_post_commit(self) -> TriageResult:
        """Run triage after a commit (post-commit hook).

        Detects issue/MR from branch, infers labels, sets iteration.
        """
        result = TriageResult(dry_run=self.config.dry_run)

        if not self.config.enabled:
            return result

        adapter = self.adapter
        if adapter is None:
            logger.debug("No platform adapter available")
            return result

        if not adapter.check_cli_available():
            logger.debug(f"CLI for {self.platform.value} not available")
            return result

        # Step 1: Get current branch
        branch = self._get_current_branch()
        if not branch:
            return result

        # Step 2: Detect issue from branch name
        issue_num = self._extract_issue_from_branch(branch)
        if issue_num:
            result.issue_ref = IssueRef(
                number=issue_num,
                platform=self.platform,
                project=self._project,
            )

        # Step 3: Find associated MR/PR
        mr_ref = adapter.find_mr_by_branch(branch)
        if mr_ref:
            result.mr_ref = mr_ref

        # Step 4: Infer labels
        if self.config.auto_label:
            labels = self._infer_labels(branch)
            result.labels_inferred = list(labels)

        # Step 5: Determine iteration
        if self.config.auto_iteration:
            result.iteration = self._get_current_iteration()

        # Step 6: Apply triage actions
        if not self.config.dry_run:
            self._apply_actions(result, adapter)

        return result

    def run_post_push(self) -> TriageResult:
        """Run triage after a push (pre-push hook, non-blocking).

        Similar to post_commit but focuses on MR/PR updates.
        """
        return self.run_post_commit()

    def _get_current_branch(self) -> str:
        """Get the current git branch name."""
        try:
            cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
            if self.repo_path:
                cmd = ["git", "-C", self.repo_path] + cmd[1:]
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=5
            )
            branch = result.stdout.strip()
            # Skip triage for main/dev/master branches
            if branch in ("main", "master", "dev", "HEAD"):
                return ""
            return branch
        except Exception:
            return ""

    def _extract_issue_from_branch(self, branch: str) -> Optional[int]:
        """Extract issue number from branch name."""
        for pattern in BRANCH_ISSUE_PATTERNS:
            match = pattern.search(branch)
            if match:
                val = match.group(1)
                # Skip Jira-style references (not numeric)
                if not val.isdigit():
                    continue
                return int(val)
        return None

    def _extract_issue_from_commit(self, message: str) -> Optional[int]:
        """Extract issue number from commit message."""
        for pattern in COMMIT_ISSUE_PATTERNS:
            match = pattern.search(message)
            if match:
                return int(match.group(1))
        return None

    def _infer_labels(self, branch: str) -> Set[str]:
        """Infer labels from branch prefix and changed files."""
        labels: Set[str] = set()

        # From branch prefix
        for prefix, label in self.config.branch_prefix_labels.items():
            if branch.startswith(prefix):
                labels.add(label)
                break

        # From changed files (last commit)
        changed_files = self._get_changed_files()
        for file_path in changed_files:
            for pattern, file_labels in self.config.path_labels.items():
                if self._match_glob(file_path, pattern):
                    labels.update(file_labels)

        return labels

    def _get_changed_files(self) -> List[str]:
        """Get files changed in the last commit."""
        try:
            cmd = ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"]
            if self.repo_path:
                cmd = ["git", "-C", self.repo_path] + cmd[1:]
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=10
            )
            if result.returncode == 0:
                return [f for f in result.stdout.strip().split("\n") if f]
            return []
        except Exception:
            return []

    def _get_current_iteration(self) -> str:
        """Get the current iteration/sprint name (ISO week format)."""
        now = datetime.datetime.now()
        return now.strftime(self.config.iteration_format)

    def _match_glob(self, filepath: str, pattern: str) -> bool:
        """Simple glob matching for file paths."""
        from fnmatch import fnmatch

        # Handle ** patterns
        if "**" in pattern:
            # Match against full path with ** as recursive wildcard
            parts = pattern.split("**")
            if len(parts) == 2:
                prefix, suffix = parts
                # Remove leading/trailing slashes from parts
                prefix = prefix.rstrip("/")
                suffix = suffix.lstrip("/")
                if prefix and not filepath.startswith(prefix):
                    return False
                if suffix:
                    return fnmatch(filepath.split("/")[-1], suffix) or fnmatch(
                        filepath, f"*{suffix}"
                    )
                return True
        return fnmatch(filepath, pattern)

    def _apply_actions(
        self, result: TriageResult, adapter: PlatformAdapter
    ) -> None:
        """Apply triage actions to the forge."""
        # Apply labels to MR if one exists
        if result.mr_ref and result.labels_inferred:
            action = adapter.add_labels(
                "mr", result.mr_ref.number, result.labels_inferred
            )
            result.actions.append(action)

        # Apply labels to issue if one exists
        if result.issue_ref and result.labels_inferred:
            action = adapter.add_labels(
                "issue", result.issue_ref.number, result.labels_inferred
            )
            result.actions.append(action)

        # Set iteration on issue
        if result.issue_ref and result.iteration:
            action = adapter.set_iteration(
                "issue", result.issue_ref.number, result.iteration
            )
            result.actions.append(action)

        # Set iteration/milestone on MR
        if result.mr_ref and result.iteration:
            action = adapter.set_iteration(
                "mr", result.mr_ref.number, result.iteration
            )
            result.actions.append(action)
