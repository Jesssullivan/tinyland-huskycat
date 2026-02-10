#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# FPM post-install script for Linux packages (RPM/DEB)
# Runs after package installation

set -e

echo "HuskyCat Post-Install Setup"
echo "==========================="

# Ensure binary is executable
if [ -f /usr/local/bin/huskycat ]; then
    chmod +x /usr/local/bin/huskycat
    echo "Binary installed: /usr/local/bin/huskycat"
fi

# Update icon cache (for .desktop file)
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
fi

# Update desktop database (for .desktop file)
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
fi

# Display completion message
echo ""
echo "HuskyCat installed successfully!"
echo ""
echo "Quick Start:"
echo "  huskycat --version       Check version"
echo "  huskycat status          Check installation"
echo "  huskycat setup-hooks     Install git hooks in current repo"
echo "  huskycat validate .      Validate current directory"
echo ""

# Detect git and suggest hooks setup
if command -v git &> /dev/null; then
    echo "Git detected. To set up validation hooks in a repository:"
    echo "  cd /path/to/your/repo && huskycat setup-hooks"
    echo ""
fi

# Detect Claude Code and suggest MCP registration
if command -v claude &> /dev/null; then
    echo "Claude Code detected. To register HuskyCat as an MCP server:"
    echo "  claude mcp add huskycat -- huskycat mcp-server"
    echo ""
fi

echo "Documentation: https://huskycat-570fbd.gitlab.io"
echo ""

exit 0
