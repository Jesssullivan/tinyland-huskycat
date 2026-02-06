# HuskyCat - Universal Code Validation Platform
# Replaces npm scripts with just recipes
# Usage: just <recipe> [args...]

set shell := ["bash", "-euo", "pipefail", "-c"]
set dotenv-load

# Detect container runtime
container_runtime := if `command -v podman 2>/dev/null || true` != "" { "podman" } else { "docker" }

# Default recipe - show status
default: status

# === Development ===

# Run HuskyCat CLI with arbitrary arguments
dev *ARGS:
    uv run python3 -m src.huskycat {{ARGS}}

# Run validation on current directory
validate *ARGS:
    uv run python3 -m src.huskycat validate {{ARGS}}

# Validate with auto-fix
validate-fix *ARGS:
    uv run python3 -m src.huskycat validate --fix {{ARGS}}

# Validate all files
validate-all:
    uv run python3 -m src.huskycat validate --all

# Validate staged files only
validate-staged:
    uv run python3 -m src.huskycat validate --staged

# Validate with warnings allowed (dev mode)
validate-dev:
    uv run python3 -m src.huskycat validate --allow-warnings

# Validate CI configuration
validate-ci:
    uv run python3 -m src.huskycat ci-validate .gitlab-ci.yml

# Show HuskyCat status
status:
    uv run python3 -m src.huskycat status

# Clean cache and temporary files
clean:
    uv run python3 -m src.huskycat clean

# Audit global git config
audit-config *ARGS:
    uv run python3 -m src.huskycat audit-config {{ARGS}}

# === Hooks ===

# Install git hooks
hooks-install:
    uv run python3 -m src.huskycat setup-hooks

# Start MCP server (stdio mode)
mcp-server:
    uv run python3 -m src.huskycat mcp-server

# Test MCP server with tools/list
mcp-test:
    echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' | uv run python3 -m src.huskycat mcp-server

# === Build ===

# Build PyInstaller binary
build-binary:
    uv run python scripts/build_fat_binary.py

# Build signed binary (macOS)
build-binary-signed:
    uv run python scripts/build_fat_binary.py --codesign-identity "${APPLE_SIGNING_IDENTITY:-}" --entitlements-file build/specs/entitlements.plist

# Build and compress with UPX
build-upx: build-binary
    upx --best --lzma dist/huskycat

# Build fat binary
build-fat:
    uv run python scripts/build_fat_binary.py

# Build fat binary for all platforms
build-fat-all:
    uv run python scripts/build_fat_binary.py --all-platforms

# Build everything (container + binary)
build-all: container-build build-binary

# === Container ===

# Build container image
container-build:
    {{container_runtime}} build -f ContainerFile -t huskycat:local .

# Test container image
container-test:
    {{container_runtime}} run --rm huskycat:local --version

# Validate with container
container-validate:
    {{container_runtime}} run --rm -v "$(pwd)":/workspace huskycat:local validate --all

# Validate staged files with container
container-validate-staged:
    {{container_runtime}} run --rm -v "$(pwd)":/workspace huskycat:local validate --staged

# Shell into container
container-shell:
    {{container_runtime}} run --rm -it huskycat:local /bin/bash

# === Tools ===

# Download external tools
tools-download:
    uv run python scripts/download_tools.py

# Download all tools (all platforms)
tools-download-all:
    uv run python scripts/download_tools.py --all

# Clean downloaded tools
tools-clean:
    uv run python scripts/download_tools.py --clean

# === Test ===

# Run all tests
test:
    uv run pytest tests/ -v

# Run unit tests only
test-unit:
    uv run pytest tests/ -v -m unit

# Run integration tests
test-integration:
    uv run pytest tests/ -v -m integration

# Run all non-e2e tests
test-all:
    uv run pytest tests/ -v -m 'not e2e'

# Run MCP-specific tests
test-mcp:
    uv run pytest tests/ -v -k mcp

# Verify binary after build
verify-binary:
    bash scripts/verify_binary.sh dist/huskycat

# === Nix ===

# Build with Nix
nix-build:
    nix build

# Enter Nix dev shell
nix-shell:
    nix develop

# Enter Nix CI shell (with GPL tools)
nix-shell-ci:
    nix develop .#ci

# Run Nix flake checks
nix-check:
    nix flake check

# Show Nix flake outputs
nix-show:
    nix flake show

# Build container with Nix
nix-container:
    nix build .#container

# === Docs ===

# Build MkDocs documentation
docs-build:
    mkdocs build

# Serve documentation locally
docs-serve:
    mkdocs serve

# Deploy docs to GitLab Pages
docs-deploy:
    mkdocs gh-deploy

# === Install ===

# Install in editable mode
install-local:
    uv pip install -e .

# Install all dependencies
install-deps:
    uv sync --dev

# === CI ===

# Full CI validation
ci-validate: validate-ci container-validate

# Prepare for release
release-prepare: build-all ci-validate
