"""GitLab platform adapter for auto-triage."""

import json
import logging
import subprocess
from typing import List, Optional

from .platform import MRRef, PlatformAdapter, PlatformType, TriageAction

logger = logging.getLogger(__name__)


class GitLabAdapter(PlatformAdapter):
    """GitLab forge adapter using glab CLI."""

    @property
    def platform_type(self) -> PlatformType:
        return PlatformType.GITLAB

    def check_cli_available(self) -> bool:
        """Check if glab CLI is available and authenticated."""
        try:
            result = subprocess.run(
                ["glab", "auth", "status"],
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
        """Add labels to a GitLab issue or MR."""
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

        label_str = ",".join(labels)

        try:
            if target_type == "mr":
                cmd = [
                    "glab",
                    "mr",
                    "update",
                    str(number),
                    "--add-label",
                    label_str,
                ]
            else:
                cmd = [
                    "glab",
                    "issue",
                    "update",
                    str(number),
                    "--add-label",
                    label_str,
                ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=30
            )

            if result.returncode == 0:
                action.success = True
                action.message = f"Added labels [{label_str}] to {target_type} !{number}"
            else:
                action.message = f"Failed to add labels: {result.stderr.strip()}"
        except Exception as e:
            action.message = f"Error adding labels: {e}"

        return action

    def set_iteration(
        self, target_type: str, number: int, iteration: str
    ) -> TriageAction:
        """Set iteration on a GitLab issue.

        Note: GitLab iterations are issue-only. For MRs, use milestones.
        """
        action = TriageAction(
            action_type="set_iteration",
            target_type=target_type,
            target_number=number,
            params={"iteration": iteration},
        )

        if target_type == "mr":
            # MRs don't support iterations - use milestone instead
            return self._set_milestone(number, iteration, action)

        # For issues, try to find and set the current iteration via GraphQL
        try:
            iteration_id = self._find_current_iteration()
            if not iteration_id:
                action.message = (
                    "No current iteration found (requires GitLab Premium)"
                )
                return action

            # Use GraphQL to set iteration on issue
            query = """
            mutation {
              issueSetIteration(input: {
                iid: "%s",
                projectPath: "%s",
                iterationId: "%s"
              }) {
                issue { iid }
                errors
              }
            }
            """ % (
                number,
                self.project,
                iteration_id,
            )

            result = subprocess.run(
                ["glab", "api", "graphql", "-f", f"query={query}"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )

            if result.returncode == 0:
                action.success = True
                action.message = f"Set iteration on issue #{number}"
            else:
                action.message = f"Failed to set iteration: {result.stderr.strip()}"
        except Exception as e:
            action.message = f"Error setting iteration: {e}"

        return action

    def _set_milestone(
        self, number: int, milestone_title: str, action: TriageAction
    ) -> TriageAction:
        """Set milestone on an MR (fallback when iterations unavailable)."""
        try:
            cmd = [
                "glab",
                "mr",
                "update",
                str(number),
                "--milestone",
                milestone_title,
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=30
            )

            if result.returncode == 0:
                action.success = True
                action.message = f"Set milestone '{milestone_title}' on MR !{number}"
            else:
                action.message = (
                    f"Failed to set milestone: {result.stderr.strip()}"
                )
        except Exception as e:
            action.message = f"Error setting milestone: {e}"

        return action

    def _find_current_iteration(self) -> Optional[str]:
        """Find the current iteration GID via GitLab API."""
        try:
            # Extract group from project path (e.g., 'group/project' -> 'group')
            parts = self.project.split("/")
            if len(parts) < 2:
                return None

            group = "/".join(parts[:-1])
            group_encoded = group.replace("/", "%2F")

            result = subprocess.run(
                [
                    "glab",
                    "api",
                    f"groups/{group_encoded}/iterations?state=current",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data and isinstance(data, list) and len(data) > 0:
                    return f"gid://gitlab/Iteration/{data[0]['id']}"

            return None
        except Exception as e:
            logger.debug(f"Failed to find current iteration: {e}")
            return None

    def find_mr_by_branch(self, branch: str) -> Optional[MRRef]:
        """Find an open MR for the given source branch."""
        try:
            result = subprocess.run(
                [
                    "glab",
                    "mr",
                    "list",
                    "--source-branch",
                    branch,
                    "--state",
                    "opened",
                    "--json",
                    "iid,source_branch",
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
                        number=data[0]["iid"],
                        platform=PlatformType.GITLAB,
                        project=self.project,
                        source_branch=branch,
                    )

            return None
        except Exception as e:
            logger.debug(f"Failed to find MR by branch: {e}")
            return None
