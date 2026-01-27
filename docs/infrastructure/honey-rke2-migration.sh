#!/bin/bash
# RKE2 Bind Mount Migration Script for honey server
#
# This script migrates /var/lib/rancher from root partition to /home
# using a bind mount approach.
#
# Run this script directly on honey with sudo:
#   sudo bash honey-rke2-migration.sh
#
# The script is idempotent - safe to run multiple times.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root (use sudo)"
   exit 1
fi

echo "=========================================="
echo "RKE2 Bind Mount Migration Script"
echo "=========================================="
echo ""

# Step 0: Pre-flight checks
log_info "Running pre-flight checks..."

# Check if already migrated
if mount | grep -q '/home/rancher-data.*bind'; then
    log_warn "Bind mount already exists. Migration appears complete."
    df -h /var/lib/rancher
    exit 0
fi

if grep -q '/home/rancher-data /var/lib/rancher' /etc/fstab; then
    log_warn "fstab entry exists but not mounted. Attempting to mount..."
    mount /var/lib/rancher
    df -h /var/lib/rancher
    exit 0
fi

# Check available space on /home
AVAIL=$(df --output=avail /home | tail -1)
if [[ $AVAIL -lt 1048576 ]]; then  # 1GB minimum
    log_error "/home has less than 1GB available. Aborting."
    exit 1
fi

log_info "Pre-flight checks passed."
echo ""

# Step 1: Stop RKE2
log_info "Step 1: Stopping RKE2..."
if systemctl is-active --quiet rke2-server; then
    systemctl stop rke2-server
    sleep 10
    if systemctl is-active --quiet rke2-server; then
        log_error "RKE2 failed to stop!"
        exit 1
    fi
    log_info "RKE2 stopped successfully."
else
    log_info "RKE2 already stopped."
fi
echo ""

# Step 2: Create target and copy data
log_info "Step 2: Creating target directory and copying data..."
mkdir -p /home/rancher-data

if [[ -d /var/lib/rancher && ! -L /var/lib/rancher ]]; then
    log_info "Copying data from /var/lib/rancher to /home/rancher-data..."
    rsync -avP --xattrs /var/lib/rancher/ /home/rancher-data/

    ORIG_SIZE=$(du -sm /var/lib/rancher | cut -f1)
    COPY_SIZE=$(du -sm /home/rancher-data | cut -f1)
    log_info "Original: ${ORIG_SIZE}MB, Copy: ${COPY_SIZE}MB"

    if [[ $COPY_SIZE -lt $((ORIG_SIZE - 10)) ]]; then
        log_error "Copy size mismatch! Aborting."
        exit 1
    fi
else
    log_warn "/var/lib/rancher doesn't exist or is a symlink. Skipping copy."
fi
echo ""

# Step 3: Switch to bind mount
log_info "Step 3: Setting up bind mount..."

if [[ -d /var/lib/rancher && ! -L /var/lib/rancher ]]; then
    mv /var/lib/rancher /var/lib/rancher.old
    log_info "Moved original to /var/lib/rancher.old"
fi

mkdir -p /var/lib/rancher

# Add fstab entry if not present
if ! grep -q '/home/rancher-data /var/lib/rancher' /etc/fstab; then
    echo '/home/rancher-data /var/lib/rancher none bind 0 0' >> /etc/fstab
    log_info "Added fstab entry."
else
    log_info "fstab entry already exists."
fi

mount /var/lib/rancher
log_info "Bind mount activated."
df -h /var/lib/rancher
echo ""

# Step 4: Restore SELinux contexts and start services
log_info "Step 4: Restoring SELinux contexts..."
restorecon -Rv /var/lib/rancher /home/rancher-data
echo ""

log_info "Step 5: Starting RKE2..."
systemctl start rke2-server

# Wait for RKE2 to stabilize
log_info "Waiting for RKE2 to stabilize (60 seconds)..."
sleep 60

if ! systemctl is-active --quiet rke2-server; then
    log_error "RKE2 failed to start! Check: journalctl -u rke2-server -n 50"
    log_error "Rollback with: sudo bash -c 'systemctl stop rke2-server; umount /var/lib/rancher; rmdir /var/lib/rancher; mv /var/lib/rancher.old /var/lib/rancher; sed -i \"/rancher-data.*bind/d\" /etc/fstab; systemctl start rke2-server'"
    exit 1
fi
echo ""

# Step 6: Verify
log_info "Step 6: Verification..."
echo ""
echo "Mount status:"
mount | grep rancher
echo ""
echo "Disk usage:"
df -h /var/lib/rancher
echo ""
echo "RKE2 status:"
systemctl is-active rke2-server
echo ""

# Check Kubernetes node
KUBECTL="/var/lib/rancher/rke2/bin/kubectl"
KUBECONFIG="/etc/rancher/rke2/rke2.yaml"

if [[ -x "$KUBECTL" && -f "$KUBECONFIG" ]]; then
    log_info "Kubernetes node status:"
    $KUBECTL --kubeconfig $KUBECONFIG get nodes || true
fi

echo ""
echo "=========================================="
log_info "Migration complete!"
echo "=========================================="
echo ""
echo "Cleanup (after 24-48h verification):"
echo "  sudo rm -rf /var/lib/rancher.old"
echo ""
echo "Rollback procedure:"
echo "  sudo systemctl stop rke2-server"
echo "  sudo umount /var/lib/rancher"
echo "  sudo rmdir /var/lib/rancher"
echo "  sudo mv /var/lib/rancher.old /var/lib/rancher"
echo "  sudo sed -i '/rancher-data.*bind/d' /etc/fstab"
echo "  sudo systemctl start rke2-server"
