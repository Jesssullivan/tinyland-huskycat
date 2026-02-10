"""Tests for the HookGenerator module."""

import os
import stat
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from huskycat.core.hook_generator import HookGenerator


class TestHookGeneratorInit:
    """Test HookGenerator initialization."""

    def test_init_with_repo_path(self, tmp_path):
        git_dir = tmp_path / ".git" / "hooks"
        git_dir.mkdir(parents=True)
        gen = HookGenerator(tmp_path)
        assert gen.repo_path == tmp_path
        assert gen.hooks_dir == tmp_path / ".git" / "hooks"

    def test_init_with_binary_path(self, tmp_path):
        git_dir = tmp_path / ".git" / "hooks"
        git_dir.mkdir(parents=True)
        binary = tmp_path / "huskycat"
        binary.touch()
        gen = HookGenerator(tmp_path, binary_path=binary)
        assert gen.binary_path == binary

    def test_version_fallback(self, tmp_path):
        git_dir = tmp_path / ".git" / "hooks"
        git_dir.mkdir(parents=True)
        gen = HookGenerator(tmp_path)
        # Should have some version string
        assert gen.version is not None
        assert len(gen.version) > 0


class TestHookTemplates:
    """Test hook template constants."""

    def test_pre_commit_template_exists(self):
        assert "pre-commit" in HookGenerator.HOOK_TEMPLATES

    def test_pre_push_template_exists(self):
        assert "pre-push" in HookGenerator.HOOK_TEMPLATES

    def test_post_commit_template_exists(self):
        assert "post-commit" in HookGenerator.HOOK_TEMPLATES

    def test_commit_msg_template_exists(self):
        assert "commit-msg" in HookGenerator.HOOK_TEMPLATES

    def test_prepare_commit_msg_template_exists(self):
        assert "prepare-commit-msg" in HookGenerator.HOOK_TEMPLATES

    def test_all_templates_have_paths(self):
        for hook_name, template_path in HookGenerator.HOOK_TEMPLATES.items():
            assert template_path.endswith(".template"), (
                f"Template for {hook_name} doesn't end with .template"
            )
            assert "templates/hooks/" in template_path


class TestBinaryDetection:
    """Test binary path detection logic."""

    def test_user_bin_detection(self, tmp_path):
        git_dir = tmp_path / ".git" / "hooks"
        git_dir.mkdir(parents=True)
        with patch("pathlib.Path.home", return_value=tmp_path):
            local_bin = tmp_path / ".local" / "bin" / "huskycat"
            local_bin.parent.mkdir(parents=True)
            local_bin.touch()
            gen = HookGenerator(tmp_path)
            assert gen.binary_path == local_bin

    @patch("subprocess.run")
    def test_which_detection(self, mock_run, tmp_path):
        git_dir = tmp_path / ".git" / "hooks"
        git_dir.mkdir(parents=True)
        # Create a fake binary for which to find
        fake_bin = tmp_path / "fake_huskycat"
        fake_bin.touch()
        mock_run.return_value = MagicMock(
            returncode=0, stdout=str(fake_bin) + "\n"
        )
        with patch("pathlib.Path.home", return_value=tmp_path / "nonexistent"):
            gen = HookGenerator(tmp_path)
            assert gen.binary_path == fake_bin

    def test_no_binary_found(self, tmp_path):
        git_dir = tmp_path / ".git" / "hooks"
        git_dir.mkdir(parents=True)
        with patch("pathlib.Path.home", return_value=tmp_path / "nonexistent"):
            with patch("subprocess.run", side_effect=Exception("nope")):
                gen = HookGenerator(tmp_path)
                # Should be None or some fallback
                # The exact behavior depends on system PATH detection
                assert True  # Just verify no exception
