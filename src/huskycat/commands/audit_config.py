"""Git configuration audit command for HuskyCat."""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.base import BaseCommand, CommandResult, CommandStatus


class AuditConfigCommand(BaseCommand):
    """Audit global and local git configuration for best practices."""

    @property
    def name(self) -> str:
        return "audit-config"

    @property
    def description(self) -> str:
        return "Audit git configuration for best practices and security"

    def execute(self, *args: Any, **kwargs: Any) -> CommandResult:
        """Run git configuration audit.

        Args:
            fix: Auto-fix detected issues
        """
        fix = kwargs.get("fix", False)
        checks: List[Dict[str, Any]] = []
        errors: List[str] = []
        warnings: List[str] = []
        fixed: List[str] = []

        # Run all audit checks
        checks.append(self._check_hooks_path(fix))
        checks.append(self._check_credential_protection(fix))
        checks.append(self._check_large_file_protection(fix))
        checks.append(self._check_branch_protection(fix))
        checks.append(self._check_signing(fix))
        checks.append(self._check_pager(fix))
        checks.append(self._check_direnv(fix))
        checks.append(self._check_default_branch(fix))
        checks.append(self._check_pull_rebase(fix))

        # Collect results
        passed = 0
        failed = 0
        warned = 0
        for check in checks:
            if check["status"] == "pass":
                passed += 1
            elif check["status"] == "warn":
                warned += 1
                warnings.append(f"{check['name']}: {check['message']}")
            elif check["status"] == "fail":
                failed += 1
                errors.append(f"{check['name']}: {check['message']}")
            if check.get("fixed"):
                fixed.append(f"{check['name']}: {check['fixed']}")

        # Determine overall status
        if failed > 0:
            status = CommandStatus.FAILED
            message = f"Git config audit: {failed} issues, {warned} warnings, {passed} passed"
        elif warned > 0:
            status = CommandStatus.WARNING
            message = f"Git config audit: {warned} warnings, {passed} passed"
        else:
            status = CommandStatus.SUCCESS
            message = f"Git config audit: all {passed} checks passed"

        if fixed:
            message += f" ({len(fixed)} auto-fixed)"

        return CommandResult(
            status=status,
            message=message,
            errors=errors,
            warnings=warnings,
            data={
                "checks": checks,
                "summary": {
                    "passed": passed,
                    "failed": failed,
                    "warned": warned,
                    "fixed": len(fixed),
                    "total": len(checks),
                },
            },
        )

    def _git_config(
        self, key: str, scope: str = "global"
    ) -> Optional[str]:
        """Get a git config value.

        Args:
            key: Config key (e.g., 'core.hooksPath')
            scope: 'global', 'local', or 'system'
        """
        try:
            result = subprocess.run(
                ["git", "config", f"--{scope}", key],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None

    def _set_git_config(
        self, key: str, value: str, scope: str = "global"
    ) -> bool:
        """Set a git config value."""
        try:
            result = subprocess.run(
                ["git", "config", f"--{scope}", key, value],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _check_hooks_path(self, fix: bool = False) -> Dict[str, Any]:
        """Check that core.hooksPath is set and valid."""
        check = {
            "name": "core.hooksPath",
            "description": "Global git hooks directory configured",
        }

        hooks_path = self._git_config("core.hooksPath")
        if not hooks_path:
            check["status"] = "warn"
            check["message"] = "core.hooksPath not set (no global hooks active)"
            if fix:
                default_path = os.path.expanduser("~/.config/git/hooks")
                os.makedirs(default_path, exist_ok=True)
                if self._set_git_config("core.hooksPath", default_path):
                    check["fixed"] = f"Set to {default_path}"
            return check

        expanded = os.path.expanduser(hooks_path)
        if not os.path.isdir(expanded):
            check["status"] = "fail"
            check["message"] = f"Hooks path '{hooks_path}' does not exist"
            if fix:
                os.makedirs(expanded, exist_ok=True)
                check["fixed"] = f"Created directory {expanded}"
        else:
            check["status"] = "pass"
            check["message"] = f"Set to {hooks_path}"

        return check

    def _check_credential_protection(self, fix: bool = False) -> Dict[str, Any]:
        """Check for credential protection hooks."""
        check = {
            "name": "Credential protection",
            "description": "Pre-commit hook blocks secrets and credentials",
        }

        hooks_path = self._git_config("core.hooksPath")
        if not hooks_path:
            check["status"] = "warn"
            check["message"] = "No global hooks path configured"
            return check

        pre_commit = Path(os.path.expanduser(hooks_path)) / "pre-commit"
        if not pre_commit.exists():
            check["status"] = "warn"
            check["message"] = "No global pre-commit hook found"
            return check

        content = pre_commit.read_text()
        has_cred_check = any(
            pattern in content.lower()
            for pattern in ["credential", "secret", "api.key", "private.key", ".env"]
        )

        if has_cred_check:
            check["status"] = "pass"
            check["message"] = "Credential protection active in pre-commit hook"
        else:
            check["status"] = "warn"
            check["message"] = "Pre-commit hook exists but may not check for credentials"

        return check

    def _check_large_file_protection(self, fix: bool = False) -> Dict[str, Any]:
        """Check for large file protection."""
        check = {
            "name": "Large file protection",
            "description": "Pre-commit hook warns about large files",
        }

        hooks_path = self._git_config("core.hooksPath")
        if not hooks_path:
            check["status"] = "warn"
            check["message"] = "No global hooks path configured"
            return check

        pre_commit = Path(os.path.expanduser(hooks_path)) / "pre-commit"
        if not pre_commit.exists():
            check["status"] = "warn"
            check["message"] = "No global pre-commit hook found"
            return check

        content = pre_commit.read_text()
        has_size_check = any(
            pattern in content.lower()
            for pattern in ["file_size", "filesize", "large_file", "max_size", "5000"]
        )

        if has_size_check:
            check["status"] = "pass"
            check["message"] = "Large file protection active"
        else:
            check["status"] = "warn"
            check["message"] = "No large file size check detected in hooks"

        return check

    def _check_branch_protection(self, fix: bool = False) -> Dict[str, Any]:
        """Check for branch protection in pre-push hook."""
        check = {
            "name": "Branch protection",
            "description": "Pre-push hook protects main/master branches",
        }

        hooks_path = self._git_config("core.hooksPath")
        if not hooks_path:
            check["status"] = "warn"
            check["message"] = "No global hooks path configured"
            return check

        pre_push = Path(os.path.expanduser(hooks_path)) / "pre-push"
        if not pre_push.exists():
            check["status"] = "warn"
            check["message"] = "No global pre-push hook found"
            return check

        content = pre_push.read_text()
        has_branch_check = any(
            pattern in content
            for pattern in ["main", "master", "protected", "PROTECTED_BRANCHES"]
        )

        if has_branch_check:
            check["status"] = "pass"
            check["message"] = "Branch protection active in pre-push hook"
        else:
            check["status"] = "warn"
            check["message"] = "Pre-push hook exists but may not protect branches"

        return check

    def _check_signing(self, fix: bool = False) -> Dict[str, Any]:
        """Check if commit signing is configured."""
        check = {
            "name": "Commit signing",
            "description": "GPG or SSH commit signing configured",
        }

        gpg_sign = self._git_config("commit.gpgsign")
        gpg_format = self._git_config("gpg.format")
        signing_key = self._git_config("user.signingkey")

        if gpg_sign == "true":
            fmt = gpg_format or "openpgp"
            check["status"] = "pass"
            check["message"] = f"Signing enabled ({fmt})"
            if signing_key:
                check["message"] += f", key configured"
        else:
            check["status"] = "warn"
            check["message"] = "Commit signing not enabled (recommended for production)"

        return check

    def _check_pager(self, fix: bool = False) -> Dict[str, Any]:
        """Check if delta or another pager is configured."""
        check = {
            "name": "Diff pager",
            "description": "Enhanced diff viewer configured",
        }

        pager = self._git_config("core.pager")
        if pager and "delta" in pager.lower():
            check["status"] = "pass"
            check["message"] = f"Delta pager configured ({pager})"
        elif pager:
            check["status"] = "pass"
            check["message"] = f"Custom pager configured ({pager})"
        else:
            check["status"] = "warn"
            check["message"] = "No custom pager (consider delta for better diffs)"

        return check

    def _check_direnv(self, fix: bool = False) -> Dict[str, Any]:
        """Check if direnv integration is present."""
        check = {
            "name": "direnv integration",
            "description": "direnv configured for automatic environment activation",
        }

        # Check if direnv is installed
        try:
            result = subprocess.run(
                ["which", "direnv"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if result.returncode != 0:
                check["status"] = "warn"
                check["message"] = "direnv not installed"
                return check
        except Exception:
            check["status"] = "warn"
            check["message"] = "Could not check for direnv"
            return check

        # Check for .envrc in current directory
        envrc = Path(".envrc")
        if envrc.exists():
            content = envrc.read_text()
            has_flake = "use flake" in content
            check["status"] = "pass"
            check["message"] = "direnv active"
            if has_flake:
                check["message"] += " with Nix flake"
        else:
            check["status"] = "warn"
            check["message"] = "No .envrc in current directory"

        return check

    def _check_default_branch(self, fix: bool = False) -> Dict[str, Any]:
        """Check default branch is set to main."""
        check = {
            "name": "Default branch",
            "description": "init.defaultBranch set to 'main'",
        }

        default_branch = self._git_config("init.defaultBranch")
        if default_branch == "main":
            check["status"] = "pass"
            check["message"] = "Default branch is 'main'"
        elif default_branch:
            check["status"] = "pass"
            check["message"] = f"Default branch is '{default_branch}'"
        else:
            check["status"] = "warn"
            check["message"] = "init.defaultBranch not set (defaults to 'master')"
            if fix:
                if self._set_git_config("init.defaultBranch", "main"):
                    check["fixed"] = "Set to 'main'"

        return check

    def _check_pull_rebase(self, fix: bool = False) -> Dict[str, Any]:
        """Check if pull.rebase is configured."""
        check = {
            "name": "Pull strategy",
            "description": "pull.rebase configured for clean history",
        }

        pull_rebase = self._git_config("pull.rebase")
        if pull_rebase == "true":
            check["status"] = "pass"
            check["message"] = "pull.rebase enabled (clean history)"
        elif pull_rebase:
            check["status"] = "pass"
            check["message"] = f"pull.rebase = {pull_rebase}"
        else:
            check["status"] = "warn"
            check["message"] = "pull.rebase not set (consider enabling for cleaner history)"
            if fix:
                if self._set_git_config("pull.rebase", "true"):
                    check["fixed"] = "Enabled pull.rebase"

        return check
