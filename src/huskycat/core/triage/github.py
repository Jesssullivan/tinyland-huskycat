"""GitHub platform adapter for auto-triage."""

import json
import logging
import subprocess
from typing import List, Optional

from .platform import MRRef, PlatformAdapter, PlatformType, TriageAction

logger = logging.getLogger(__name__)


class GitHubAdapter(PlatformAdapter):
    """GitHub forge adapter using gh CLI."""

    @property
    def platform_type(self) -> PlatformType:
        return PlatformType.GITHUB

    def check_cli_available(self) -> bool:
        """Check if gh CLI is available and authenticated."""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def add_labels(
        self, target_type: str, number: int, labels: List[str]
    ) -> TriageAction:
        """Add labels to a GitHub issue or PR."""
        action = TriageAction(
            action_type="add_label",
            target_type=target_type,
            target_number=number,
            params={"labels": labels},
        )

        if not labels:
            action.success = True
            action.message = "No labels to add"
            return action

        try:
            # gh issue/pr edit works for both
            cmd_type = "pr" if target_type in ("mr", "pr") else "issue"
            cmd = ["gh", cmd_type, "edit", str(number)]
            for label in labels:
                cmd.extend(["--add-label", label])

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=30
            )

            if result.returncode == 0:
                action.success = True
                label_str = ", ".join(labels)
                action.message = (
                    f"Added labels [{label_str}] to {cmd_type} #{number}"
                )
            else:
                action.message = f"Failed to add labels: {result.stderr.strip()}"
        except Exception as e:
            action.message = f"Error adding labels: {e}"

        return action

    def set_iteration(
        self, target_type: str, number: int, iteration: str
    ) -> TriageAction:
        """Set iteration on a GitHub Projects v2 item.

        Note: GitHub iterations require Projects v2 GraphQL API
        and project:read + project:write token scopes.
        Falls back to milestone assignment.
        """
        action = TriageAction(
            action_type="set_iteration",
            target_type=target_type,
            target_number=number,
            params={"iteration": iteration},
        )

        # Try milestone first (simpler, always works)
        try:
            cmd_type = "pr" if target_type in ("mr", "pr") else "issue"
            cmd = [
                "gh",
                cmd_type,
                "edit",
                str(number),
                "--milestone",
                iteration,
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=30
            )

            if result.returncode == 0:
                action.success = True
                action.message = (
                    f"Set milestone '{iteration}' on {cmd_type} #{number}"
                )
            else:
                action.message = (
                    f"Failed to set milestone: {result.stderr.strip()}"
                )
        except Exception as e:
            action.message = f"Error setting iteration: {e}"

        return action

    def find_mr_by_branch(self, branch: str) -> Optional[MRRef]:
        """Find an open PR for the given head branch."""
        try:
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--head",
                    branch,
                    "--state",
                    "open",
                    "--json",
                    "number,headRefName",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )

            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                if data and len(data) > 0:
                    return MRRef(
                        number=data[0]["number"],
                        platform=PlatformType.GITHUB,
                        project=self.project,
                        source_branch=branch,
                    )

            return None
        except Exception as e:
            logger.debug(f"Failed to find PR by branch: {e}")
            return None
