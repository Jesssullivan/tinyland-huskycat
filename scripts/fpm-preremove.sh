#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# FPM pre-remove script for Linux packages (RPM/DEB)
# Runs before package removal

echo "Preparing to remove HuskyCat..."

# Remove any installed git hooks that point to huskycat
# (only if the binary still exists at this point)
if [ -x /usr/local/bin/huskycat ]; then
    echo "Note: Git hooks installed by HuskyCat will need manual cleanup."
    echo "  Run 'git config --unset core.hooksPath' in affected repositories."
fi

# Preserve user configuration
echo ""
echo "Configuration at ~/.huskycat and ~/.cache/huskycat will be preserved."
echo "Remove manually if not needed:"
echo "  rm -rf ~/.huskycat ~/.cache/huskycat"

exit 0
