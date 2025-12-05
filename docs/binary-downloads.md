# Binary Downloads

HuskyCat provides pre-built binaries for multiple platforms through GitLab releases.

## Quick Install

### Linux (AMD64)

```bash
# Download latest release
curl -L -o huskycat https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64

# Make executable
chmod +x huskycat

# Install to system path (optional)
sudo mv huskycat /usr/local/bin/
```

### Linux (ARM64)

```bash
# Download latest release
curl -L -o huskycat https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-arm64

# Make executable
chmod +x huskycat

# Install to system path (optional)
sudo mv huskycat /usr/local/bin/
```

### macOS (Apple Silicon)

```bash
# Download latest release (ad-hoc signed)
curl -L -o huskycat https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-darwin-arm64

# Make executable
chmod +x huskycat

# Install to user path (recommended for unsigned binaries)
mv huskycat ~/.local/bin/

# Add to PATH if needed
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Note**: macOS binaries are ad-hoc signed. You may need to allow execution in System Settings > Privacy & Security on first run.

## Available Binaries

| Platform | Architecture | Binary Name | Status |
|----------|-------------|-------------|---------|
| Linux | x86_64 | `huskycat-linux-amd64` | ✅ Rocky Linux 10 |
| Linux | ARM64/aarch64 | `huskycat-linux-arm64` | ✅ Rocky Linux 10 |
| macOS | Apple Silicon (M1/M2/M3) | `huskycat-darwin-arm64` | ✅ Ad-hoc signed |
| macOS | Intel (x86_64) | ❌ Not available | GitLab SaaS ARM64 only |

## Download Options

### Option 1: Latest Release (Recommended)

Use GitLab's permalink to always get the latest version:

```bash
# Linux AMD64
https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64

# Linux ARM64
https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-arm64

# macOS ARM64
https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-darwin-arm64
```

### Option 2: Specific Version

Download a specific tagged release:

```bash
# Replace $VERSION with desired tag (e.g., v2.0.0)
https://gitlab.com/tinyland/ai/huskycat/-/jobs/artifacts/$VERSION/raw/dist/bin/huskycat-linux-amd64?job=binary:build:linux
```

### Option 3: Browse All Releases

Visit the releases page to see all available versions:

[https://gitlab.com/tinyland/ai/huskycat/-/releases](https://gitlab.com/tinyland/ai/huskycat/-/releases)

## Verification

### Check Version

```bash
./huskycat --version
```

### Verify Installation

```bash
# Show system status
./huskycat status

# Test validation
./huskycat validate --help
```

### Container Requirements

HuskyCat requires a container runtime for validation:

```bash
# Check for Podman
podman --version

# Or check for Docker
docker --version
```

If neither is installed, see [Container Runtime Installation](#container-runtime-installation).

## Installation Methods

### Method 1: User Installation (Recommended)

Install to `~/.local/bin` (no sudo required):

```bash
# Create directory if it doesn't exist
mkdir -p ~/.local/bin

# Download and install
curl -L -o ~/.local/bin/huskycat https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64
chmod +x ~/.local/bin/huskycat

# Add to PATH (if not already)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Method 2: System-Wide Installation

Install to `/usr/local/bin` (requires sudo):

```bash
# Download
curl -L -o /tmp/huskycat https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64

# Install
sudo install -m 0755 /tmp/huskycat /usr/local/bin/huskycat
rm /tmp/huskycat
```

### Method 3: Project-Local Installation

Install in your project directory:

```bash
# Download to project
curl -L -o huskycat https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64
chmod +x huskycat

# Use relative path
./huskycat setup-hooks
./huskycat validate
```

## Container Runtime Installation

HuskyCat requires either Podman or Docker for validation.

### Podman (Recommended)

#### macOS

```bash
# Using Homebrew
brew install podman

# Start Podman machine
podman machine init
podman machine start
```

#### Linux

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y podman

# Fedora/Rocky/RHEL
sudo dnf install -y podman

# Arch
sudo pacman -S podman
```

### Docker

#### macOS

Download Docker Desktop from [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)

#### Linux

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (optional)
sudo usermod -aG docker $USER
newgrp docker
```

## Post-Installation

### 1. Setup Git Hooks

```bash
# Navigate to your project
cd your-project

# Install HuskyCat git hooks
huskycat setup-hooks
```

### 2. Configure MCP (Optional)

For Claude Code integration:

```bash
huskycat bootstrap
```

See [MCP Server Integration](features/mcp-server.md) for details.

### 3. Build Container (First Run)

```bash
# Build validation container
cd /path/to/huskycats-bates
npm run container:build
```

**Note**: This step is only needed if you're developing HuskyCat itself. For normal usage, the binary will use pre-built container images.

## Troubleshooting

### "Permission denied" on macOS

macOS Gatekeeper may block unsigned binaries:

```bash
# Allow execution
xattr -d com.apple.quarantine ~/.local/bin/huskycat

# Or: System Settings > Privacy & Security > Allow "huskycat"
```

### "No container runtime available"

Install Podman or Docker:

```bash
# Check if installed
which podman || which docker

# Install Podman (recommended)
brew install podman  # macOS
sudo dnf install podman  # Rocky Linux
```

### Binary not found after installation

Check PATH:

```bash
# Verify binary location
ls -l ~/.local/bin/huskycat

# Check if directory is in PATH
echo $PATH | grep -q "$HOME/.local/bin" && echo "✓ In PATH" || echo "✗ Not in PATH"

# Add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Architecture mismatch

Ensure you downloaded the correct binary for your platform:

```bash
# Check your architecture
uname -m
# x86_64 → Use huskycat-linux-amd64
# aarch64 or arm64 → Use huskycat-linux-arm64 or huskycat-darwin-arm64

# Check binary architecture
file huskycat
```

## Updating

### Manual Update

```bash
# Download new version
curl -L -o /tmp/huskycat https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-linux-amd64

# Replace existing binary
chmod +x /tmp/huskycat
mv /tmp/huskycat ~/.local/bin/huskycat

# Verify new version
huskycat --version
```

### Update Script

Create an update script:

```bash
#!/usr/bin/env bash
# update-huskycat.sh

set -euo pipefail

PLATFORM="linux-amd64"  # Change to your platform
INSTALL_DIR="$HOME/.local/bin"
BINARY_URL="https://gitlab.com/tinyland/ai/huskycat/-/releases/permalink/latest/downloads/huskycat-${PLATFORM}"

echo "Downloading HuskyCat for ${PLATFORM}..."
curl -L -o /tmp/huskycat "$BINARY_URL"

echo "Installing to ${INSTALL_DIR}..."
chmod +x /tmp/huskycat
mv /tmp/huskycat "${INSTALL_DIR}/huskycat"

echo "✓ HuskyCat updated successfully!"
huskycat --version
```

```bash
# Make executable and run
chmod +x update-huskycat.sh
./update-huskycat.sh
```

## Alternative: Build from Source

If binaries aren't available for your platform, build from source:

```bash
git clone https://gitlab.com/tinyland/ai/huskycat.git
cd huskycat
npm install
uv sync --dev
npm run build:binary

# Binary will be at: dist/huskycat
```

See [Installation Guide](installation.md) for detailed build instructions.

---

For additional support, see [Troubleshooting](troubleshooting.md) or visit our [GitLab Issues](https://gitlab.com/tinyland/ai/huskycat/-/issues).
