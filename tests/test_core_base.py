"""Tests for core base module - BaseCommand, CommandResult, CommandStatus."""

from pathlib import Path

import pytest

from huskycat.core.base import BaseCommand, CommandResult, CommandStatus


class TestCommandStatus:
    """Test CommandStatus enum."""

    def test_all_statuses(self):
        assert CommandStatus.SUCCESS.value == "success"
        assert CommandStatus.FAILED.value == "failed"
        assert CommandStatus.WARNING.value == "warning"
        assert CommandStatus.SKIPPED.value == "skipped"

    def test_enum_members(self):
        members = list(CommandStatus)
        assert len(members) == 4


class TestCommandResult:
    """Test CommandResult dataclass."""

    def test_minimal_result(self):
        result = CommandResult(status=CommandStatus.SUCCESS, message="OK")
        assert result.status == CommandStatus.SUCCESS
        assert result.message == "OK"
        assert result.data is None
        assert result.errors == []
        assert result.warnings == []

    def test_result_with_data(self):
        result = CommandResult(
            status=CommandStatus.SUCCESS,
            message="Done",
            data={"count": 5, "files": ["a.py"]},
        )
        assert result.data["count"] == 5
        assert len(result.data["files"]) == 1

    def test_result_with_errors(self):
        result = CommandResult(
            status=CommandStatus.FAILED,
            message="Failed",
            errors=["Error 1", "Error 2"],
        )
        assert len(result.errors) == 2
        assert "Error 1" in result.errors

    def test_result_with_warnings(self):
        result = CommandResult(
            status=CommandStatus.WARNING,
            message="Warnings found",
            warnings=["Warning 1"],
        )
        assert len(result.warnings) == 1

    def test_post_init_none_errors(self):
        """Ensure None errors/warnings are converted to empty lists."""
        result = CommandResult(
            status=CommandStatus.SUCCESS,
            message="OK",
            errors=None,
            warnings=None,
        )
        assert result.errors == []
        assert result.warnings == []

    def test_result_preserves_explicit_lists(self):
        result = CommandResult(
            status=CommandStatus.FAILED,
            message="err",
            errors=["a"],
            warnings=["b"],
        )
        assert result.errors == ["a"]
        assert result.warnings == ["b"]


class TestBaseCommandAbstract:
    """Test that BaseCommand is properly abstract."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseCommand()

    def test_subclass_must_implement_execute(self):
        class IncompleteCommand(BaseCommand):
            @property
            def name(self):
                return "incomplete"

            @property
            def description(self):
                return "Incomplete"

        with pytest.raises(TypeError):
            IncompleteCommand()

    def test_concrete_subclass(self, tmp_path):
        class TestCommand(BaseCommand):
            @property
            def name(self):
                return "test"

            @property
            def description(self):
                return "Test command"

            def execute(self, *args, **kwargs):
                return CommandResult(
                    status=CommandStatus.SUCCESS, message="Test passed"
                )

        cmd = TestCommand(config_dir=tmp_path)
        assert cmd.name == "test"
        assert cmd.description == "Test command"
        result = cmd.execute()
        assert result.status == CommandStatus.SUCCESS

    def test_validate_prerequisites_default(self, tmp_path):
        class TestCommand(BaseCommand):
            @property
            def name(self):
                return "test"

            @property
            def description(self):
                return "Test"

            def execute(self, *args, **kwargs):
                return CommandResult(status=CommandStatus.SUCCESS, message="OK")

        cmd = TestCommand(config_dir=tmp_path)
        result = cmd.validate_prerequisites()
        assert result.status == CommandStatus.SUCCESS

    def test_log_verbose(self, tmp_path, capsys):
        class TestCommand(BaseCommand):
            @property
            def name(self):
                return "test"

            @property
            def description(self):
                return "Test"

            def execute(self, *args, **kwargs):
                return CommandResult(status=CommandStatus.SUCCESS, message="OK")

        cmd = TestCommand(config_dir=tmp_path, verbose=True)
        cmd.log("Hello")
        captured = capsys.readouterr()
        assert "Hello" in captured.out

    def test_log_not_verbose(self, tmp_path, capsys):
        class TestCommand(BaseCommand):
            @property
            def name(self):
                return "test"

            @property
            def description(self):
                return "Test"

            def execute(self, *args, **kwargs):
                return CommandResult(status=CommandStatus.SUCCESS, message="OK")

        cmd = TestCommand(config_dir=tmp_path, verbose=False)
        cmd.log("Silent")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_config_dir_created(self, tmp_path):
        config_dir = tmp_path / "huskycat_test_config"

        class TestCommand(BaseCommand):
            @property
            def name(self):
                return "test"

            @property
            def description(self):
                return "Test"

            def execute(self, *args, **kwargs):
                return CommandResult(status=CommandStatus.SUCCESS, message="OK")

        cmd = TestCommand(config_dir=config_dir)
        assert config_dir.exists()
