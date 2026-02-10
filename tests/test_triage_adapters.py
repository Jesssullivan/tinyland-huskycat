"""Tests for triage platform adapters (GitLab, GitHub, Codeberg)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from huskycat.core.triage.platform import (
    IssueRef,
    MRRef,
    PlatformAdapter,
    PlatformType,
    TriageAction,
    detect_platform,
    get_remote_project,
)
from huskycat.core.triage.gitlab import GitLabAdapter
from huskycat.core.triage.github import GitHubAdapter
from huskycat.core.triage.codeberg import CodebergAdapter


class TestPlatformDetection:
    """Test forge platform detection from git remotes."""

    @patch("subprocess.run")
    def test_detect_gitlab(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="origin\tgit@gitlab.com:tinyland/ai/huskycat.git (fetch)\n",
        )
        assert detect_platform() == PlatformType.GITLAB

    @patch("subprocess.run")
    def test_detect_github(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="origin\tgit@github.com:user/repo.git (fetch)\n",
        )
        assert detect_platform() == PlatformType.GITHUB

    @patch("subprocess.run")
    def test_detect_codeberg(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="origin\thttps://codeberg.org/user/repo.git (fetch)\n",
        )
        assert detect_platform() == PlatformType.CODEBERG

    @patch("subprocess.run")
    def test_detect_unknown(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="origin\thttps://bitbucket.org/user/repo.git (fetch)\n",
        )
        assert detect_platform() == PlatformType.UNKNOWN

    @patch("subprocess.run")
    def test_detect_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert detect_platform() == PlatformType.UNKNOWN

    @patch("subprocess.run", side_effect=Exception("boom"))
    def test_detect_exception(self, mock_run):
        assert detect_platform() == PlatformType.UNKNOWN

    @patch("subprocess.run")
    def test_detect_with_repo_path(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="origin\tgit@gitlab.com:group/project.git (fetch)\n",
        )
        result = detect_platform("/tmp/repo")
        assert result == PlatformType.GITLAB
        # Verify -C flag was added
        call_args = mock_run.call_args[0][0]
        assert "-C" in call_args
        assert "/tmp/repo" in call_args


class TestGetRemoteProject:
    """Test owner/repo extraction from git remote URL."""

    @patch("subprocess.run")
    def test_ssh_url(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="git@gitlab.com:tinyland/ai/huskycat.git\n",
        )
        assert get_remote_project() == "tinyland/ai/huskycat"

    @patch("subprocess.run")
    def test_https_url(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/user/repo.git\n",
        )
        assert get_remote_project() == "user/repo"

    @patch("subprocess.run")
    def test_https_no_git_suffix(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/user/repo\n",
        )
        assert get_remote_project() == "user/repo"

    @patch("subprocess.run")
    def test_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert get_remote_project() == ""

    @patch("subprocess.run", side_effect=Exception("timeout"))
    def test_exception(self, mock_run):
        assert get_remote_project() == ""


class TestPlatformTypeEnum:
    """Test PlatformType enum."""

    def test_values(self):
        assert PlatformType.GITLAB.value == "gitlab"
        assert PlatformType.GITHUB.value == "github"
        assert PlatformType.CODEBERG.value == "codeberg"
        assert PlatformType.UNKNOWN.value == "unknown"


class TestTriageActionDataclass:
    """Test TriageAction dataclass."""

    def test_default_values(self):
        action = TriageAction("add_label", "issue", 1)
        assert action.success is False
        assert action.message == ""
        assert action.params == {}

    def test_with_params(self):
        action = TriageAction(
            "add_label", "issue", 42,
            params={"labels": ["bug"]},
            success=True,
            message="Done",
        )
        assert action.params["labels"] == ["bug"]
        assert action.success is True


class TestIssueRefDataclass:
    """Test IssueRef dataclass."""

    def test_basic(self):
        ref = IssueRef(number=42, platform=PlatformType.GITLAB)
        assert ref.number == 42
        assert ref.project == ""

    def test_with_project(self):
        ref = IssueRef(number=1, platform=PlatformType.GITHUB, project="user/repo")
        assert ref.project == "user/repo"


class TestMRRefDataclass:
    """Test MRRef dataclass."""

    def test_basic(self):
        ref = MRRef(number=5, platform=PlatformType.GITLAB)
        assert ref.source_branch == ""

    def test_with_branch(self):
        ref = MRRef(
            number=5,
            platform=PlatformType.GITLAB,
            project="group/proj",
            source_branch="feat/login",
        )
        assert ref.source_branch == "feat/login"


class TestGitLabAdapter:
    """Test GitLab adapter using glab CLI."""

    def test_platform_type(self):
        adapter = GitLabAdapter("group/project")
        assert adapter.platform_type == PlatformType.GITLAB

    @patch("subprocess.run")
    def test_check_cli_available_true(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        adapter = GitLabAdapter("group/project")
        assert adapter.check_cli_available() is True

    @patch("subprocess.run")
    def test_check_cli_available_false(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        adapter = GitLabAdapter("group/project")
        assert adapter.check_cli_available() is False

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_check_cli_not_installed(self, mock_run):
        adapter = GitLabAdapter("group/project")
        assert adapter.check_cli_available() is False

    @patch("subprocess.run")
    def test_add_labels_to_mr(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        adapter = GitLabAdapter("group/project")
        action = adapter.add_labels("mr", 5, ["bug", "python"])
        assert action.success is True
        assert "bug,python" in action.message or "bug" in action.message

    @patch("subprocess.run")
    def test_add_labels_to_issue(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        adapter = GitLabAdapter("group/project")
        action = adapter.add_labels("issue", 42, ["feature"])
        assert action.success is True

    def test_add_labels_empty(self):
        adapter = GitLabAdapter("group/project")
        action = adapter.add_labels("issue", 1, [])
        assert action.success is True
        assert "No labels" in action.message

    @patch("subprocess.run")
    def test_add_labels_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="Not found")
        adapter = GitLabAdapter("group/project")
        action = adapter.add_labels("issue", 999, ["bug"])
        assert action.success is False
        assert "Failed" in action.message

    @patch("subprocess.run")
    def test_find_mr_by_branch_found(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([{"iid": 10, "source_branch": "feat/login"}]),
        )
        adapter = GitLabAdapter("group/project")
        mr = adapter.find_mr_by_branch("feat/login")
        assert mr is not None
        assert mr.number == 10
        assert mr.source_branch == "feat/login"

    @patch("subprocess.run")
    def test_find_mr_by_branch_not_found(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="[]")
        adapter = GitLabAdapter("group/project")
        mr = adapter.find_mr_by_branch("no-such-branch")
        assert mr is None

    @patch("subprocess.run")
    def test_find_mr_by_branch_empty_output(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        adapter = GitLabAdapter("group/project")
        mr = adapter.find_mr_by_branch("feat/test")
        assert mr is None

    @patch("subprocess.run")
    def test_set_iteration_mr_uses_milestone(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        adapter = GitLabAdapter("group/project")
        action = adapter.set_iteration("mr", 5, "2026-W06")
        assert action.success is True
        assert "milestone" in action.message.lower()


class TestGitHubAdapter:
    """Test GitHub adapter using gh CLI."""

    def test_platform_type(self):
        adapter = GitHubAdapter("user/repo")
        assert adapter.platform_type == PlatformType.GITHUB

    @patch("subprocess.run")
    def test_check_cli_available(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        adapter = GitHubAdapter("user/repo")
        assert adapter.check_cli_available() is True

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_check_cli_not_installed(self, mock_run):
        adapter = GitHubAdapter("user/repo")
        assert adapter.check_cli_available() is False

    @patch("subprocess.run")
    def test_add_labels_to_pr(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        adapter = GitHubAdapter("user/repo")
        action = adapter.add_labels("pr", 10, ["bug"])
        assert action.success is True

    @patch("subprocess.run")
    def test_add_labels_to_issue(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        adapter = GitHubAdapter("user/repo")
        action = adapter.add_labels("issue", 5, ["feature"])
        assert action.success is True

    def test_add_labels_empty(self):
        adapter = GitHubAdapter("user/repo")
        action = adapter.add_labels("issue", 1, [])
        assert action.success is True

    @patch("subprocess.run")
    def test_set_iteration_uses_milestone(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        adapter = GitHubAdapter("user/repo")
        action = adapter.set_iteration("issue", 1, "2026-W06")
        assert action.success is True
        assert "milestone" in action.message.lower()

    @patch("subprocess.run")
    def test_find_pr_by_branch_found(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([{"number": 42, "headRefName": "feat/login"}]),
        )
        adapter = GitHubAdapter("user/repo")
        mr = adapter.find_mr_by_branch("feat/login")
        assert mr is not None
        assert mr.number == 42

    @patch("subprocess.run")
    def test_find_pr_by_branch_not_found(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="[]")
        adapter = GitHubAdapter("user/repo")
        assert adapter.find_mr_by_branch("none") is None


class TestCodebergAdapter:
    """Test Codeberg/Gitea adapter using REST API."""

    def test_platform_type(self):
        adapter = CodebergAdapter("user/repo")
        assert adapter.platform_type == PlatformType.CODEBERG

    def test_check_cli_no_token(self):
        with patch.dict("os.environ", {}, clear=True):
            adapter = CodebergAdapter("user/repo")
            adapter._token = ""
            assert adapter.check_cli_available() is False

    def test_check_cli_with_token(self):
        adapter = CodebergAdapter("user/repo")
        adapter._token = "test-token-123"
        assert adapter.check_cli_available() is True

    def test_add_labels_empty(self):
        adapter = CodebergAdapter("user/repo")
        action = adapter.add_labels("issue", 1, [])
        assert action.success is True

    @patch.object(CodebergAdapter, "_resolve_label_ids", return_value=[])
    def test_add_labels_unresolved(self, mock_resolve):
        adapter = CodebergAdapter("user/repo")
        adapter._token = "token"
        action = adapter.add_labels("issue", 1, ["nonexistent"])
        assert action.success is False
        assert "resolve" in action.message.lower()

    @patch.object(CodebergAdapter, "_resolve_label_ids", return_value=[1, 2])
    @patch.object(CodebergAdapter, "_api_request", return_value=[{"id": 1}])
    def test_add_labels_success(self, mock_api, mock_resolve):
        adapter = CodebergAdapter("user/repo")
        adapter._token = "token"
        action = adapter.add_labels("issue", 5, ["bug", "feature"])
        assert action.success is True

    @patch.object(CodebergAdapter, "_find_milestone_id", return_value=None)
    def test_set_iteration_no_milestone(self, mock_find):
        adapter = CodebergAdapter("user/repo")
        adapter._token = "token"
        action = adapter.set_iteration("issue", 1, "2026-W06")
        assert action.success is False
        assert "not found" in action.message.lower()

    @patch.object(CodebergAdapter, "_find_milestone_id", return_value=42)
    @patch.object(CodebergAdapter, "_api_request", return_value={"id": 1})
    def test_set_iteration_success(self, mock_api, mock_find):
        adapter = CodebergAdapter("user/repo")
        adapter._token = "token"
        action = adapter.set_iteration("issue", 1, "2026-W06")
        assert action.success is True

    @patch.object(CodebergAdapter, "_api_request")
    def test_find_mr_by_branch_found(self, mock_api):
        mock_api.return_value = [
            {"number": 7, "head": {"ref": "feat/login"}},
            {"number": 8, "head": {"ref": "other-branch"}},
        ]
        adapter = CodebergAdapter("user/repo")
        adapter._token = "token"
        mr = adapter.find_mr_by_branch("feat/login")
        assert mr is not None
        assert mr.number == 7

    @patch.object(CodebergAdapter, "_api_request", return_value=[])
    def test_find_mr_by_branch_not_found(self, mock_api):
        adapter = CodebergAdapter("user/repo")
        adapter._token = "token"
        assert adapter.find_mr_by_branch("none") is None

    @patch.object(CodebergAdapter, "_api_request", return_value=None)
    def test_find_mr_by_branch_api_error(self, mock_api):
        adapter = CodebergAdapter("user/repo")
        adapter._token = "token"
        assert adapter.find_mr_by_branch("feat/test") is None

    @patch.object(CodebergAdapter, "_api_request")
    def test_resolve_label_ids(self, mock_api):
        mock_api.return_value = [
            {"name": "bug", "id": 1},
            {"name": "feature", "id": 2},
            {"name": "docs", "id": 3},
        ]
        adapter = CodebergAdapter("user/repo")
        adapter._token = "token"
        ids = adapter._resolve_label_ids(["bug", "feature"])
        assert ids == [1, 2]

    @patch.object(CodebergAdapter, "_api_request", return_value=None)
    def test_resolve_label_ids_api_error(self, mock_api):
        adapter = CodebergAdapter("user/repo")
        adapter._token = "token"
        assert adapter._resolve_label_ids(["bug"]) == []

    @patch.object(CodebergAdapter, "_api_request")
    def test_find_milestone_id(self, mock_api):
        mock_api.return_value = [
            {"title": "2026-W05", "id": 10},
            {"title": "2026-W06", "id": 11},
        ]
        adapter = CodebergAdapter("user/repo")
        adapter._token = "token"
        assert adapter._find_milestone_id("2026-W06") == 11

    @patch.object(CodebergAdapter, "_api_request")
    def test_find_milestone_id_not_found(self, mock_api):
        mock_api.return_value = [{"title": "other", "id": 1}]
        adapter = CodebergAdapter("user/repo")
        adapter._token = "token"
        assert adapter._find_milestone_id("2026-W06") is None
