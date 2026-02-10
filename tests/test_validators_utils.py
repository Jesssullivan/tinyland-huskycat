"""Tests for validators._utils module."""

from unittest.mock import patch, MagicMock

import pytest

from huskycat.validators._utils import (
    is_gpl_tool,
    is_running_in_container,
)


class TestIsGplTool:
    """Test GPL tool detection."""

    def test_shellcheck_is_gpl(self):
        assert is_gpl_tool("shellcheck") is True

    def test_hadolint_is_gpl(self):
        assert is_gpl_tool("hadolint") is True

    def test_yamllint_is_gpl(self):
        assert is_gpl_tool("yamllint") is True

    def test_ruff_is_not_gpl(self):
        assert is_gpl_tool("ruff") is False

    def test_mypy_is_not_gpl(self):
        assert is_gpl_tool("mypy") is False

    def test_bandit_is_not_gpl(self):
        assert is_gpl_tool("bandit") is False

    def test_unknown_tool(self):
        assert is_gpl_tool("nonexistent-tool") is False


class TestIsRunningInContainer:
    """Test container runtime detection."""

    @patch("os.path.exists", return_value=False)
    @patch.dict("os.environ", {}, clear=True)
    def test_not_in_container(self, mock_exists):
        assert is_running_in_container() is False

    @patch("os.path.exists", side_effect=lambda p: p == "/.dockerenv")
    @patch.dict("os.environ", {}, clear=True)
    def test_docker(self, mock_exists):
        assert is_running_in_container() is True

    @patch("os.path.exists", return_value=False)
    @patch.dict("os.environ", {"container": "podman"}, clear=False)
    def test_podman_env(self, mock_exists):
        assert is_running_in_container() is True

    @patch("os.path.exists", side_effect=lambda p: p == "/run/.containerenv")
    @patch.dict("os.environ", {}, clear=True)
    def test_containerenv(self, mock_exists):
        assert is_running_in_container() is True
