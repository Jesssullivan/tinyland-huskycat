"""Tests for the HuskyCatFactory command factory pattern."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from huskycat.core.factory import HuskyCatFactory
from huskycat.core.base import BaseCommand, CommandResult, CommandStatus


class TestFactoryInit:
    """Test factory initialization."""

    def test_default_config_dir(self):
        factory = HuskyCatFactory()
        assert factory.config_dir == Path.home() / ".huskycat"

    def test_custom_config_dir(self, tmp_path):
        factory = HuskyCatFactory(config_dir=tmp_path)
        assert factory.config_dir == tmp_path

    def test_verbose_flag(self):
        factory = HuskyCatFactory(verbose=True)
        assert factory.verbose is True

    def test_commands_registered(self):
        factory = HuskyCatFactory()
        commands = factory.list_commands()
        assert len(commands) >= 10
        assert "validate" in commands
        assert "status" in commands
        assert "clean" in commands
        assert "install" in commands
        assert "setup-hooks" in commands

    def test_all_14_commands_registered(self):
        factory = HuskyCatFactory()
        expected = {
            "validate", "auto-fix", "install", "setup-hooks",
            "update-schemas", "ci-validate", "auto-devops",
            "mcp-server", "bootstrap", "clean", "status",
            "history", "tasks", "audit-config",
        }
        registered = set(factory.list_commands())
        for cmd in expected:
            assert cmd in registered, f"Command '{cmd}' not registered"


class TestCreateCommand:
    """Test command creation."""

    def test_create_validate(self):
        factory = HuskyCatFactory()
        cmd = factory.create_command("validate")
        assert cmd is not None
        assert cmd.name == "validate"

    def test_create_status(self):
        factory = HuskyCatFactory()
        cmd = factory.create_command("status")
        assert cmd is not None
        assert cmd.name == "status"

    def test_create_clean(self):
        factory = HuskyCatFactory()
        cmd = factory.create_command("clean")
        assert cmd is not None

    def test_create_audit_config(self):
        factory = HuskyCatFactory()
        cmd = factory.create_command("audit-config")
        assert cmd is not None

    def test_create_unknown_returns_none(self):
        factory = HuskyCatFactory()
        cmd = factory.create_command("nonexistent-command")
        assert cmd is None

    def test_created_command_inherits_verbose(self):
        factory = HuskyCatFactory(verbose=True)
        cmd = factory.create_command("status")
        assert cmd is not None
        assert cmd.verbose is True

    def test_created_command_inherits_config_dir(self, tmp_path):
        factory = HuskyCatFactory(config_dir=tmp_path)
        cmd = factory.create_command("status")
        assert cmd is not None
        assert cmd.config_dir == tmp_path


class TestExecuteCommand:
    """Test command execution through factory."""

    def test_execute_unknown_command(self):
        factory = HuskyCatFactory()
        result = factory.execute_command("nonexistent")
        assert result.status == CommandStatus.FAILED
        assert "not found" in result.message.lower() or "Unknown" in result.message

    def test_execute_returns_command_result(self):
        factory = HuskyCatFactory()
        # status command should succeed
        result = factory.execute_command("status")
        assert isinstance(result, CommandResult)
        assert result.status in (
            CommandStatus.SUCCESS,
            CommandStatus.FAILED,
            CommandStatus.WARNING,
        )


class TestGetCommandInfo:
    """Test command info retrieval."""

    def test_known_command(self):
        factory = HuskyCatFactory()
        info = factory.get_command_info("validate")
        assert info is not None
        assert "name" in info
        assert "description" in info
        assert "module" in info
        assert "class" in info
        assert info["name"] == "validate"

    def test_unknown_command(self):
        factory = HuskyCatFactory()
        info = factory.get_command_info("nonexistent")
        assert info is None

    def test_all_commands_have_info(self):
        factory = HuskyCatFactory()
        for cmd_name in factory.list_commands():
            info = factory.get_command_info(cmd_name)
            assert info is not None, f"No info for command '{cmd_name}'"
            assert info["name"], f"Empty name for command '{cmd_name}'"
            assert info["description"], f"Empty description for command '{cmd_name}'"


class TestBaseCommand:
    """Test BaseCommand abstract class."""

    def test_command_result_defaults(self):
        result = CommandResult(status=CommandStatus.SUCCESS, message="OK")
        assert result.errors == []
        assert result.warnings == []
        assert result.data is None

    def test_command_result_with_errors(self):
        result = CommandResult(
            status=CommandStatus.FAILED,
            message="Failed",
            errors=["Error 1", "Error 2"],
        )
        assert len(result.errors) == 2

    def test_command_status_enum(self):
        assert CommandStatus.SUCCESS.value == "success"
        assert CommandStatus.FAILED.value == "failed"
        assert CommandStatus.WARNING.value == "warning"
        assert CommandStatus.SKIPPED.value == "skipped"

    def test_validate_prerequisites_default(self):
        """BaseCommand.validate_prerequisites returns success by default."""
        factory = HuskyCatFactory()
        cmd = factory.create_command("status")
        result = cmd.validate_prerequisites()
        assert result.status == CommandStatus.SUCCESS
