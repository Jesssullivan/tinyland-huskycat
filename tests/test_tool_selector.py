"""Tests for tool_selector module - license-compliant tool selection."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from huskycat.core.tool_selector import (
    COMPREHENSIVE_DOCKERFILE_TOOLS,
    COMPREHENSIVE_PYTHON_TOOLS,
    COMPREHENSIVE_SHELL_TOOLS,
    COMPREHENSIVE_YAML_TOOLS,
    FAST_DOCKERFILE_TOOLS,
    FAST_PYTHON_TOOLS,
    FAST_SHELL_TOOLS,
    FAST_YAML_TOOLS,
    TOOL_REGISTRY,
    LintingMode,
    ToolInfo,
    ToolLicense,
    detect_file_types,
    get_bundled_tools,
    get_gpl_tools,
    get_mode_from_env,
    get_tool_info,
    get_tools_for_file_type,
    get_tools_for_mode,
    is_tool_bundled,
)


class TestLintingModeEnum:
    """Test LintingMode enum."""

    def test_fast_value(self):
        assert LintingMode.FAST.value == "fast"

    def test_comprehensive_value(self):
        assert LintingMode.COMPREHENSIVE.value == "comprehensive"


class TestToolLicenseEnum:
    """Test ToolLicense enum."""

    def test_license_values(self):
        assert ToolLicense.MIT.value == "mit"
        assert ToolLicense.APACHE.value == "apache"
        assert ToolLicense.GPL.value == "gpl"


class TestToolInfo:
    """Test ToolInfo dataclass."""

    def test_auto_validator_class(self):
        info = ToolInfo("my-tool", ToolLicense.MIT, "desc", {"python"})
        assert info.validator_class == "MyToolValidator"

    def test_explicit_validator_class(self):
        info = ToolInfo(
            "ruff", ToolLicense.MIT, "desc", {"python"},
            validator_class="CustomValidator",
        )
        assert info.validator_class == "CustomValidator"

    def test_bundled_default(self):
        info = ToolInfo("test", ToolLicense.MIT, "desc", {"python"})
        assert info.bundled is True


class TestToolRegistry:
    """Test the TOOL_REGISTRY constant."""

    def test_ruff_in_registry(self):
        assert "ruff" in TOOL_REGISTRY
        assert TOOL_REGISTRY["ruff"].license == ToolLicense.MIT

    def test_shellcheck_is_gpl(self):
        assert "shellcheck" in TOOL_REGISTRY
        assert TOOL_REGISTRY["shellcheck"].license == ToolLicense.GPL
        assert TOOL_REGISTRY["shellcheck"].bundled is False

    def test_hadolint_is_gpl(self):
        assert "hadolint" in TOOL_REGISTRY
        assert TOOL_REGISTRY["hadolint"].license == ToolLicense.GPL

    def test_yamllint_is_gpl(self):
        assert "yamllint" in TOOL_REGISTRY
        assert TOOL_REGISTRY["yamllint"].license == ToolLicense.GPL

    def test_bandit_is_apache(self):
        assert "bandit" in TOOL_REGISTRY
        assert TOOL_REGISTRY["bandit"].license == ToolLicense.APACHE

    def test_all_tools_have_file_types(self):
        for name, info in TOOL_REGISTRY.items():
            assert len(info.file_types) > 0, f"Tool {name} has no file types"

    def test_registry_has_expected_count(self):
        assert len(TOOL_REGISTRY) >= 16


class TestGetToolsForMode:
    """Test tool selection based on linting mode and file types."""

    def test_fast_mode_excludes_gpl(self):
        tools = get_tools_for_mode(LintingMode.FAST, {"python", "shell", "yaml"})
        assert "shellcheck" not in tools
        assert "hadolint" not in tools
        assert "yamllint" not in tools

    def test_comprehensive_mode_includes_gpl(self):
        tools = get_tools_for_mode(
            LintingMode.COMPREHENSIVE, {"python", "shell", "yaml"}
        )
        assert "shellcheck" in tools
        assert "yamllint" in tools

    def test_python_tools_selected(self):
        tools = get_tools_for_mode(LintingMode.FAST, {"python"})
        assert "ruff" in tools
        assert "mypy" in tools
        assert "python-black" in tools

    def test_no_matching_file_types(self):
        tools = get_tools_for_mode(LintingMode.FAST, {"unknown_type"})
        assert len(tools) == 0

    def test_ci_excluded_by_default(self):
        tools = get_tools_for_mode(LintingMode.FAST, {"yaml"})
        assert "gitlab-ci" not in tools

    def test_ci_included_when_requested(self):
        tools = get_tools_for_mode(LintingMode.FAST, {"yaml"}, include_ci=True)
        assert "gitlab-ci" in tools


class TestGetBundledTools:
    """Test bundled tool set."""

    def test_includes_ruff(self):
        assert "ruff" in get_bundled_tools()

    def test_includes_mypy(self):
        assert "mypy" in get_bundled_tools()

    def test_excludes_gpl(self):
        bundled = get_bundled_tools()
        assert "shellcheck" not in bundled
        assert "hadolint" not in bundled
        assert "yamllint" not in bundled

    def test_only_bundled_and_non_gpl(self):
        for tool_name in get_bundled_tools():
            info = TOOL_REGISTRY[tool_name]
            assert info.bundled is True
            assert info.license != ToolLicense.GPL


class TestGetGplTools:
    """Test GPL tool set."""

    def test_includes_shellcheck(self):
        assert "shellcheck" in get_gpl_tools()

    def test_includes_hadolint(self):
        assert "hadolint" in get_gpl_tools()

    def test_includes_yamllint(self):
        assert "yamllint" in get_gpl_tools()

    def test_excludes_non_gpl(self):
        gpl = get_gpl_tools()
        assert "ruff" not in gpl
        assert "mypy" not in gpl


class TestDetectFileTypes:
    """Test file type detection from paths."""

    def test_python_file(self):
        types = detect_file_types([Path("test.py")])
        assert "python" in types

    def test_pyi_stub(self):
        types = detect_file_types([Path("types.pyi")])
        assert "python" in types

    def test_javascript(self):
        types = detect_file_types([Path("app.js")])
        assert "javascript" in types

    def test_typescript(self):
        types = detect_file_types([Path("app.ts")])
        assert "typescript" in types

    def test_shell_script(self):
        types = detect_file_types([Path("script.sh")])
        assert "shell" in types

    def test_yaml_file(self):
        types = detect_file_types([Path("config.yml")])
        assert "yaml" in types

    def test_toml_file(self):
        types = detect_file_types([Path("pyproject.toml")])
        assert "toml" in types

    def test_terraform_file(self):
        types = detect_file_types([Path("main.tf")])
        assert "terraform" in types

    def test_chapel_file(self):
        types = detect_file_types([Path("program.chpl")])
        assert "chapel" in types

    def test_multiple_types(self):
        types = detect_file_types([
            Path("app.py"),
            Path("script.sh"),
            Path("config.yml"),
        ])
        assert "python" in types
        assert "shell" in types
        assert "yaml" in types

    def test_empty_list(self):
        types = detect_file_types([])
        assert len(types) == 0

    def test_ansible_detection(self):
        types = detect_file_types([Path("playbooks/main.yml")])
        assert "ansible" in types
        assert "yaml" in types

    def test_roles_directory_ansible(self):
        types = detect_file_types([Path("roles/webserver/tasks/main.yml")])
        assert "ansible" in types

    def test_dockerfile_filename(self):
        types = detect_file_types([Path("Dockerfile")])
        assert "dockerfile" in types

    def test_containerfile_filename(self):
        types = detect_file_types([Path("Containerfile")])
        assert "dockerfile" in types


class TestGetModeFromEnv:
    """Test linting mode detection from environment."""

    @patch.dict(os.environ, {"HUSKYCAT_LINTING_MODE": "fast"}, clear=False)
    def test_explicit_fast(self):
        assert get_mode_from_env() == LintingMode.FAST

    @patch.dict(os.environ, {"HUSKYCAT_LINTING_MODE": "comprehensive"}, clear=False)
    def test_explicit_comprehensive(self):
        assert get_mode_from_env() == LintingMode.COMPREHENSIVE

    @patch.dict(os.environ, {"HUSKYCAT_MODE": "git_hooks"}, clear=False)
    def test_infer_from_git_hooks(self):
        with patch.dict(os.environ, {"HUSKYCAT_LINTING_MODE": ""}, clear=False):
            assert get_mode_from_env() == LintingMode.FAST

    @patch.dict(os.environ, {"HUSKYCAT_MODE": "ci"}, clear=False)
    def test_infer_from_ci(self):
        with patch.dict(os.environ, {"HUSKYCAT_LINTING_MODE": ""}, clear=False):
            assert get_mode_from_env() == LintingMode.COMPREHENSIVE

    @patch.dict(os.environ, {"HUSKYCAT_MODE": "pipeline"}, clear=False)
    def test_infer_from_pipeline(self):
        with patch.dict(os.environ, {"HUSKYCAT_LINTING_MODE": ""}, clear=False):
            assert get_mode_from_env() == LintingMode.COMPREHENSIVE

    @patch.dict(os.environ, {}, clear=True)
    @patch("os.path.exists", return_value=False)
    def test_default_is_fast(self, mock_exists):
        assert get_mode_from_env() == LintingMode.FAST


class TestGetToolInfo:
    """Test get_tool_info function."""

    def test_known_tool(self):
        info = get_tool_info("ruff")
        assert info.name == "ruff"
        assert info.license == ToolLicense.MIT

    def test_unknown_tool_raises(self):
        with pytest.raises(KeyError, match="not found"):
            get_tool_info("nonexistent-tool")


class TestIsToolBundled:
    """Test is_tool_bundled function."""

    def test_bundled_tool(self):
        assert is_tool_bundled("ruff") is True

    def test_non_bundled_tool(self):
        assert is_tool_bundled("shellcheck") is False

    def test_unknown_tool(self):
        assert is_tool_bundled("nonexistent") is False


class TestGetToolsForFileType:
    """Test get_tools_for_file_type function."""

    def test_python_fast(self):
        tools = get_tools_for_file_type("python", LintingMode.FAST)
        assert "ruff" in tools
        assert "mypy" in tools

    def test_python_comprehensive(self):
        tools = get_tools_for_file_type("python", LintingMode.COMPREHENSIVE)
        assert "ruff" in tools
        assert "bandit" in tools

    def test_shell_fast_empty(self):
        tools = get_tools_for_file_type("shell", LintingMode.FAST)
        assert "shellcheck" not in tools

    def test_shell_comprehensive(self):
        tools = get_tools_for_file_type("shell", LintingMode.COMPREHENSIVE)
        assert "shellcheck" in tools

    def test_unknown_type(self):
        tools = get_tools_for_file_type("brainfuck", LintingMode.FAST)
        assert len(tools) == 0

    def test_tools_are_sorted(self):
        tools = get_tools_for_file_type("python", LintingMode.FAST)
        # python-black should come before ruff (formatters first)
        if "python-black" in tools and "ruff" in tools:
            assert tools.index("python-black") < tools.index("ruff")


class TestConvenienceSets:
    """Test the convenience tool set constants."""

    def test_fast_python(self):
        assert "ruff" in FAST_PYTHON_TOOLS
        assert "mypy" in FAST_PYTHON_TOOLS
        assert "python-black" in FAST_PYTHON_TOOLS
        assert "flake8" in FAST_PYTHON_TOOLS

    def test_comprehensive_python_superset(self):
        assert FAST_PYTHON_TOOLS.issubset(COMPREHENSIVE_PYTHON_TOOLS)
        assert "bandit" in COMPREHENSIVE_PYTHON_TOOLS

    def test_gpl_yaml(self):
        assert "yamllint" in COMPREHENSIVE_YAML_TOOLS
        assert len(FAST_YAML_TOOLS) == 0

    def test_gpl_shell(self):
        assert "shellcheck" in COMPREHENSIVE_SHELL_TOOLS
        assert len(FAST_SHELL_TOOLS) == 0

    def test_gpl_dockerfile(self):
        assert "hadolint" in COMPREHENSIVE_DOCKERFILE_TOOLS
        assert len(FAST_DOCKERFILE_TOOLS) == 0
