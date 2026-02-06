"""Codeberg (Gitea) platform adapter for auto-triage."""

import json
import logging
import os
import subprocess
import urllib.request
import urllib.error
from typing import Dict, List, Optional

from .platform import MRRef, PlatformAdapter, PlatformType, TriageAction

logger = logging.getLogger(__name__)

# Codeberg API base
CODEBERG_API = "https://codeberg.org/api/v1"


class CodebergAdapter(PlatformAdapter):
    """Codeberg/Gitea forge adapter using REST API directly.

    Codeberg uses the Gitea API. There is no official CLI tool,
    so we use urllib for API calls.
    """

    def __init__(self, project: str = ""):
        super().__init__(project)
        self._token = os.environ.get("CODEBERG_TOKEN", "")
        self._api_base = os.environ.get("CODEBERG_API_URL", CODEBERG_API)

    @property
    def platform_type(self) -> PlatformType:
        return PlatformType.CODEBERG

    def check_cli_available(self) -> bool:
        """Check if Codeberg API token is available."""
        return bool(self._token)

    def _api_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """Make an API request to Codeberg/Gitea.

        Args:
            method: HTTP method
            path: API path (e.g., '/repos/owner/repo/issues/1/labels')
            data: JSON body for POST/PUT/PATCH

        Returns:
            Response JSON or None on error
        """
        url = f"{self._api_base}{path}"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._token:
            headers["Authorization"] = f"token {self._token}"

        body = json.dumps(data).encode("utf-8") if data else None

        try:
            req = urllib.request.Request(
                url, data=body, headers=headers, method=method
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            logger.debug(f"Codeberg API error {e.code}: {e.reason}")
            return None
        except Exception as e:
            logger.debug(f"Codeberg API request failed: {e}")
            return None

    def add_labels(
        self, target_type: str, number: int, labels: List[str]
    ) -> TriageAction:
        """Add labels to a Codeberg issue or PR.

        In Gitea, PRs and issues share the same label API endpoint.
        """
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

        # First, get label IDs by name
        label_ids = self._resolve_label_ids(labels)
        if not label_ids:
            action.message = "Could not resolve label names to IDs"
            return action

        # Gitea uses issue number for both issues and PRs
        path = f"/repos/{self.project}/issues/{number}/labels"
        result = self._api_request("POST", path, {"labels": label_ids})

        if result is not None:
            action.success = True
            label_str = ", ".join(labels)
            action.message = (
                f"Added labels [{label_str}] to {target_type} #{number}"
            )
        else:
            action.message = f"Failed to add labels to {target_type} #{number}"

        return action

    def set_iteration(
        self, target_type: str, number: int, iteration: str
    ) -> TriageAction:
        """Set milestone on a Codeberg issue/PR.

        Codeberg/Gitea doesn't have iterations natively - use milestones.
        """
        action = TriageAction(
            action_type="set_iteration",
            target_type=target_type,
            target_number=number,
            params={"iteration": iteration},
        )

        # Find milestone by title
        milestone_id = self._find_milestone_id(iteration)
        if milestone_id is None:
            action.message = f"Milestone '{iteration}' not found"
            return action

        # Set milestone on issue/PR
        path = f"/repos/{self.project}/issues/{number}"
        result = self._api_request("PATCH", path, {"milestone": milestone_id})

        if result is not None:
            action.success = True
            action.message = (
                f"Set milestone '{iteration}' on {target_type} #{number}"
            )
        else:
            action.message = f"Failed to set milestone on {target_type} #{number}"

        return action

    def find_mr_by_branch(self, branch: str) -> Optional[MRRef]:
        """Find an open PR for the given head branch."""
        path = f"/repos/{self.project}/pulls?state=open"
        result = self._api_request("GET", path)

        if result and isinstance(result, list):
            for pr in result:
                if pr.get("head", {}).get("ref") == branch:
                    return MRRef(
                        number=pr["number"],
                        platform=PlatformType.CODEBERG,
                        project=self.project,
                        source_branch=branch,
                    )

        return None

    def _resolve_label_ids(self, label_names: List[str]) -> List[int]:
        """Resolve label names to Gitea label IDs."""
        path = f"/repos/{self.project}/labels"
        result = self._api_request("GET", path)

        if not result or not isinstance(result, list):
            return []

        name_to_id = {label["name"]: label["id"] for label in result}
        return [name_to_id[name] for name in label_names if name in name_to_id]

    def _find_milestone_id(self, title: str) -> Optional[int]:
        """Find milestone ID by title."""
        path = f"/repos/{self.project}/milestones?state=open"
        result = self._api_request("GET", path)

        if result and isinstance(result, list):
            for milestone in result:
                if milestone.get("title") == title:
                    return milestone["id"]

        return None
