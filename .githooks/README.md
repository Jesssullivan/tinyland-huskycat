# HuskyCat Git Hooks

This directory contains git-tracked hooks for the HuskyCat repository. These hooks enforce code quality standards and are an essential part of the development workflow.

## Prerequisites

**UV virtual environment MUST be active for development in this repository.**

```bash
# First-time setup
uv sync --dev

# Verify setup
uv run python --version
uv run black --version
```

## Setup

Configure git to use these tracked hooks:

```bash
# One-time setup (or run: npm run hooks:install)
git config core.hooksPath .githooks
```

This is also done automatically by `npm install` (via postinstall script).

## Hook Flow Diagram

```
                              GIT WORKFLOW
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           git add <files>                               │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          git commit -m "..."                            │
│                                  │                                      │
│                                  ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                        PRE-COMMIT HOOK                            │  │
│  │                                                                   │  │
│  │   1. Verify UV venv active                                        │  │
│  │   2. Get staged Python files                                      │  │
│  │   3. Run Black (format check)                                     │  │
│  │      └── If fail: prompt auto-fix? → apply & re-stage             │  │
│  │   4. Run Ruff (lint check)                                        │  │
│  │      └── If fail: prompt auto-fix? → apply & re-stage             │  │
│  │   5. Run Flake8 (additional lint)                                 │  │
│  │      └── If fail: manual fix required                             │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                  │                                      │
│                                  ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                        COMMIT-MSG HOOK                            │  │
│  │                                                                   │  │
│  │   Validate conventional commit format:                            │  │
│  │   <type>(<scope>): <description>                                  │  │
│  │                                                                   │  │
│  │   Types: feat|fix|docs|style|refactor|test|chore|perf|ci|build    │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                  │                                      │
│                                  ▼                                      │
│                           COMMIT CREATED                                │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              git push                                   │
│                                  │                                      │
│                                  ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                         PRE-PUSH HOOK                             │  │
│  │                                                                   │  │
│  │   1. Verify UV venv active                                        │  │
│  │   2. Black --check src/ tests/  (full codebase)                   │  │
│  │   3. Ruff check src/ tests/     (full codebase)                   │  │
│  │   4. Flake8 src/ tests/         (full codebase)                   │  │
│  │   5. glab ci lint .gitlab-ci.yml (if glab available)              │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                  │                                      │
│                                  ▼                                      │
│                            PUSH TO REMOTE                               │
└─────────────────────────────────────────────────────────────────────────┘
```

## Hooks Overview

| Hook | Trigger | What it does |
|------|---------|--------------|
| `pre-commit` | Before commit is created | Validates staged Python files with Black, Ruff, Flake8 |
| `commit-msg` | After commit message entered | Validates conventional commit format |
| `pre-push` | Before push to remote | Full codebase validation + CI config check |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SKIP_HOOKS` | `0` | Set to `1` to skip all hooks |
| `HUSKYCAT_SKIP_HOOKS` | `0` | Alternative skip variable |
| `HUSKYCAT_AUTO_APPROVE` | `0` | Set to `1` to auto-approve all fixes |
| `AUTO_FIX` | `0` | Alternative auto-approve variable |

## Usage Examples

### Normal workflow
```bash
git add src/myfile.py
git commit -m "feat: add new feature"
git push
```

### Skip hooks (emergency only)
```bash
# Skip via environment variable
SKIP_HOOKS=1 git commit -m "wip: work in progress"

# Or use git's built-in flag
git commit --no-verify -m "wip: work in progress"
git push --no-verify
```

### Auto-approve all fixes (CI/scripts)
```bash
HUSKYCAT_AUTO_APPROVE=1 git commit -m "feat: new feature"
```

### Fix issues manually before commit
```bash
# Format code
uv run black src/ tests/

# Fix lint issues
uv run ruff check --fix src/ tests/

# Then commit
git add -u
git commit -m "style: fix formatting"
```

## Interactive Auto-Fix Flow

When validation fails, hooks will prompt:

```
[WARN] Black found issues
Apply Black auto-fix? [y/N]: y
[STEP] Applying Black fixes...
[OK] Black: Fixes applied
[OK] Fixed files re-staged
```

In non-interactive mode (CI, scripts), auto-fix is skipped unless `HUSKYCAT_AUTO_APPROVE=1`.

## File Structure

```
.githooks/
├── README.md           # This file
├── _/
│   └── common.sh       # Shared utilities (colors, logging, helpers)
├── pre-commit          # Staged file validation
├── pre-push            # Full codebase validation
└── commit-msg          # Commit message format validation
```

## Troubleshooting

### "UV not found" error
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Then setup venv
uv sync --dev
```

### "Virtual environment not found" error
```bash
# Create venv with dev dependencies
uv sync --dev
```

### Hooks not running
```bash
# Verify hooks path is configured
git config core.hooksPath
# Should output: .githooks

# If not, set it
git config core.hooksPath .githooks
```

### Permission denied on hook
```bash
# Make hooks executable
chmod +x .githooks/*
chmod +x .githooks/_/*
```

## Design Principles

1. **UV-Only Execution**: No binary fallback, no container fallback. Forces "eat your own dogfood" from day one.

2. **Git-Tracked**: All hooks are version-controlled. Changes to hooks are reviewed like any other code change.

3. **Interactive by Default**: Prompts for auto-fix when issues found. Supports non-interactive mode for CI.

4. **Fail-Fast**: Stops on first failure category (formatting, then linting).

5. **Clear Escape Hatches**: `SKIP_HOOKS=1` or `--no-verify` when needed.
