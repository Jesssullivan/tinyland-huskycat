"""E2E tests for HuskyCat bootstrap on GitOps repositories."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pytest

from .fixtures.repo_factory import TestRepoFactory


class TestBootstrapGitOps:
    """E2E tests for HuskyCat bootstrap on GitOps repositories."""

    @pytest.fixture
    def huskycat_executable(self) -> Path:
        """
        Get path to HuskyCat executable.

        This tries multiple locations:
        1. Binary in ~/.local/bin/huskycat
        2. UV run command (development mode)
        """
        # Try binary first
        binary_path = Path.home() / ".local" / "bin" / "huskycat"
        if binary_path.exists() and binary_path.is_file():
            return binary_path

        # Fall back to UV run (development mode)
        # Return a special marker that we'll handle in _run_huskycat
        return Path("UV_RUN_MODE")

    def _run_huskycat(
        self,
        huskycat_exec: Path,
        args: list[str],
        cwd: Path,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Run HuskyCat command, handling both binary and UV modes.

        Args:
            huskycat_exec: Path to executable or UV_RUN_MODE marker
            args: Command arguments
            cwd: Working directory
            check: Whether to check return code

        Returns:
            CompletedProcess result
        """
        if huskycat_exec.name == "UV_RUN_MODE":
            # UV development mode
            project_root = Path(__file__).parent.parent.parent
            cmd = [
                "uv",
                "run",
                "python",
                "-m",
                "huskycat",
            ] + args
            # Copy existing environment and update with our custom variables
            env = os.environ.copy()
            env["PYTHONPATH"] = str(project_root / "src")
            return subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=check,
                env=env,
            )
        # Binary mode
        cmd = [str(huskycat_exec)] + args
        return subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
        )

    def test_bootstrap_full_gitops_repo(
        self,
        huskycat_executable: Path,
        tmp_path: Path,
    ) -> None:
        """Test bootstrap on repository with all GitOps features."""
        # Create test repo with all features
        repo = TestRepoFactory.create_gitops_repo(
            features=["gitlab_ci", "helm", "k8s", "terraform", "ansible"],
            temp_dir=tmp_path,
        )

        # Run bootstrap
        result = self._run_huskycat(
            huskycat_executable,
            ["bootstrap", "--force"],
            repo,
            check=False,
        )

        # Assert success
        assert result.returncode == 0, (
            f"Bootstrap failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # Verify output mentions GitOps repository
        assert (
            "GitOps" in result.stdout or "gitops" in result.stdout.lower()
        ), f"Output should mention GitOps: {result.stdout}"

        # Verify hooks installed
        hooks_dir = repo / ".git" / "hooks"
        assert (hooks_dir / "pre-commit").exists(), "pre-commit hook not installed"
        assert (hooks_dir / "pre-push").exists(), "pre-push hook not installed"
        assert (hooks_dir / "commit-msg").exists(), "commit-msg hook not installed"

        # Verify hooks are executable
        for hook in ["pre-commit", "pre-push", "commit-msg"]:
            hook_path = hooks_dir / hook
            assert hook_path.stat().st_mode & 0o111, f"{hook} not executable"

        # Verify detected features are mentioned in output
        output_lower = result.stdout.lower()
        assert "gitlab ci" in output_lower or "gitlab-ci" in output_lower
        assert "helm" in output_lower
        assert "kubernetes" in output_lower or "k8s" in output_lower

        # Cleanup
        TestRepoFactory.cleanup_repo(repo)

    def test_bootstrap_helm_only_repo(
        self,
        huskycat_executable: Path,
        tmp_path: Path,
    ) -> None:
        """Test bootstrap on Helm-only repository."""
        # Create test repo with only Helm
        repo = TestRepoFactory.create_gitops_repo(
            features=["helm"],
            temp_dir=tmp_path,
        )

        # Run bootstrap
        result = self._run_huskycat(
            huskycat_executable,
            ["bootstrap"],
            repo,
            check=False,
        )

        # Assert success
        assert result.returncode == 0, f"Bootstrap failed: {result.stderr}"

        # Verify GitOps detected
        output_lower = result.stdout.lower()
        assert "gitops" in output_lower or "helm" in output_lower

        # Verify Terraform NOT detected
        assert "terraform" not in output_lower

        # Cleanup
        TestRepoFactory.cleanup_repo(repo)

    def test_bootstrap_k8s_only_repo(
        self,
        huskycat_executable: Path,
        tmp_path: Path,
    ) -> None:
        """Test bootstrap on Kubernetes-only repository."""
        repo = TestRepoFactory.create_gitops_repo(
            features=["k8s"],
            temp_dir=tmp_path,
        )

        result = self._run_huskycat(
            huskycat_executable,
            ["bootstrap"],
            repo,
            check=False,
        )

        assert result.returncode == 0, f"Bootstrap failed: {result.stderr}"

        output_lower = result.stdout.lower()
        assert "gitops" in output_lower or "kubernetes" in output_lower or "k8s" in output_lower

        # Cleanup
        TestRepoFactory.cleanup_repo(repo)

    def test_bootstrap_plain_python_repo(
        self,
        huskycat_executable: Path,
        tmp_path: Path,
    ) -> None:
        """Test bootstrap on non-GitOps Python repository."""
        # Create plain git repo (no GitOps features)
        repo = tmp_path
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Create Python file
        (repo / "main.py").write_text('print("Hello World")\n')
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Run bootstrap
        result = self._run_huskycat(
            huskycat_executable,
            ["bootstrap"],
            repo,
            check=False,
        )

        assert result.returncode == 0, f"Bootstrap failed: {result.stderr}"

        # Verify hooks installed
        hooks_dir = repo / ".git" / "hooks"
        assert (hooks_dir / "pre-commit").exists()
        assert (hooks_dir / "pre-push").exists()
        assert (hooks_dir / "commit-msg").exists()

        # Should NOT mention GitOps (not a GitOps repo)
        output_lower = result.stdout.lower()
        # Allow "gitops" in context of "no gitops detected" messages
        if "gitops" in output_lower:
            assert (
                "no gitops" in output_lower
                or "not a gitops" in output_lower
                or "gitops not detected" in output_lower
            ), "Should indicate no GitOps features for plain Python repo"

    def test_hook_execution_pre_commit_valid(
        self,
        huskycat_executable: Path,
        tmp_path: Path,
    ) -> None:
        """Test pre-commit hook executes and passes for valid Python file."""
        repo = TestRepoFactory.create_gitops_repo(
            features=["gitlab_ci"],
            temp_dir=tmp_path,
        )

        # Bootstrap
        self._run_huskycat(huskycat_executable, ["bootstrap"], repo)

        # Create valid Python file
        valid_py = '''"""Test module."""


def hello() -> str:
    """Say hello."""
    return "Hello"
'''
        (repo / "test.py").write_text(valid_py)
        subprocess.run(["git", "add", "test.py"], cwd=repo, check=True, capture_output=True)

        # Try to commit (should succeed)
        result = subprocess.run(
            ["git", "commit", "-m", "feat: add test file"],
            check=False, cwd=repo,
            capture_output=True,
            text=True,
        )

        # Pre-commit hook should allow commit
        assert result.returncode == 0, (
            f"Pre-commit hook should have passed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # Cleanup
        TestRepoFactory.cleanup_repo(repo)

    def test_hook_execution_pre_commit_invalid_syntax(
        self,
        huskycat_executable: Path,
        tmp_path: Path,
    ) -> None:
        """Test pre-commit hook blocks commit with invalid Python syntax."""
        repo = TestRepoFactory.create_gitops_repo(
            features=["gitlab_ci"],
            temp_dir=tmp_path,
        )

        # Bootstrap
        self._run_huskycat(huskycat_executable, ["bootstrap"], repo)

        # Create invalid Python file (syntax error)
        TestRepoFactory.create_invalid_python_file(repo, "bad.py")
        subprocess.run(["git", "add", "bad.py"], cwd=repo, check=True, capture_output=True)

        # Try to commit (should fail)
        result = subprocess.run(
            ["git", "commit", "-m", "feat: add bad file"],
            check=False, cwd=repo,
            capture_output=True,
            text=True,
        )

        # Pre-commit hook should block commit
        assert result.returncode != 0, (
            "Hook should have blocked commit with invalid syntax"
        )

        # Cleanup
        TestRepoFactory.cleanup_repo(repo)

    def test_hook_execution_commit_msg_invalid_format(
        self,
        huskycat_executable: Path,
        tmp_path: Path,
    ) -> None:
        """Test commit-msg hook blocks invalid commit message format."""
        repo = TestRepoFactory.create_gitops_repo(
            features=["helm"],
            temp_dir=tmp_path,
        )

        # Bootstrap
        self._run_huskycat(huskycat_executable, ["bootstrap"], repo)

        # Create valid file
        (repo / "test.txt").write_text("test content\n")
        subprocess.run(["git", "add", "test.txt"], cwd=repo, check=True, capture_output=True)

        # Try to commit with invalid message format
        result = subprocess.run(
            ["git", "commit", "-m", "Added new file"],  # Invalid format
            check=False, cwd=repo,
            capture_output=True,
            text=True,
        )

        # commit-msg hook should block
        assert result.returncode != 0, (
            "Hook should have blocked invalid commit message"
        )

        # Cleanup
        TestRepoFactory.cleanup_repo(repo)

    def test_hook_execution_commit_msg_valid_format(
        self,
        huskycat_executable: Path,
        tmp_path: Path,
    ) -> None:
        """Test commit-msg hook allows valid conventional commit format."""
        repo = TestRepoFactory.create_gitops_repo(
            features=["helm"],
            temp_dir=tmp_path,
        )

        # Bootstrap
        self._run_huskycat(huskycat_executable, ["bootstrap"], repo)

        # Create valid file
        (repo / "test.txt").write_text("test content\n")
        subprocess.run(["git", "add", "test.txt"], cwd=repo, check=True, capture_output=True)

        # Try to commit with valid message format
        result = subprocess.run(
            ["git", "commit", "-m", "feat: add test file"],  # Valid format
            check=False, cwd=repo,
            capture_output=True,
            text=True,
        )

        # commit-msg hook should allow
        assert result.returncode == 0, (
            f"Hook should have allowed valid commit message:\nstderr: {result.stderr}"
        )

        # Cleanup
        TestRepoFactory.cleanup_repo(repo)

    def test_force_regenerate_hooks(
        self,
        huskycat_executable: Path,
        tmp_path: Path,
    ) -> None:
        """Test --force flag regenerates existing hooks."""
        repo = TestRepoFactory.create_gitops_repo(
            features=["helm", "k8s"],
            temp_dir=tmp_path,
        )

        # Bootstrap first time
        result1 = self._run_huskycat(huskycat_executable, ["bootstrap"], repo)
        assert result1.returncode == 0

        # Get hook content
        pre_commit_hook = repo / ".git" / "hooks" / "pre-commit"
        original_content = pre_commit_hook.read_text()

        # Modify hook (simulate old version)
        modified_content = original_content.replace(
            'VERSION="2.0.0"', 'VERSION="1.9.0"'
        )
        pre_commit_hook.write_text(modified_content)

        # Bootstrap again with --force
        result2 = self._run_huskycat(
            huskycat_executable,
            ["bootstrap", "--force"],
            repo,
        )
        assert result2.returncode == 0

        # Verify hook was regenerated
        new_content = pre_commit_hook.read_text()
        assert 'VERSION="2.0.0"' in new_content or "VERSION=2.0.0" in new_content

        # Cleanup
        TestRepoFactory.cleanup_repo(repo)

    def test_gitlab_ci_validation_in_hooks(
        self,
        huskycat_executable: Path,
        tmp_path: Path,
    ) -> None:
        """Test that GitLab CI validation runs in pre-push hook."""
        repo = TestRepoFactory.create_gitops_repo(
            features=["gitlab_ci", "helm"],
            temp_dir=tmp_path,
        )

        # Bootstrap
        self._run_huskycat(huskycat_executable, ["bootstrap"], repo)

        # Verify pre-push hook mentions GitLab CI
        pre_push_hook = repo / ".git" / "hooks" / "pre-push"
        hook_content = pre_push_hook.read_text()
        assert (
            "gitlab-ci" in hook_content.lower() or "ci-validate" in hook_content.lower()
        ), "Pre-push hook should validate GitLab CI"

        # Cleanup
        TestRepoFactory.cleanup_repo(repo)

    def test_gitops_fast_mode_in_hooks(
        self,
        huskycat_executable: Path,
        tmp_path: Path,
    ) -> None:
        """Test that GitOps validation uses --fast flag in hooks."""
        repo = TestRepoFactory.create_gitops_repo(
            features=["helm", "k8s"],
            temp_dir=tmp_path,
        )

        # Bootstrap
        self._run_huskycat(huskycat_executable, ["bootstrap"], repo)

        # Verify pre-push hook uses --fast
        pre_push_hook = repo / ".git" / "hooks" / "pre-push"
        hook_content = pre_push_hook.read_text()
        assert "--fast" in hook_content, (
            "Pre-push hook should use --fast for GitOps validation"
        )

        # Cleanup
        TestRepoFactory.cleanup_repo(repo)


class TestBootstrapEdgeCases:
    """Test edge cases and error handling in bootstrap."""

    @pytest.fixture
    def huskycat_executable(self) -> Path:
        """Get path to HuskyCat executable."""
        binary_path = Path.home() / ".local" / "bin" / "huskycat"
        if binary_path.exists() and binary_path.is_file():
            return binary_path
        return Path("UV_RUN_MODE")

    def _run_huskycat(
        self,
        huskycat_exec: Path,
        args: list[str],
        cwd: Path,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run HuskyCat command."""
        if huskycat_exec.name == "UV_RUN_MODE":
            project_root = Path(__file__).parent.parent.parent
            cmd = ["uv", "run", "python", "-m", "huskycat"] + args
            # Copy existing environment and update with our custom variables
            env = os.environ.copy()
            env["PYTHONPATH"] = str(project_root / "src")
            return subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=check,
                env=env,
            )
        cmd = [str(huskycat_exec)] + args
        return subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
        )

    def test_bootstrap_non_git_directory(
        self,
        huskycat_executable: Path,
        tmp_path: Path,
    ) -> None:
        """Test bootstrap fails gracefully on non-git directory."""
        # Don't initialize git
        (tmp_path / "test.txt").write_text("test")

        result = self._run_huskycat(
            huskycat_executable,
            ["bootstrap"],
            tmp_path,
            check=False,
        )

        # Should fail with clear error
        assert result.returncode != 0, "Should fail on non-git directory"
        assert (
            "not a git repository" in result.stderr.lower()
            or "not a git repository" in result.stdout.lower()
        ), "Should indicate it's not a git repo"

    def test_bootstrap_empty_git_repo(
        self,
        huskycat_executable: Path,
        tmp_path: Path,
    ) -> None:
        """Test bootstrap on empty git repository."""
        # Initialize git but don't commit anything
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        result = self._run_huskycat(
            huskycat_executable,
            ["bootstrap"],
            tmp_path,
            check=False,
        )

        # Should succeed (hooks can be installed on empty repos)
        assert result.returncode == 0, f"Bootstrap should work on empty repo: {result.stderr}"

        # Verify hooks installed
        hooks_dir = tmp_path / ".git" / "hooks"
        assert (hooks_dir / "pre-commit").exists()
        assert (hooks_dir / "pre-push").exists()
        assert (hooks_dir / "commit-msg").exists()
