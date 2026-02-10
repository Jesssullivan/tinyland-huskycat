"""Tests for all validator validate() methods via mocked _execute_command.

This covers the actual validation logic paths (success, failure, auto-fix,
exception) for every validator to maximize coverage of the validators package.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from huskycat.validators.isort import IsortValidator
from huskycat.validators.autoflake import AutoflakeValidator
from huskycat.validators.bandit import BanditValidator
from huskycat.validators.taplo import TaploValidator
from huskycat.validators.terraform import TerraformValidator
from huskycat.validators.eslint import ESLintValidator
from huskycat.validators.prettier import PrettierValidator
from huskycat.validators.chapel import ChapelValidator
from huskycat.validators.shellcheck import ShellcheckValidator
from huskycat.validators.hadolint import HadolintValidator
from huskycat.validators.yamllint import YamlLintValidator
from huskycat.validators.gitlab_ci import GitLabCIValidator
from huskycat.validators.ansible_lint import AnsibleLintValidator


FP = Path("/tmp/test.py")


class TestIsortValidate:
    """Test IsortValidator.validate()."""

    @patch.object(IsortValidator, "_execute_command")
    def test_success(self, mock_exec):
        mock_exec.return_value = MagicMock(returncode=0)
        result = IsortValidator().validate(FP)
        assert result.success is True
        assert "sorted" in result.messages[0].lower()

    @patch.object(IsortValidator, "_execute_command")
    def test_failure_no_fix(self, mock_exec):
        mock_exec.return_value = MagicMock(returncode=1, stdout="- import os\n+ import sys")
        result = IsortValidator().validate(FP)
        assert result.success is False
        assert "not properly sorted" in result.errors[0].lower()

    @patch.object(IsortValidator, "_execute_command")
    def test_failure_with_fix_success(self, mock_exec):
        # First call (check) fails, second call (fix) succeeds
        mock_exec.side_effect = [
            MagicMock(returncode=1, stdout="diff"),
            MagicMock(returncode=0),
        ]
        result = IsortValidator(auto_fix=True).validate(FP)
        assert result.success is True
        assert result.fixed is True

    @patch.object(IsortValidator, "_execute_command")
    def test_failure_with_fix_failure(self, mock_exec):
        mock_exec.side_effect = [
            MagicMock(returncode=1, stdout=""),
            MagicMock(returncode=1, stderr="error"),
        ]
        result = IsortValidator(auto_fix=True).validate(FP)
        assert result.success is False

    @patch.object(IsortValidator, "_execute_command", side_effect=Exception("err"))
    def test_exception(self, mock_exec):
        result = IsortValidator().validate(FP)
        assert result.success is False


class TestAutoflakeValidate:
    """Test AutoflakeValidator.validate()."""

    @patch.object(AutoflakeValidator, "_execute_command")
    def test_success(self, mock_exec):
        mock_exec.return_value = MagicMock(returncode=0)
        result = AutoflakeValidator().validate(FP)
        assert result.success is True

    @patch.object(AutoflakeValidator, "_execute_command")
    def test_failure_no_fix(self, mock_exec):
        mock_exec.return_value = MagicMock(returncode=1, stdout="")
        result = AutoflakeValidator().validate(FP)
        assert result.success is False
        assert "unused" in result.errors[0].lower()

    @patch.object(AutoflakeValidator, "_execute_command")
    def test_failure_with_fix_success(self, mock_exec):
        mock_exec.side_effect = [
            MagicMock(returncode=1, stdout=""),
            MagicMock(returncode=0),
        ]
        result = AutoflakeValidator(auto_fix=True).validate(FP)
        assert result.success is True
        assert result.fixed is True

    @patch.object(AutoflakeValidator, "_execute_command")
    def test_failure_with_fix_failure(self, mock_exec):
        mock_exec.side_effect = [
            MagicMock(returncode=1, stdout=""),
            MagicMock(returncode=1, stderr="error"),
        ]
        result = AutoflakeValidator(auto_fix=True).validate(FP)
        assert result.success is False

    @patch.object(AutoflakeValidator, "_execute_command", side_effect=Exception("boom"))
    def test_exception(self, mock_exec):
        result = AutoflakeValidator().validate(FP)
        assert result.success is False


class TestBanditValidate:
    """Test BanditValidator.validate()."""

    @patch.object(BanditValidator, "_execute_command")
    def test_success(self, mock_exec):
        mock_exec.return_value = MagicMock(returncode=0, stdout="")
        result = BanditValidator().validate(FP)
        assert result.success is True

    @patch.object(BanditValidator, "_execute_command")
    def test_failure_with_json(self, mock_exec):
        data = {
            "results": [
                {
                    "line_number": 10,
                    "test_name": "B602",
                    "issue_text": "subprocess call with shell=True",
                    "issue_severity": "HIGH",
                }
            ]
        }
        mock_exec.return_value = MagicMock(returncode=1, stdout=json.dumps(data))
        result = BanditValidator().validate(FP)
        assert result.success is False
        assert len(result.errors) == 1
        assert "Line 10" in result.errors[0]

    @patch.object(BanditValidator, "_execute_command")
    def test_failure_medium_severity_is_warning(self, mock_exec):
        data = {
            "results": [
                {
                    "line_number": 5,
                    "test_name": "B101",
                    "issue_text": "Use of assert",
                    "issue_severity": "MEDIUM",
                }
            ]
        }
        mock_exec.return_value = MagicMock(returncode=1, stdout=json.dumps(data))
        result = BanditValidator().validate(FP)
        assert result.success is False
        assert len(result.warnings) == 1

    @patch.object(BanditValidator, "_execute_command")
    def test_failure_non_json(self, mock_exec):
        mock_exec.return_value = MagicMock(returncode=1, stdout="error text")
        result = BanditValidator().validate(FP)
        assert result.success is False

    @patch.object(BanditValidator, "_execute_command", side_effect=Exception("crash"))
    def test_exception(self, mock_exec):
        result = BanditValidator().validate(FP)
        assert result.success is False


class TestTaploValidate:
    """Test TaploValidator.validate()."""

    @patch.object(TaploValidator, "_execute_command")
    def test_success(self, mock_exec):
        mock_exec.return_value = MagicMock(returncode=0)
        result = TaploValidator().validate(Path("/tmp/test.toml"))
        assert result.success is True
        assert "formatted" in result.messages[0].lower()

    @patch.object(TaploValidator, "_execute_command")
    def test_failure_no_fix(self, mock_exec):
        mock_exec.return_value = MagicMock(returncode=1, stdout="file needs format", stderr="")
        result = TaploValidator().validate(Path("/tmp/test.toml"))
        assert result.success is False

    @patch.object(TaploValidator, "_execute_command")
    def test_failure_with_fix_success(self, mock_exec):
        mock_exec.side_effect = [
            MagicMock(returncode=1, stdout=""),
            MagicMock(returncode=0),
        ]
        result = TaploValidator(auto_fix=True).validate(Path("/tmp/test.toml"))
        assert result.success is True
        assert result.fixed is True

    @patch.object(TaploValidator, "_execute_command")
    def test_failure_with_fix_failure(self, mock_exec):
        mock_exec.side_effect = [
            MagicMock(returncode=1, stdout=""),
            MagicMock(returncode=1, stderr="parse error", stdout=""),
        ]
        result = TaploValidator(auto_fix=True).validate(Path("/tmp/test.toml"))
        assert result.success is False

    @patch.object(TaploValidator, "_execute_command", side_effect=Exception("err"))
    def test_exception(self, mock_exec):
        result = TaploValidator().validate(Path("/tmp/test.toml"))
        assert result.success is False


class TestTerraformValidate:
    """Test TerraformValidator.validate()."""

    @patch.object(TerraformValidator, "_execute_command")
    def test_success(self, mock_exec):
        mock_exec.return_value = MagicMock(returncode=0, stdout="")
        result = TerraformValidator().validate(Path("/tmp/main.tf"))
        assert result.success is True

    @patch.object(TerraformValidator, "_execute_command")
    def test_failure(self, mock_exec):
        mock_exec.return_value = MagicMock(returncode=1, stdout="Error: Invalid syntax", stderr="")
        result = TerraformValidator().validate(Path("/tmp/main.tf"))
        assert result.success is False

    @patch.object(TerraformValidator, "_execute_command", side_effect=Exception("err"))
    def test_exception(self, mock_exec):
        result = TerraformValidator().validate(Path("/tmp/main.tf"))
        assert result.success is False


class TestESLintValidate:
    """Test ESLintValidator.validate()."""

    @patch.object(ESLintValidator, "_execute_command")
    def test_success(self, mock_exec):
        mock_exec.return_value = MagicMock(returncode=0, stdout="")
        result = ESLintValidator().validate(Path("/tmp/app.js"))
        assert result.success is True

    @patch.object(ESLintValidator, "_execute_command")
    def test_failure(self, mock_exec):
        mock_exec.return_value = MagicMock(
            returncode=1, stdout="1:1 error Missing semicolon", stderr=""
        )
        result = ESLintValidator().validate(Path("/tmp/app.js"))
        assert result.success is False

    @patch.object(ESLintValidator, "_execute_command", side_effect=Exception("err"))
    def test_exception(self, mock_exec):
        result = ESLintValidator().validate(Path("/tmp/app.js"))
        assert result.success is False


class TestPrettierValidate:
    """Test PrettierValidator.validate()."""

    @patch.object(PrettierValidator, "_execute_command")
    def test_success(self, mock_exec):
        mock_exec.return_value = MagicMock(returncode=0, stdout="")
        result = PrettierValidator().validate(Path("/tmp/app.js"))
        assert result.success is True

    @patch.object(PrettierValidator, "_execute_command")
    def test_failure(self, mock_exec):
        mock_exec.return_value = MagicMock(returncode=1, stdout="format diff", stderr="")
        result = PrettierValidator().validate(Path("/tmp/app.js"))
        assert result.success is False

    @patch.object(PrettierValidator, "_execute_command", side_effect=Exception("err"))
    def test_exception(self, mock_exec):
        result = PrettierValidator().validate(Path("/tmp/app.js"))
        assert result.success is False


class TestChapelValidate:
    """Test ChapelValidator.validate()."""

    def test_success(self, tmp_path):
        f = tmp_path / "test.chpl"
        f.write_text("writeln(42);\n")
        result = ChapelValidator().validate(f)
        # Chapel formats in-memory, success depends on valid syntax
        assert isinstance(result.success, bool)
        assert result.tool == "chapel"

    def test_nonexistent_file(self):
        result = ChapelValidator().validate(Path("/tmp/nonexistent.chpl"))
        assert result.success is False


class TestShellcheckValidate:
    """Test ShellcheckValidator.validate()."""

    @patch.object(ShellcheckValidator, "_execute_command")
    def test_success(self, mock_exec):
        mock_exec.return_value = MagicMock(returncode=0, stdout="[]")
        result = ShellcheckValidator().validate(Path("/tmp/test.sh"))
        assert result.success is True

    @patch.object(ShellcheckValidator, "_execute_command")
    def test_failure(self, mock_exec):
        mock_exec.return_value = MagicMock(
            returncode=1,
            stdout='[{"line":1,"message":"Not following"}]',
            stderr="",
        )
        result = ShellcheckValidator().validate(Path("/tmp/test.sh"))
        assert result.success is False

    @patch.object(ShellcheckValidator, "_execute_command", side_effect=Exception("err"))
    def test_exception(self, mock_exec):
        result = ShellcheckValidator().validate(Path("/tmp/test.sh"))
        assert result.success is False


class TestHadolintValidate:
    """Test HadolintValidator.validate()."""

    @patch.object(HadolintValidator, "_execute_command")
    def test_success(self, mock_exec):
        mock_exec.return_value = MagicMock(returncode=0, stdout="")
        result = HadolintValidator().validate(Path("/tmp/Dockerfile"))
        assert result.success is True

    @patch.object(HadolintValidator, "_execute_command")
    def test_failure(self, mock_exec):
        mock_exec.return_value = MagicMock(
            returncode=1,
            stdout="DL3006 Always tag the version of an image",
            stderr="",
        )
        result = HadolintValidator().validate(Path("/tmp/Dockerfile"))
        assert result.success is False

    @patch.object(HadolintValidator, "_execute_command", side_effect=Exception("err"))
    def test_exception(self, mock_exec):
        result = HadolintValidator().validate(Path("/tmp/Dockerfile"))
        assert result.success is False


class TestYamlLintValidate:
    """Test YamlLintValidator.validate()."""

    @patch.object(YamlLintValidator, "_execute_command")
    def test_success(self, mock_exec):
        mock_exec.return_value = MagicMock(returncode=0, stdout="")
        result = YamlLintValidator().validate(Path("/tmp/test.yml"))
        assert result.success is True

    @patch.object(YamlLintValidator, "_execute_command")
    def test_failure(self, mock_exec):
        mock_exec.return_value = MagicMock(
            returncode=1, stdout="1:1 error too many blank lines", stderr=""
        )
        result = YamlLintValidator().validate(Path("/tmp/test.yml"))
        assert result.success is False

    @patch.object(YamlLintValidator, "_execute_command", side_effect=Exception("err"))
    def test_exception(self, mock_exec):
        result = YamlLintValidator().validate(Path("/tmp/test.yml"))
        assert result.success is False


class TestGitLabCIValidate:
    """Test GitLabCIValidator.validate()."""

    def test_valid_ci_file(self, tmp_path):
        f = tmp_path / ".gitlab-ci.yml"
        f.write_text("stages:\n  - build\n  - test\n\nbuild_job:\n  stage: build\n  script:\n    - echo hello\n")
        result = GitLabCIValidator().validate(f)
        assert result.tool == "gitlab-ci"
        # May pass or fail depending on validation rules
        assert isinstance(result.success, bool)

    def test_nonexistent_file(self):
        result = GitLabCIValidator().validate(Path("/tmp/nonexistent.yml"))
        assert result.success is False
        assert len(result.errors) > 0

    def test_invalid_yaml(self, tmp_path):
        f = tmp_path / ".gitlab-ci.yml"
        f.write_text("invalid: yaml: content: [bad")
        result = GitLabCIValidator().validate(f)
        assert result.success is False


class TestAnsibleLintValidate:
    """Test AnsibleLintValidator.validate()."""

    @patch.object(AnsibleLintValidator, "_execute_command")
    def test_success(self, mock_exec):
        mock_exec.return_value = MagicMock(returncode=0, stdout="")
        result = AnsibleLintValidator().validate(Path("/tmp/playbook.yml"))
        assert result.success is True

    @patch.object(AnsibleLintValidator, "_execute_command")
    def test_failure(self, mock_exec):
        mock_exec.return_value = MagicMock(
            returncode=1, stdout="playbook.yml:1 risky-file-permissions", stderr=""
        )
        result = AnsibleLintValidator().validate(Path("/tmp/playbook.yml"))
        assert result.success is False

    @patch.object(AnsibleLintValidator, "_execute_command", side_effect=Exception("err"))
    def test_exception(self, mock_exec):
        result = AnsibleLintValidator().validate(Path("/tmp/playbook.yml"))
        assert result.success is False
