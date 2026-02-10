# Changelog

All notable changes to HuskyCat will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-02-08 - Full Distribution & Integration

### Added

#### Distribution Channels
- GitLab Pages site with downloads page, install script, and LLM docs
- RPM packages for Rocky Linux via FPM with GitLab Package Registry upload
- DEB packages for Debian/Ubuntu via FPM with GitLab Package Registry upload
- nix2container images pushed to GitLab Container Registry
- macOS PKG installers with code signing, notarization, and stapling
- One-line installer: `curl -fsSL https://huskycat-570fbd.gitlab.io/install.sh | bash`
- SHA256 checksum verification in install script (supports SHA256SUMS.txt)

#### Nix Home-Manager Module
- Recursive git repo auto-discovery across configurable scan directories
- Shell hook integration (direnv/cd-based) for automatic hook installation
- Per-repo opt-out via `.huskycat-disable` sentinel file
- Crush-dots dispatcher integration for multi-hook priority handling
- Configurable options: `tinyland.huskycat.autoDiscover.*`

#### Auto-Triage Engine
- Platform adapters for GitLab, GitHub, and Codeberg
- Post-commit hook for non-blocking triage
- Commit analysis with label suggestions and iteration assignment
- API integration via `glab` and `gh` CLI tools

#### New CLI Commands
- `huskycat audit-config` - Git configuration audit with 9 checks and `--fix` mode
- `huskycat triage` - Manual triage trigger for commit analysis

#### Documentation
- 3 new installation pages: nix-install.md, package-install.md, container-usage.md
- LLM-friendly docs served at /llms.txt, /llms.json, /llms-full.md
- Downloads page with platform detection and auto-generated index
- 28 total documentation pages (16,649 lines)

#### CI/CD Hardening
- Robust notarization error handling (replaces `|| true` with exit code capture)
- Container registry push verification with `skopeo inspect`
- SBOM container job retry logic
- Docker pull verification after DinD push
- Nix flake check now catches real test failures (removed `|| true`)
- `allow_failure: false` on nix:container, nix:flake:check, nix:devshell
- Registry variable consolidation ($CONTAINER_REGISTRY used consistently)

#### Testing
- 60%+ test coverage (up from 27.5%)
- pytest configuration formalized in pyproject.toml
- Coverage enforcement: CI fails below 60%
- Updated git hook tests from legacy .husky/ to .githooks/
- 30+ new test files for validators, commands, and core modules

### Changed
- `justfile` replaces npm scripts (44 recipes)
- Pages job now pulls build artifacts via `needs:` dependencies
- Install script checksum verification uses SHA256SUMS.txt format
- FPM packages use correct desktop file path (assets/linux/huskycat.desktop)

### Fixed
- Downloads page artifact paths (was looking in wrong directories)
- Desktop entry file not found in FPM packaging
- Nix container registry variable inconsistency ($CI_REGISTRY_IMAGE vs $CONTAINER_REGISTRY)
- macOS notarization failures silently swallowed by `|| true`
- PKG installer shipped unsigned without warning when cert missing
- Flake check always passing due to `|| true` on pytest

---

## [2.0.0] - 2025-12-07 - Sprint 10

### Added

#### Non-Blocking Git Hooks
- Non-blocking git hooks with parent return time under 100ms (300x faster than blocking)
- Background validation process with real-time TUI progress display using Rich library
- Previous run failure detection prevents commits with unresolved validation errors
- ProcessManager for fork management, PID tracking, and result caching
- ValidationTUI with thread-safe status updates and graceful TTY detection
- Validation run history with status tracking (.huskycat/runs/)
- Cleanup commands for old validation runs and zombie processes

#### Fat Binaries with Embedded Tools
- Standalone fat binaries (150-200MB) with embedded validation tools
- Embedded tool extraction to ~/.huskycat/tools/ on first run
- Version-aware tool extraction (only re-extracts on bundle version changes)
- Platform-specific binaries: darwin-arm64, darwin-amd64, linux-arm64, linux-amd64
- Tool resolution priority: bundled > local > container > container fallback
- Elimination of container runtime dependency for binary distributions

#### Parallel Tool Execution
- ParallelExecutor with intelligent dependency graph management
- 7.5x speedup vs sequential execution (15+ tools in 2 execution levels)
- ThreadPoolExecutor with configurable worker count (default: 8 workers)
- Automatic topological sorting ensures correct tool execution order
- Smart failure handling skips dependent tools when dependencies fail
- Timeout protection prevents hanging tool executions

#### Performance Improvements
- Git hook parent process returns in <100ms (previously 30s)
- Embedded tool execution 4.5x faster than container mode (0.42s vs 1.87s)
- All 15+ validation tools run in background (previously only 4 fast tools)
- Parallel execution reduces full validation time from 30s to 10s

### Changed

#### Architecture Changes
- Git hooks now non-blocking by default (enable with feature flag)
- Tool resolution prioritizes bundled tools over local/container tools
- Execution models expanded to include embedded tools mode
- All validation tools run in git hooks (not just fast subset)

#### Configuration Changes
- Added feature_flags.nonblocking_hooks configuration option
- Added feature_flags.parallel_execution configuration option
- Added feature_flags.tui_progress configuration option
- Added feature_flags.cache_results configuration option

#### CLI Changes
- Added --fork option to validate command for explicit forking
- Added status checking commands to view validation history
- Added cleanup commands for managing validation runs

### Deprecated

#### Deprecated Features
- Fast mode replaced by non-blocking mode (fast mode concept deprecated)
- Container-first tool resolution (now fallback only with warning)
- Blocking git hooks (legacy mode, non-blocking recommended)

### Performance

#### Benchmarks
- **Git Operations**: 300x faster (30s → 100ms parent return)
- **Tool Execution**: 7.5x faster (parallel vs sequential)
- **Container Avoidance**: 4.5x faster (bundled vs container: 0.42s vs 1.87s)
- **Full Validation**: 3x faster (30s → 10s with parallelization)

#### Resource Usage
- Memory: ~50MB per validation run
- CPU: Scales with available cores (8 workers default)
- Disk: ~1KB per run result (auto-cleaned after 7 days)
- Binary size: 150-200MB (platform-dependent)

### Fixed

#### Bug Fixes
- Fixed container runtime detection for Podman vs Docker
- Fixed tool extraction permissions on first run
- Fixed zombie process cleanup on validation interruption
- Fixed TTY detection for TUI display in non-interactive environments

### Security

#### Security Improvements
- Tool isolation: embedded tools extracted to user cache only (~/.huskycat/)
- No system-wide installation required
- No elevated privileges needed for tool extraction
- Read-only repository mounting when using container mode

### Documentation

#### New Documentation
- docs/nonblocking-hooks.md - Comprehensive non-blocking hooks guide
- docs/EMBEDDED_TOOL_EXECUTION.md - Embedded tools architecture
- docs/FAT_BINARY_ARCHITECTURE.md - Fat binary build process
- docs/parallel_executor.md - Parallel execution engine documentation
- docs/performance.md - Performance benchmarks and optimization guide
- docs/migration/to-nonblocking.md - Migration guide from blocking hooks

#### Updated Documentation
- README.md - Added Sprint 10 features and benchmarks
- docs/architecture/execution-models.md - Added non-blocking and embedded modes
- docs/troubleshooting.md - Added Sprint 10 troubleshooting section
- CLAUDE.md - Updated with Sprint 10 instructions

### Technical Details

#### Implementation Files
- src/huskycat/core/process_manager.py - Process management and forking
- src/huskycat/core/tui.py - Real-time validation TUI
- src/huskycat/core/parallel_executor.py - Parallel tool execution
- src/huskycat/core/adapters/git_hooks_nonblocking.py - Non-blocking adapter
- src/huskycat/core/tool_extractor.py - Embedded tool extraction
- build_fat_binary.py - Fat binary build script
- scripts/download_tools.py - Tool download utility

#### Tool Dependencies
Level 0 (9 tools in parallel):
  - autoflake, black, chapel-format, hadolint
  - isort, ruff, shellcheck, taplo, yamllint

Level 1 (6 tools in parallel):
  - ansible-lint (depends on: yamllint)
  - bandit (depends on: black)
  - flake8 (depends on: black, isort)
  - gitlab-ci (depends on: yamllint)
  - helm-lint (depends on: yamllint)
  - mypy (depends on: black, isort)

### Migration Notes

#### Breaking Changes
None! Sprint 10 is fully backward compatible.

#### Recommended Actions
1. Enable non-blocking hooks: Set feature_flags.nonblocking_hooks: true
2. Download platform-specific fat binary for portable deployment
3. Enable parallel execution: Set feature_flags.parallel_execution: true
4. Configure TUI progress: Set feature_flags.tui_progress: true

#### Rollback Procedure
To revert to blocking hooks:
```yaml
feature_flags:
  nonblocking_hooks: false
```

Or set environment variable:
```bash
export HUSKYCAT_FEATURE_NONBLOCKING_HOOKS=false
```

### Known Issues

#### Current Limitations
- TUI requires TTY (falls back to log file in non-interactive mode)
- Fat binaries only support Linux and macOS (Windows support planned)
- Tool extraction requires write access to ~/.huskycat/
- Background processes may become zombies if parent terminates unexpectedly

#### Workarounds
- Use `huskycat clean --zombies` to cleanup orphaned processes
- Check `~/.huskycat/runs/latest.log` for validation output in non-TTY mode
- Ensure adequate disk space for tool extraction (~500MB)

---

## [1.0.0] - 2025-11-XX - Sprint 0-9

### Added
- Five product modes: Git Hooks, CI, CLI, Pipeline, MCP Server
- Three execution models: Binary, Container, UV Development
- Multi-arch container support: amd64, arm64
- GitLab CI/CD validation with official schema
- GitLab Auto-DevOps Helm/K8s validation
- Chapel language formatting support
- MCP server for Claude Code integration
- Universal validation: Python, YAML, Shell, Docker, TOML
- Auto-fix framework with confidence tiers
- Git hooks setup and management
- Binary builds with PyInstaller
- Container builds with Alpine Linux

### Technical
- Mode detection with priority: flag → env → command → git → CI → TTY
- Adapter pattern for mode-specific behavior
- Factory pattern for command routing
- Validator base class with execution routing
- Container runtime detection and delegation

### Documentation
- Architecture documentation with code references
- Installation and user guides
- CLI reference and examples
- Development guide

---

## Version History

- **2.1.0** (2026-02-08): Full Distribution - Pages, Nix, RPM/DEB, containers, macOS signing, triage, 60%+ coverage
- **2.0.0** (2025-12-07): Sprint 10 - Non-blocking hooks, fat binaries, parallel execution
- **1.0.0** (2025-11-XX): Sprint 0-9 - Initial release with 5 product modes, 3 execution models

---

## Links

- [GitLab Repository](https://gitlab.com/tinyland/ai/huskycat)
- [Documentation](https://huskycat-570fbd.gitlab.io)
- [Issue Tracker](https://gitlab.com/tinyland/ai/huskycat/-/issues)
- [Releases](https://gitlab.com/tinyland/ai/huskycat/-/releases)
- [Container Registry](https://gitlab.com/tinyland/ai/huskycat/container_registry)

---

**Note**: This changelog follows semantic versioning. Major version bumps (2.0.0) indicate significant architectural changes or new features, even when fully backward compatible.
