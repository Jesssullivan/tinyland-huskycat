"""Tests for the triage engine core logic."""

import datetime
from unittest.mock import MagicMock, patch

import pytest

from huskycat.core.triage.engine import (
    BRANCH_ISSUE_PATTERNS,
    BRANCH_PREFIX_LABELS,
    COMMIT_ISSUE_PATTERNS,
    DEFAULT_PATH_LABELS,
    TriageConfig,
    TriageEngine,
    TriageResult,
)
from huskycat.core.triage.platform import (
    IssueRef,
    MRRef,
    PlatformType,
    TriageAction,
)


class TestTriageConfig:
    """Test TriageConfig dataclass."""

    def test_default_values(self):
        config = TriageConfig()
        assert config.enabled is True
        assert config.auto_label is True
        assert config.auto_iteration is True
        assert "gitlab" in config.platforms
        assert "github" in config.platforms
        assert "codeberg" in config.platforms
        assert config.dry_run is False
        assert config.iteration_format == "%Y-W%V"

    def test_from_dict_full(self):
        data = {
            "triage": {
                "enabled": False,
                "auto_label": False,
                "auto_iteration": False,
                "platforms": ["gitlab"],
                "dry_run": True,
                "iteration_format": "%Y-S%V",
            }
        }
        config = TriageConfig.from_dict(data)
        assert config.enabled is False
        assert config.auto_label is False
        assert config.auto_iteration is False
        assert config.platforms == ["gitlab"]
        assert config.dry_run is True
        assert config.iteration_format == "%Y-S%V"

    def test_from_dict_defaults(self):
        config = TriageConfig.from_dict({})
        assert config.enabled is True
        assert config.auto_label is True

    def test_from_dict_nested_triage_key(self):
        data = {"triage": {"dry_run": True}}
        config = TriageConfig.from_dict(data)
        assert config.dry_run is True

    def test_from_dict_flat(self):
        data = {"enabled": False, "auto_label": False}
        config = TriageConfig.from_dict(data)
        assert config.enabled is False
        assert config.auto_label is False

    def test_path_labels_default(self):
        config = TriageConfig()
        assert "src/**/*.py" in config.path_labels
        assert "docs/**" in config.path_labels

    def test_branch_prefix_labels_default(self):
        config = TriageConfig()
        assert "feat/" in config.branch_prefix_labels
        assert config.branch_prefix_labels["fix/"] == "bug"


class TestTriageResult:
    """Test TriageResult dataclass."""

    def test_empty_result_success(self):
        result = TriageResult()
        assert result.success is True

    def test_result_with_successful_actions(self):
        result = TriageResult(
            actions=[
                TriageAction("add_label", "issue", 1, success=True),
                TriageAction("set_iteration", "issue", 1, success=True),
            ]
        )
        assert result.success is True

    def test_result_with_failed_action(self):
        result = TriageResult(
            actions=[
                TriageAction("add_label", "issue", 1, success=True),
                TriageAction("set_iteration", "issue", 1, success=False),
            ]
        )
        assert result.success is False

    def test_summary_empty(self):
        result = TriageResult()
        assert result.summary() == "No triage actions needed"

    def test_summary_with_issue(self):
        result = TriageResult(
            issue_ref=IssueRef(number=42, platform=PlatformType.GITLAB)
        )
        assert "Issue: #42" in result.summary()

    def test_summary_with_mr(self):
        result = TriageResult(
            mr_ref=MRRef(number=10, platform=PlatformType.GITLAB)
        )
        assert "MR: !10" in result.summary()

    def test_summary_with_labels(self):
        result = TriageResult(labels_inferred=["bug", "python"])
        summary = result.summary()
        assert "Labels:" in summary
        assert "bug" in summary
        assert "python" in summary

    def test_summary_with_iteration(self):
        result = TriageResult(iteration="2026-W06")
        assert "Iteration: 2026-W06" in result.summary()

    def test_summary_dry_run(self):
        result = TriageResult(
            issue_ref=IssueRef(number=1, platform=PlatformType.GITLAB),
            dry_run=True,
        )
        assert "[DRY RUN]" in result.summary()


class TestBranchIssueExtraction:
    """Test branch name → issue number extraction."""

    def test_feat_with_issue(self):
        engine = TriageEngine()
        assert engine._extract_issue_from_branch("feat/123-add-login") == 123

    def test_fix_with_issue(self):
        engine = TriageEngine()
        assert engine._extract_issue_from_branch("fix/456-crash") == 456

    def test_sid_branch(self):
        engine = TriageEngine()
        assert engine._extract_issue_from_branch("sid/42-feature") == 42

    def test_mr_branch(self):
        engine = TriageEngine()
        assert engine._extract_issue_from_branch("mr-99") == 99

    def test_no_issue(self):
        engine = TriageEngine()
        assert engine._extract_issue_from_branch("feature-no-number") is None

    def test_gl_prefix(self):
        engine = TriageEngine()
        assert engine._extract_issue_from_branch("feat/GL-789") == 789

    def test_gh_prefix(self):
        engine = TriageEngine()
        assert engine._extract_issue_from_branch("fix/GH-321") == 321

    def test_chore_branch(self):
        engine = TriageEngine()
        assert engine._extract_issue_from_branch("chore/100-cleanup") == 100


class TestCommitIssueExtraction:
    """Test commit message → issue number extraction."""

    def test_closes_hash(self):
        engine = TriageEngine()
        assert engine._extract_issue_from_commit("Closes #42") == 42

    def test_fixes_hash(self):
        engine = TriageEngine()
        assert engine._extract_issue_from_commit("Fixes #99") == 99

    def test_refs_hash(self):
        engine = TriageEngine()
        assert engine._extract_issue_from_commit("Refs #7") == 7

    def test_case_insensitive(self):
        engine = TriageEngine()
        assert engine._extract_issue_from_commit("closes #10") == 10
        assert engine._extract_issue_from_commit("FIXES #20") == 20

    def test_no_reference(self):
        engine = TriageEngine()
        assert engine._extract_issue_from_commit("Just a regular commit") is None


class TestLabelInference:
    """Test label inference from branch prefix and file paths."""

    def test_feat_prefix(self):
        engine = TriageEngine()
        labels = engine._infer_labels("feat/new-feature")
        assert "feature" in labels

    def test_fix_prefix(self):
        engine = TriageEngine()
        labels = engine._infer_labels("fix/crash-bug")
        assert "bug" in labels

    def test_docs_prefix(self):
        engine = TriageEngine()
        labels = engine._infer_labels("docs/update-readme")
        assert "documentation" in labels

    def test_ci_prefix(self):
        engine = TriageEngine()
        labels = engine._infer_labels("ci/pipeline-fix")
        assert "ci/cd" in labels

    @patch.object(TriageEngine, "_get_changed_files")
    def test_python_files_label(self, mock_files):
        mock_files.return_value = ["src/huskycat/core/engine.py"]
        engine = TriageEngine()
        labels = engine._infer_labels("feat/new-feature")
        assert "python" in labels

    @patch.object(TriageEngine, "_get_changed_files")
    def test_nix_files_label(self, mock_files):
        mock_files.return_value = ["flake.nix"]
        engine = TriageEngine()
        labels = engine._infer_labels("chore/nix-update")
        assert "nix" in labels
        assert "infrastructure" in labels

    @patch.object(TriageEngine, "_get_changed_files")
    def test_ci_files_label(self, mock_files):
        mock_files.return_value = [".gitlab-ci.yml"]
        engine = TriageEngine()
        labels = engine._infer_labels("ci/pipeline")
        assert "ci/cd" in labels

    @patch.object(TriageEngine, "_get_changed_files")
    def test_docs_files_label(self, mock_files):
        mock_files.return_value = ["docs/installation.md"]
        engine = TriageEngine()
        labels = engine._infer_labels("docs/install")
        assert "documentation" in labels


class TestGlobMatching:
    """Test the simple glob matching in TriageEngine."""

    def test_double_star_suffix(self):
        engine = TriageEngine()
        assert engine._match_glob("src/huskycat/core/engine.py", "src/**/*.py")

    def test_double_star_no_match(self):
        engine = TriageEngine()
        assert not engine._match_glob("src/huskycat/core/engine.py", "docs/**/*.md")

    def test_simple_pattern(self):
        engine = TriageEngine()
        assert engine._match_glob("flake.nix", "*.nix")

    def test_simple_no_match(self):
        engine = TriageEngine()
        assert not engine._match_glob("flake.nix", "*.py")

    def test_double_star_prefix_only(self):
        engine = TriageEngine()
        assert engine._match_glob("tests/test_foo.py", "tests/**")

    def test_double_star_any_python(self):
        engine = TriageEngine()
        assert engine._match_glob("deep/nested/file.py", "**/*.py")


class TestCurrentIteration:
    """Test iteration/sprint name generation."""

    def test_default_format(self):
        engine = TriageEngine()
        iteration = engine._get_current_iteration()
        # Should be in format YYYY-WXX
        assert len(iteration) >= 7
        assert iteration.startswith("20")
        assert "-W" in iteration

    def test_custom_format(self):
        config = TriageConfig(iteration_format="%Y-Sprint-%V")
        engine = TriageEngine(config=config)
        iteration = engine._get_current_iteration()
        assert "Sprint" in iteration


class TestTriageEnginePostCommit:
    """Test the full post-commit triage flow."""

    @patch.object(TriageEngine, "_get_current_branch", return_value="")
    def test_skip_on_main_branch(self, mock_branch):
        engine = TriageEngine()
        result = engine.run_post_commit()
        assert result.success is True
        assert not result.issue_ref

    def test_disabled_config(self):
        config = TriageConfig(enabled=False)
        engine = TriageEngine(config=config)
        result = engine.run_post_commit()
        assert result.success is True

    @patch.object(TriageEngine, "_get_current_branch", return_value="feat/42-login")
    @patch.object(TriageEngine, "_get_changed_files", return_value=["src/app.py"])
    def test_dry_run_no_api_calls(self, mock_files, mock_branch):
        config = TriageConfig(dry_run=True)
        engine = TriageEngine(config=config)
        # Mock the adapter so platform detection doesn't hit real git
        mock_adapter = MagicMock()
        mock_adapter.check_cli_available.return_value = True
        mock_adapter.find_mr_by_branch.return_value = None
        engine._adapter = mock_adapter
        engine._platform = PlatformType.GITLAB

        result = engine.run_post_commit()
        assert result.dry_run is True
        assert result.issue_ref is not None
        assert result.issue_ref.number == 42
        assert "feature" in result.labels_inferred
        assert len(result.actions) == 0  # dry_run skips apply

    @patch.object(TriageEngine, "_get_current_branch", return_value="fix/99-crash")
    @patch.object(TriageEngine, "_get_changed_files", return_value=[])
    def test_full_flow_with_mock_adapter(self, mock_files, mock_branch):
        config = TriageConfig(dry_run=False)
        engine = TriageEngine(config=config)

        mock_adapter = MagicMock()
        mock_adapter.check_cli_available.return_value = True
        mock_adapter.find_mr_by_branch.return_value = MRRef(
            number=5, platform=PlatformType.GITLAB, source_branch="fix/99-crash"
        )
        mock_adapter.add_labels.return_value = TriageAction(
            "add_label", "mr", 5, success=True
        )
        mock_adapter.set_iteration.return_value = TriageAction(
            "set_iteration", "mr", 5, success=True
        )
        engine._adapter = mock_adapter
        engine._platform = PlatformType.GITLAB

        result = engine.run_post_commit()
        assert result.issue_ref.number == 99
        assert result.mr_ref.number == 5
        assert "bug" in result.labels_inferred
        assert len(result.actions) > 0

    def test_no_adapter_available(self):
        engine = TriageEngine()
        engine._adapter = None  # Force no adapter
        engine._platform = PlatformType.UNKNOWN

        result = engine.run_post_commit()
        assert result.success is True
        assert not result.issue_ref
