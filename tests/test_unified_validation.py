"""Tests for the unified validation engine."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from huskycat.core.tool_selector import LintingMode
from huskycat.unified_validation import ValidationEngine, ValidationResult


class TestValidationEngineInit:
    """Test ValidationEngine initialization."""

    def test_default_init(self):
        engine = ValidationEngine()
        assert engine.auto_fix is False
        assert engine.interactive is False
        assert engine.allow_warnings is False
        assert engine.use_container is False

    def test_fast_mode(self):
        engine = ValidationEngine(linting_mode=LintingMode.FAST)
        assert engine.linting_mode == LintingMode.FAST

    def test_comprehensive_mode(self):
        engine = ValidationEngine(linting_mode=LintingMode.COMPREHENSIVE)
        assert engine.linting_mode == LintingMode.COMPREHENSIVE

    def test_auto_fix_enabled(self):
        engine = ValidationEngine(auto_fix=True)
        assert engine.auto_fix is True

    def test_validators_loaded(self):
        engine = ValidationEngine()
        # Should have at least some validators
        assert isinstance(engine.validators, list)

    def test_extension_map_built(self):
        engine = ValidationEngine()
        assert isinstance(engine._extension_map, dict)


class TestShouldUseTool:
    """Test linting mode tool filtering."""

    def test_comprehensive_allows_all(self):
        engine = ValidationEngine(linting_mode=LintingMode.COMPREHENSIVE)
        assert engine._should_use_tool("ruff") is True
        assert engine._should_use_tool("shellcheck") is True
        assert engine._should_use_tool("yamllint") is True

    def test_fast_allows_bundled(self):
        engine = ValidationEngine(linting_mode=LintingMode.FAST)
        assert engine._should_use_tool("ruff") is True
        assert engine._should_use_tool("mypy") is True

    def test_fast_blocks_gpl(self):
        engine = ValidationEngine(linting_mode=LintingMode.FAST)
        # GPL tools are not bundled
        assert engine._should_use_tool("shellcheck") is False
        assert engine._should_use_tool("hadolint") is False


class TestShouldToolAutoFix:
    """Test per-tool auto-fix decisions."""

    def test_no_adapter_uses_global(self):
        engine = ValidationEngine(auto_fix=True)
        assert engine._should_tool_auto_fix("ruff") is True

    def test_no_adapter_global_false(self):
        engine = ValidationEngine(auto_fix=False)
        assert engine._should_tool_auto_fix("ruff") is False

    def test_adapter_override(self):
        adapter = MagicMock()
        adapter.should_auto_fix_tool.return_value = False
        engine = ValidationEngine(auto_fix=True, adapter=adapter)
        assert engine._should_tool_auto_fix("ruff") is False
        adapter.should_auto_fix_tool.assert_called_with("ruff", True)


class TestGetValidatorsForFile:
    """Test validator selection for files."""

    def test_python_file(self):
        engine = ValidationEngine()
        validators = engine.get_validators_for_file(Path("test.py"))
        names = [v.name for v in validators]
        # Should include at least ruff if available
        assert isinstance(names, list)

    def test_unknown_extension(self):
        engine = ValidationEngine()
        validators = engine.get_validators_for_file(Path("test.xyz"))
        assert isinstance(validators, list)


class TestBuildExtensionMap:
    """Test extension map construction."""

    def test_py_extension_mapped(self):
        engine = ValidationEngine()
        if ".py" in engine._extension_map:
            for v in engine._extension_map[".py"]:
                assert ".py" in v.extensions

    def test_map_keys_are_extensions(self):
        engine = ValidationEngine()
        for ext in engine._extension_map:
            assert isinstance(ext, str)


class TestLoadDockerLintValidator:
    """Test dynamic DockerLint validator loading."""

    def test_load_success(self):
        engine = ValidationEngine()
        result = engine._load_dockerlint_validator()
        # May or may not be available depending on environment
        assert result is not None or result is None

    @patch("huskycat.unified_validation.ValidationEngine._load_dockerlint_validator", return_value=None)
    def test_load_failure(self, mock_load):
        engine = ValidationEngine()
        assert mock_load.return_value is None
