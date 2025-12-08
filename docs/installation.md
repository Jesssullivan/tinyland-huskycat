# Installation Guide

This guide covers installing HuskyCat locally and in development projects.

See [Architecture Documentation](architecture/) for details on execution models and product modes.

## Prerequisites

### Core Requirements
- **Python 3.8+**: For binary build and UV development mode
- **UV Package Manager**: `pip install uv`
- **Node.js and npm**: Build system

### Optional Requirements
- **Container Runtime**: Podman or Docker (for container execution mode)
- **Git Repository**: For hooks and staged file validation

### Execution Model Requirements

| Model | Python | UV | Container Runtime | Build Tools |
|-------|--------|-----|-------------------|-------------|
| **Binary** | Build only | No | Optional | PyInstaller |
| **Container** | No | No | Required | Podman/Docker |
| **UV Development** | Yes | Yes | Optional | npm |

See [Execution Models](architecture/execution-models.md) for complete details.

## Quick Start - HuskyCat Installation

HuskyCat provides multiple installation methods to suit different workflows.

### Method 1: Build from Source (Recommended)

```bash
# Clone and build HuskyCat
git clone <repository>
cd huskycats-bates
npm install

# Install Python dependencies (for UV development mode)
uv sync --dev

# Optional: Build container for container-based execution
npm run container:build

# Build binary entry point
npm run build:binary

# Verify installation
./dist/huskycat --version
./dist/huskycat status
```

### Method 2: Development Mode (UV + npm)

```bash
# For active development on HuskyCat itself
npm run dev -- --help             # Show available commands
npm run validate                   # Validate current directory
npm run hooks:install              # Setup git hooks
npm run mcp:server                 # Start MCP server
```

### Method 3: Container Execution

```bash
# Build validation container
npm run container:build

# Run validation through container
npm run container:validate

# Container-based validation with volume mount
podman run --rm -v "$(pwd)":/workspace huskycat:local validate --all
```

## Using HuskyCat in Your Projects

### 1. Setup Git Hooks

```bash
# Navigate to your project
cd your-project

# Setup HuskyCat git hooks
./path/to/huskycat setup-hooks

# Test the installation
git add .
git commit -m "test: verify hooks"  # Should run validation
```

**Git Hooks Mode** uses fast subset validation (black, ruff, mypy) for <5s execution.
See [Product Modes](architecture/product-modes.md) for mode-specific behavior.

### 2. Validate Code

```bash
# Validate current directory
./path/to/huskycat validate

# Validate specific files
./path/to/huskycat validate src/main.py

# Validate all files
./path/to/huskycat validate --all

# Validate only staged files
./path/to/huskycat validate --staged

# Auto-fix validation issues
./path/to/huskycat validate --fix
```

## Execution Models

HuskyCat supports three execution models:

### Binary Execution (Recommended)
```bash
./dist/huskycat validate --staged    # Fast startup, optional container delegation
```
**Implementation**: `huskycat_main.py:1-27` → `__main__.py:1-50`
**Best for**: Git hooks, CI/CD, production deployments
**Container**: Optional delegation when runtime available (`unified_validation.py:85-109`)

### Container Execution
```bash
npm run container:validate           # Alpine-based multi-arch
```
**Implementation**: `ContainerFile:1-153`, `.gitlab-ci.yml:158-218`
**Best for**: Maximum isolation, consistent toolchain
**Requirement**: Container runtime (podman or docker)

### UV Development Mode
```bash
npm run dev -- validate              # UV + npm scripts
```
**Implementation**: `package.json:8-38`
**Best for**: Development, testing, convenience
**Requirement**: UV package manager, Python 3.8+

## MCP Server Integration

### Setup MCP for Claude Code

```bash
# Start MCP server for Claude Code integration (stdio protocol)
./path/to/huskycat mcp-server

# Test MCP server connection
echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' | ./path/to/huskycat mcp-server

# Configure in Claude Code MCP settings:
# Command: /path/to/huskycat
# Args: ["mcp-server"]
```

**Implementation**: `mcp_server.py:1-150` - JSON-RPC 2.0 over stdio

## What Gets Configured

HuskyCat setup creates:

```
your-project/
├── .git/hooks/               # Git hooks installed by setup-hooks
│   ├── pre-commit           # Validates staged files (fast subset)
│   ├── pre-push             # Validates CI configuration
│   └── commit-msg           # Validates commit message format
├── .huskycat/               # Configuration and cache
│   ├── config.json         # HuskyCat configuration
│   └── schemas/            # Downloaded validation schemas
└── (existing project files remain unchanged)
```

**Note**: Binary config stored in `~/.huskycat/` separately from repository for isolation.

## Post-Installation

### Verify Installation

```bash
# Check HuskyCat status
./dist/huskycat status

# Test validation
./dist/huskycat validate --all

# Verify git hooks are working (Git Hooks mode: fast subset)
git add .
git commit -m "test: verify hooks"  # Runs black, ruff, mypy

# Update validation schemas
./dist/huskycat update-schemas
```

### Using HuskyCat Commands

After installation, you can use these commands:

```bash
# Validate code
./dist/huskycat validate                    # Validate current directory
./dist/huskycat validate --staged          # Validate staged files
./dist/huskycat validate src/main.py       # Validate specific file
./dist/huskycat validate --fix             # Auto-fix issues

# CI/CD validation
./dist/huskycat ci-validate .gitlab-ci.yml # Validate GitLab CI

# MCP integration
./dist/huskycat mcp-server                  # Start MCP server (stdio)

# Management
./dist/huskycat clean                       # Clean cache
./dist/huskycat update-schemas              # Update schemas
./dist/huskycat status                      # Show status

# Mode override
./dist/huskycat --mode ci validate          # Force CI mode (JUnit XML)
./dist/huskycat --mode pipeline validate    # Force pipeline mode (JSON)
./dist/huskycat --json validate             # Shorthand for pipeline mode
```

## Product Modes

HuskyCat automatically detects and adapts to different usage contexts:

| Mode | Output | Tools | Interactive | Detection |
|------|--------|-------|-------------|-----------|
| **Git Hooks** | Minimal | Fast subset (4) | Auto-detect TTY | Git env vars |
| **CI** | JUnit XML | All (15+) | Never | CI=true env |
| **CLI** | Rich colored | Configurable | Yes | Default/TTY |
| **Pipeline** | JSON | All | Never | --json flag |
| **MCP Server** | JSON-RPC 2.0 | All | Never | mcp-server cmd |

**Mode Detection**: `mode_detector.py:30-82` (priority: flag → env → command → git → CI → TTY → default)

See [Product Modes Documentation](architecture/product-modes.md) for complete comparison matrix.

## Development Configuration

### Configure Your IDE

#### VS Code
Add to `.vscode/settings.json`:
```json
{
  "editor.formatOnSave": true,
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

#### PyCharm
1. Go to Settings → Tools → File Watchers
2. Add watchers for Black and flake8
3. Enable "Reformat on Save"

### Update package.json Scripts

Add these helpful scripts:
```json
{
  "scripts": {
    "lint": "./path/to/huskycat validate --all",
    "lint:fix": "./path/to/huskycat validate --all --fix",
    "lint:staged": "./path/to/huskycat validate --staged"
  }
}
```

## Troubleshooting

### Execution Model Issues

1. **Container runtime not available**
   ```bash
   # Install podman (recommended) or docker
   brew install podman  # macOS
   apt install podman   # Ubuntu/Debian

   # Build container
   npm run container:build

   # Verify container works
   npm run container:test
   ```

2. **Binary execution issues**
   ```bash
   # Rebuild binary
   npm run build:binary

   # Check binary works
   ./dist/huskycat --version
   ./dist/huskycat status
   ```

3. **UV development mode issues**
   ```bash
   # Install UV package manager
   pip install uv

   # Sync dependencies
   uv sync --dev

   # Test UV mode
   npm run dev -- --help
   ```

### Architecture Issues

1. **"exec format error" when running containers**
   ```bash
   # Architecture mismatch - use platform flag
   podman run --rm --platform linux/amd64 -v "$(pwd):/workspace" \
     huskycat:local validate --all

   # Check your system architecture
   uname -m
   # x86_64 = use linux/amd64
   # arm64 or aarch64 = use linux/arm64
   ```

2. **Multi-arch container builds**
   ```bash
   # Build for specific architecture
   podman build --platform linux/amd64 -f ContainerFile -t huskycat:amd64 .
   podman build --platform linux/arm64 -f ContainerFile -t huskycat:arm64 .
   ```

### Common Issues

1. **"command not found" errors**
   - Binary not in PATH - use full path or add to PATH
   - Container not built - run `npm run container:build`
   - UV not installed - run `pip install uv`

2. **Permission denied**
   - Make binary executable: `chmod +x dist/huskycat`
   - Check file permissions: `ls -la dist/huskycat`

3. **Git hooks not running**
   - Run `./dist/huskycat setup-hooks` in your project
   - Check Git version (needs 2.9+)
   - Verify hooks installed: `ls -la .git/hooks/`

4. **Mode detection issues**
   - Force specific mode: `huskycat --mode cli validate`
   - Check environment: `echo $CI; echo $HUSKYCAT_MODE`
   - Review detection logic: `mode_detector.py:30-82`

See [Troubleshooting Guide](troubleshooting.md) for more solutions.

## Next Steps

- [Architecture Overview](architecture/)
  - [Execution Models](architecture/execution-models.md) - Binary, Container, UV modes
  - [Product Modes](architecture/product-modes.md) - 5 modes with code references
- [Configuration Guide](configuration.md) - Customize validation rules
- [MCP Server Documentation](features/mcp-server.md) - Claude Code integration
- [Git Hooks Guide](features/git-hooks.md) - Automated validation setup
