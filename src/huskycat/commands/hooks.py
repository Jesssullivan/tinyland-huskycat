"""
Git hooks setup command - configures git to use tracked hooks.

This command sets up git to use the project's tracked hooks in .githooks/
instead of the default .git/hooks/ directory.

The actual hook scripts are tracked in version control at:
    .githooks/
    ├── _/common.sh      # Shared utilities
    ├── pre-commit       # Staged file validation
    ├── pre-push         # Full codebase validation
    └── commit-msg       # Conventional commit format

IMPORTANT: Development in this repository requires UV venv to be active.
See .githooks/README.md for full documentation.
"""

import subprocess
from pathlib import Path
from typing import Any

from ..core.base import BaseCommand, CommandResult, CommandStatus  # noqa: TID252


class SetupHooksCommand(BaseCommand):
    """Configure git to use project-tracked hooks in .githooks/ directory."""

    @property
    def name(self) -> str:
        return "setup-hooks"

    @property
    def description(self) -> str:
        return "Configure git to use tracked hooks in .githooks/"

    def execute(self, **kwargs: Any) -> CommandResult:  # noqa: ARG002, ANN401
        """
        Set git core.hooksPath to .githooks directory.

        This enables the git-tracked hooks which use UV venv for tool execution.
        No binary fallback, no container fallback - UV venv is required.

        Args:
            **kwargs: Accepts but ignores additional arguments for API compatibility

        Returns:
            CommandResult with setup status
        """
        # Verify we're in a git repository
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],  # noqa: S607
                capture_output=True,
                text=True,
                check=True,
            )
            git_dir = Path(result.stdout.strip())
        except subprocess.CalledProcessError:
            return CommandResult(
                status=CommandStatus.FAILED,
                message="Not in a git repository",
                errors=["Current directory is not a git repository"],
            )

        # Verify .githooks directory exists
        hooks_dir = Path(".githooks")
        if not hooks_dir.exists():
            return CommandResult(
                status=CommandStatus.FAILED,
                message=".githooks directory not found",
                errors=[
                    ".githooks directory not found in repository root",
                    "This should be tracked in git - check if repo is complete",
                ],
            )

        # Check for required hook files
        required_hooks = ["pre-commit", "pre-push", "commit-msg"]
        missing_hooks = [h for h in required_hooks if not (hooks_dir / h).exists()]
        if missing_hooks:
            return CommandResult(
                status=CommandStatus.WARNING,
                message="Some hook files are missing",
                warnings=[f"Missing hook: .githooks/{h}" for h in missing_hooks],
            )

        # Check for common.sh utility
        common_sh = hooks_dir / "_" / "common.sh"
        if not common_sh.exists():
            return CommandResult(
                status=CommandStatus.FAILED,
                message="Shared utilities not found",
                errors=[
                    ".githooks/_/common.sh not found",
                    "This file is required for hooks to function",
                ],
            )

        # Set core.hooksPath to use tracked hooks
        try:
            subprocess.run(
                ["git", "config", "core.hooksPath", ".githooks"],  # noqa: S607
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            return CommandResult(
                status=CommandStatus.FAILED,
                message=f"Failed to configure git: {e}",
                errors=[str(e)],
            )

        # Verify hooks are executable
        non_executable = []
        for hook in required_hooks:
            hook_path = hooks_dir / hook
            if hook_path.exists() and not hook_path.stat().st_mode & 0o111:
                non_executable.append(hook)

        warnings = []
        if non_executable:
            warnings.append(
                f"Some hooks may not be executable: {', '.join(non_executable)}",
            )
            warnings.append("Run: chmod +x .githooks/*")

        # Check UV availability
        try:
            subprocess.run(
                ["uv", "--version"],  # noqa: S607
                check=True,
                capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            warnings.append("UV not found - required for hook execution")
            warnings.append("Install: curl -LsSf https://astral.sh/uv/install.sh | sh")
            warnings.append("Then run: uv sync --dev")

        # Check venv exists
        if not Path(".venv").exists():
            warnings.append("Virtual environment not found")
            warnings.append("Run: uv sync --dev")

        # Build available hooks list
        available_hooks = [
            f.name
            for f in hooks_dir.iterdir()
            if f.is_file() and not f.name.startswith(".") and f.name != "README.md"
        ]

        status = CommandStatus.WARNING if warnings else CommandStatus.SUCCESS

        return CommandResult(
            status=status,
            message="Git hooks configured to use .githooks/",
            warnings=warnings if warnings else None,
            data={
                "hooks_path": ".githooks",
                "git_dir": str(git_dir),
                "hooks_available": available_hooks,
                "requirements": [
                    "UV package manager must be installed",
                    "Virtual environment must be active (uv sync --dev)",
                    "See .githooks/README.md for full documentation",
                ],
            },
        )
