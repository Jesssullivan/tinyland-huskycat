"""Tests for all 17 validators - basic interface, availability, and validation logic."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from huskycat.validators.base import ValidationResult, Validator
from huskycat.validators.ruff import RuffValidator
from huskycat.validators.black import BlackValidator
from huskycat.validators.mypy import MypyValidator
from huskycat.validators.flake8 import Flake8Validator
from huskycat.validators.isort import IsortValidator
from huskycat.validators.autoflake import AutoflakeValidator
from huskycat.validators.bandit import BanditValidator
from huskycat.validators.taplo import TaploValidator
from huskycat.validators.terraform import TerraformValidator
from huskycat.validators.eslint import ESLintValidator
from huskycat.validators.prettier import PrettierValidator
from huskycat.validators.chapel import ChapelValidator
from huskycat.validators.ansible_lint import AnsibleLintValidator
from huskycat.validators.yamllint import YamlLintValidator
from huskycat.validators.hadolint import HadolintValidator
from huskycat.validators.shellcheck import ShellcheckValidator
from huskycat.validators.gitlab_ci import GitLabCIValidator


# All validators with their expected properties
ALL_VALIDATORS = [
    (RuffValidator, "ruff", {".py", ".pyi"}),
    (BlackValidator, "python-black", {".py", ".pyi"}),
    (MypyValidator, "mypy", {".py", ".pyi"}),
    (Flake8Validator, "flake8", {".py", ".pyi"}),
    (IsortValidator, "isort", {".py", ".pyi"}),
    (AutoflakeValidator, "autoflake", {".py", ".pyi"}),
    (BanditValidator, "bandit", {".py", ".pyi"}),
    (TaploValidator, "taplo", {".toml"}),
    (TerraformValidator, "terraform", {".tf", ".tfvars"}),
    (ESLintValidator, "js-eslint", {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}),
    (PrettierValidator, "js-prettier", {".js", ".jsx", ".ts", ".tsx", ".json", ".css", ".md", ".html", ".scss"}),
    (ChapelValidator, "chapel", {".chpl"}),
    (AnsibleLintValidator, "ansible-lint", set()),
    (YamlLintValidator, "yamllint", {".yml", ".yaml"}),
    (HadolintValidator, "hadolint", {".dockerfile"}),
    (ShellcheckValidator, "shellcheck", {".sh", ".bash", ".zsh", ".ksh"}),
    (GitLabCIValidator, "gitlab-ci", set()),
]


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_defaults(self):
        result = ValidationResult(tool="ruff", filepath="test.py", success=True)
        assert result.messages == []
        assert result.errors == []
        assert result.warnings == []
        assert result.fixed is False
        assert result.duration_ms == 0

    def test_to_dict(self):
        result = ValidationResult(
            tool="ruff",
            filepath="test.py",
            success=False,
            errors=["Line 1: E302"],
            duration_ms=42,
        )
        d = result.to_dict()
        assert d["tool"] == "ruff"
        assert d["filepath"] == "test.py"
        assert d["success"] is False
        assert d["errors"] == ["Line 1: E302"]
        assert d["duration_ms"] == 42

    def test_error_count(self):
        result = ValidationResult(
            tool="test", filepath="f.py", success=False,
            errors=["e1", "e2", "e3"],
        )
        assert result.error_count == 3

    def test_warning_count(self):
        result = ValidationResult(
            tool="test", filepath="f.py", success=True,
            warnings=["w1"],
        )
        assert result.warning_count == 1

    def test_zero_counts(self):
        result = ValidationResult(tool="test", filepath="f.py", success=True)
        assert result.error_count == 0
        assert result.warning_count == 0


class TestValidatorBase:
    """Test Validator abstract base class."""

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            Validator()

    def test_auto_fix_default(self):
        """auto_fix defaults to False."""
        v = RuffValidator()
        assert v.auto_fix is False

    def test_auto_fix_enabled(self):
        v = RuffValidator(auto_fix=True)
        assert v.auto_fix is True

    def test_command_defaults_to_name(self):
        v = RuffValidator()
        assert v.command == v.name

    def test_can_handle_matching(self):
        v = RuffValidator()
        assert v.can_handle(Path("test.py")) is True
        assert v.can_handle(Path("test.pyi")) is True

    def test_can_handle_non_matching(self):
        v = RuffValidator()
        assert v.can_handle(Path("test.js")) is False
        assert v.can_handle(Path("test.toml")) is False


class TestValidatorIsAvailable:
    """Test is_available() for all validators."""

    @patch("shutil.which", return_value="/usr/bin/ruff")
    def test_local_tool_available(self, mock_which):
        v = RuffValidator()
        with patch.object(v, "_get_execution_mode", return_value="local"):
            assert v.is_available() is True

    @patch("shutil.which", return_value=None)
    def test_local_tool_not_available(self, mock_which):
        v = RuffValidator()
        with patch.object(v, "_get_execution_mode", return_value="local"):
            assert v.is_available() is False

    def test_container_mode(self):
        v = RuffValidator()
        with patch.object(v, "_get_execution_mode", return_value="container"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                assert v.is_available() is True

    def test_container_mode_not_found(self):
        v = RuffValidator()
        with patch.object(v, "_get_execution_mode", return_value="container"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)
                assert v.is_available() is False


class TestExecutionMode:
    """Test execution mode detection."""

    def test_local_mode_default(self):
        v = RuffValidator()
        with patch.object(v, "_is_running_in_container", return_value=False):
            mode = v._get_execution_mode()
            assert mode == "local"

    def test_container_mode_detection(self):
        v = RuffValidator()
        with patch.object(v, "_is_running_in_container", return_value=True):
            mode = v._get_execution_mode()
            assert mode == "container"

    def test_is_running_in_container_dockerenv(self):
        v = RuffValidator()
        with patch("os.path.exists", side_effect=lambda p: p == "/.dockerenv"):
            with patch.dict("os.environ", {}, clear=True):
                assert v._is_running_in_container() is True

    def test_is_running_in_container_podman(self):
        v = RuffValidator()
        with patch("os.path.exists", return_value=False):
            with patch.dict("os.environ", {"container": "podman"}, clear=False):
                assert v._is_running_in_container() is True

    def test_not_in_container(self):
        v = RuffValidator()
        with patch("os.path.exists", return_value=False):
            with patch.dict("os.environ", {}, clear=True):
                assert v._is_running_in_container() is False


class TestValidatorInterface:
    """Test that all validators implement the required interface correctly."""

    @pytest.mark.parametrize(
        "validator_class,expected_name,expected_extensions",
        ALL_VALIDATORS,
        ids=[v[1] for v in ALL_VALIDATORS],
    )
    def test_validator_name(self, validator_class, expected_name, expected_extensions):
        v = validator_class()
        assert v.name == expected_name

    @pytest.mark.parametrize(
        "validator_class,expected_name,expected_extensions",
        ALL_VALIDATORS,
        ids=[v[1] for v in ALL_VALIDATORS],
    )
    def test_validator_extensions(self, validator_class, expected_name, expected_extensions):
        v = validator_class()
        assert v.extensions == expected_extensions

    @pytest.mark.parametrize(
        "validator_class,expected_name,expected_extensions",
        ALL_VALIDATORS,
        ids=[v[1] for v in ALL_VALIDATORS],
    )
    def test_validator_has_validate_method(self, validator_class, expected_name, expected_extensions):
        v = validator_class()
        assert hasattr(v, "validate")
        assert callable(v.validate)

    @pytest.mark.parametrize(
        "validator_class,expected_name,expected_extensions",
        ALL_VALIDATORS,
        ids=[v[1] for v in ALL_VALIDATORS],
    )
    def test_validator_has_is_available(self, validator_class, expected_name, expected_extensions):
        v = validator_class()
        assert hasattr(v, "is_available")
        assert callable(v.is_available)

    @pytest.mark.parametrize(
        "validator_class,expected_name,expected_extensions",
        ALL_VALIDATORS,
        ids=[v[1] for v in ALL_VALIDATORS],
    )
    def test_validator_auto_fix(self, validator_class, expected_name, expected_extensions):
        v = validator_class(auto_fix=True)
        assert v.auto_fix is True


class TestRuffValidation:
    """Test RuffValidator.validate()."""

    @patch.object(RuffValidator, "_execute_command")
    def test_validate_success(self, mock_exec, tmp_path):
        mock_exec.return_value = MagicMock(returncode=0, stdout="")
        v = RuffValidator()
        result = v.validate(tmp_path / "test.py")
        assert result.success is True
        assert result.tool == "ruff"

    @patch.object(RuffValidator, "_execute_command")
    def test_validate_failure_json(self, mock_exec, tmp_path):
        import json
        issues = [{"location": {"row": 1}, "message": "E302 expected 2 blank lines"}]
        mock_exec.return_value = MagicMock(returncode=1, stdout=json.dumps(issues))
        v = RuffValidator()
        result = v.validate(tmp_path / "test.py")
        assert result.success is False
        assert len(result.errors) == 1
        assert "Line 1" in result.errors[0]

    @patch.object(RuffValidator, "_execute_command")
    def test_validate_failure_non_json(self, mock_exec, tmp_path):
        mock_exec.return_value = MagicMock(returncode=1, stdout="syntax error")
        v = RuffValidator()
        result = v.validate(tmp_path / "test.py")
        assert result.success is False

    @patch.object(RuffValidator, "_execute_command", side_effect=Exception("timeout"))
    def test_validate_exception(self, mock_exec, tmp_path):
        v = RuffValidator()
        result = v.validate(tmp_path / "test.py")
        assert result.success is False
        assert "timeout" in result.errors[0]

    @patch.object(RuffValidator, "_execute_command")
    def test_validate_with_fix(self, mock_exec, tmp_path):
        mock_exec.return_value = MagicMock(returncode=0, stdout="")
        v = RuffValidator(auto_fix=True)
        result = v.validate(tmp_path / "test.py")
        assert result.success is True
        assert result.fixed is True
        # Verify --fix was in command
        call_args = mock_exec.call_args[0][0]
        assert "--fix" in call_args


class TestBlackValidation:
    """Test BlackValidator.validate()."""

    @patch.object(BlackValidator, "_execute_command")
    def test_validate_success(self, mock_exec, tmp_path):
        mock_exec.return_value = MagicMock(returncode=0, stdout="")
        v = BlackValidator()
        result = v.validate(tmp_path / "test.py")
        assert result.success is True
        assert "formatted" in result.messages[0].lower()

    @patch.object(BlackValidator, "_execute_command")
    def test_validate_needs_formatting(self, mock_exec, tmp_path):
        mock_exec.return_value = MagicMock(returncode=1, stdout="would reformat test.py")
        v = BlackValidator()
        result = v.validate(tmp_path / "test.py")
        assert result.success is False
        assert "formatting" in result.errors[0].lower()

    @patch.object(BlackValidator, "_execute_command", side_effect=Exception("boom"))
    def test_validate_exception(self, mock_exec, tmp_path):
        v = BlackValidator()
        result = v.validate(tmp_path / "test.py")
        assert result.success is False

    @patch.object(BlackValidator, "_execute_command")
    def test_validate_with_fix(self, mock_exec, tmp_path):
        mock_exec.return_value = MagicMock(returncode=0, stdout="")
        v = BlackValidator(auto_fix=True)
        result = v.validate(tmp_path / "test.py")
        assert result.success is True
        # Verify --check was NOT in command
        call_args = mock_exec.call_args[0][0]
        assert "--check" not in call_args


class TestMypyValidation:
    """Test MypyValidator.validate()."""

    @patch.object(MypyValidator, "_execute_command")
    def test_validate_success(self, mock_exec, tmp_path):
        mock_exec.return_value = MagicMock(returncode=0, stdout="")
        v = MypyValidator()
        result = v.validate(tmp_path / "test.py")
        assert result.success is True

    @patch.object(MypyValidator, "_execute_command")
    def test_validate_type_errors(self, mock_exec, tmp_path):
        mock_exec.return_value = MagicMock(
            returncode=1,
            stdout="test.py:1: error: Incompatible types\ntest.py:2: warning: unused var",
        )
        v = MypyValidator()
        result = v.validate(tmp_path / "test.py")
        assert result.success is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1

    @patch.object(MypyValidator, "_execute_command", side_effect=Exception("crash"))
    def test_validate_exception(self, mock_exec, tmp_path):
        v = MypyValidator()
        result = v.validate(tmp_path / "test.py")
        assert result.success is False


class TestFlake8Validation:
    """Test Flake8Validator.validate()."""

    @patch.object(Flake8Validator, "_execute_command")
    def test_validate_success(self, mock_exec, tmp_path):
        mock_exec.return_value = MagicMock(returncode=0, stdout="")
        v = Flake8Validator()
        result = v.validate(tmp_path / "test.py")
        assert result.success is True

    @patch.object(Flake8Validator, "_execute_command")
    def test_validate_errors(self, mock_exec, tmp_path):
        mock_exec.return_value = MagicMock(
            returncode=1,
            stdout="test.py:1:1: E302 expected 2 blank lines\ntest.py:5:1: W291 trailing whitespace",
        )
        v = Flake8Validator()
        result = v.validate(tmp_path / "test.py")
        assert result.success is False

    @patch.object(Flake8Validator, "_execute_command", side_effect=Exception("err"))
    def test_validate_exception(self, mock_exec, tmp_path):
        v = Flake8Validator()
        result = v.validate(tmp_path / "test.py")
        assert result.success is False


class TestBundledToolPath:
    """Test bundled tool path detection."""

    def test_no_bundled_dir(self, tmp_path):
        v = RuffValidator()
        with patch("pathlib.Path.home", return_value=tmp_path):
            assert v._get_bundled_tool_path() is None

    def test_bundled_tool_found(self, tmp_path):
        tools_dir = tmp_path / ".huskycat" / "tools"
        tools_dir.mkdir(parents=True)
        ruff_bin = tools_dir / "ruff"
        ruff_bin.touch()

        v = RuffValidator()
        with patch("pathlib.Path.home", return_value=tmp_path):
            assert v._get_bundled_tool_path() == ruff_bin

    def test_bundled_tool_not_found(self, tmp_path):
        tools_dir = tmp_path / ".huskycat" / "tools"
        tools_dir.mkdir(parents=True)
        # No ruff binary

        v = RuffValidator()
        with patch("pathlib.Path.home", return_value=tmp_path):
            assert v._get_bundled_tool_path() is None


class TestContainerRuntime:
    """Test container runtime detection."""

    @patch("subprocess.run")
    def test_podman_available(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        v = RuffValidator()
        assert v._container_runtime_exists() is True

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_no_runtime(self, mock_run):
        v = RuffValidator()
        assert v._container_runtime_exists() is False

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_get_available_runtime_raises(self, mock_run):
        v = RuffValidator()
        with pytest.raises(RuntimeError, match="No container runtime"):
            v._get_available_container_runtime()


class TestLogExecutionMode:
    """Test execution mode logging."""

    def test_log_local(self):
        v = RuffValidator()
        v._log_execution_mode("local")  # Should not raise

    def test_log_bundled(self):
        v = RuffValidator()
        v._log_execution_mode("bundled")  # Should not raise

    def test_log_container(self):
        v = RuffValidator()
        v._log_execution_mode("container")  # Should not raise
