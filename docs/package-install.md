# RPM & DEB Packages

HuskyCat provides native Linux packages for RPM-based (Rocky Linux, RHEL, Fedora) and DEB-based (Debian, Ubuntu) distributions.

## RPM Installation (Rocky Linux / RHEL / Fedora)

### Direct Install from GitLab

```bash
# Rocky Linux 10 / RHEL 10
rpm -i https://gitlab.com/tinyland/ai/huskycat/-/packages/generic/huskycat/latest/huskycat-2.0.0-1.x86_64.rpm

# Or download first
curl -LO https://gitlab.com/tinyland/ai/huskycat/-/packages/generic/huskycat/latest/huskycat-2.0.0-1.x86_64.rpm
sudo rpm -i huskycat-2.0.0-1.x86_64.rpm
```

### Using DNF

```bash
# Install from local file
sudo dnf install ./huskycat-2.0.0-1.x86_64.rpm

# Verify installation
huskycat --version
```

### Package Contents

The RPM installs:

| Path | Description |
|------|-------------|
| `/usr/local/bin/huskycat` | Main binary |
| `/usr/share/doc/huskycat/README.md` | Documentation |
| `/usr/share/doc/huskycat/LICENSE` | Apache-2.0 license |
| `/usr/share/applications/huskycat.desktop` | Desktop entry |
| `/etc/huskycat/` | Configuration directory |

### Uninstall

```bash
sudo rpm -e huskycat
# or
sudo dnf remove huskycat
```

## DEB Installation (Debian / Ubuntu)

### Direct Install

```bash
curl -LO https://gitlab.com/tinyland/ai/huskycat/-/packages/generic/huskycat/latest/huskycat_2.0.0-1_amd64.deb
sudo dpkg -i huskycat_2.0.0-1_amd64.deb
```

### Using APT

```bash
# Install from local file (resolves dependencies)
sudo apt install ./huskycat_2.0.0-1_amd64.deb

# Verify installation
huskycat --version
```

### Uninstall

```bash
sudo apt remove huskycat
# or
sudo dpkg -r huskycat
```

## Post-Installation

After installing, set up git hooks and verify the installation:

```bash
# Check version
huskycat --version

# Show status
huskycat status

# Set up git hooks in your repository
cd /path/to/your/repo
huskycat setup-hooks

# Run validation
huskycat validate .

# Optional: register MCP server with Claude Code
claude mcp add huskycat -- huskycat mcp-server
```

## Dependencies

The packages require:

- **git** >= 2.0 (for hooks integration)
- **glibc** (included in all standard distributions)

No Python installation is required - the binary is self-contained.

## Supported Platforms

| Distribution | Version | Architecture | Status |
|-------------|---------|--------------|--------|
| Rocky Linux | 10 | x86_64 | Supported |
| Rocky Linux | 9 | x86_64 | Supported |
| RHEL | 9, 10 | x86_64 | Supported |
| Fedora | 38+ | x86_64 | Supported |
| Ubuntu | 22.04+ | amd64 | Supported |
| Debian | 12+ | amd64 | Supported |

## Building from Source

To build packages locally:

```bash
# Install FPM
gem install fpm

# Build RPM
fpm -s dir -t rpm --name huskycat --version 2.0.0 \
  -C pkg-root .

# Build DEB
fpm -s dir -t deb --name huskycat --version 2.0.0 \
  -C pkg-root .
```

See `.gitlab/ci/fpm-packages.yml` for the full CI build configuration.
