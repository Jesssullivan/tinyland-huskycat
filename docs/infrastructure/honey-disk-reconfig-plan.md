# Honey Disk Reconfiguration Plan

**Created**: 2026-01-26
**Updated**: 2026-01-27
**Status**: PHASE 2 READY - Corrected Approach (Bind Mount)
**Risk Level**: Low (bind mount approach, reversible)

## Current State (Verified 2026-01-27)

### Hardware
- **CPU**: Dual-socket (unknown model)
- **RAM**: 219GB (110G per tmpfs)
- **Storage**: 2x SSDs

### Disk Layout

| Disk | Size | Current Use | Notes |
|------|------|-------------|-------|
| sda | 476.9GB | runner-vg (GitLab cache) | **100% ALLOCATED - NO VFREE** |
| sdb | 3.6TB | Rocky Linux | Active system disk |

### Current sdb (3.6TB) Partitioning

| Partition | Size | Mount | Purpose |
|-----------|------|-------|---------|
| sdb1 | 600MB | /boot/efi | EFI System |
| sdb2 | 1GB | /boot | Boot |
| sdb3 (LVM) | 3.6TB | - | LVM PV (rl VG) |

### Current LVM Layout

**Volume Group: runner-vg (sda1)** - PHASE 1 COMPLETE
| LV | Size | Mount | Status |
|----|------|-------|--------|
| runner-cache | 477GB | /var/lib/gitlab-runner/cache | Active, 2% used (9.2GB) |

**CRITICAL**: runner-vg has **0 bytes VFree** - entire VG allocated to runner-cache.
The original plan incorrectly confused filesystem available space (468GB inside XFS) with LVM VFree.

**Volume Group: rl (sdb3)**
| LV | Size | Mount | Current Use |
|----|------|-------|-------------|
| rl-root | 70GB | / | OS + RKE2 (68% = 48GB used) |
| rl-swap | 32GB | swap | Swap (commented out in fstab) |
| rl-home | 3.5TB | /home | User data + Docker (11% = 389GB used, **3.2TB available**) |

### Current Service Data Locations (Verified)

| Service | Path | Partition | Size Used | Notes |
|---------|------|-----------|-----------|-------|
| RKE2 | /var/lib/rancher | rl-root (/) | ~558MB base + containerd | Containerd data grows |
| Docker | /home/docker-data | rl-home (/home) | Variable | Root Dir configured |
| GitLab Runner Cache | /var/lib/gitlab-runner/cache | runner-vg (sda) | 9.2GB | **PHASE 1 COMPLETE** |
| GitLab Runner Config | /etc/gitlab-runner | rl-root (/) | Minimal | Config only |

### RKE2 Cluster Status

| Node | Status | Roles | Version |
|------|--------|-------|---------|
| honey | Ready | control-plane,etcd,master | v1.31.14+rke2r1 |
| blahaj | NotReady | agent | v1.31.14+rke2r1 |

**Note**: blahaj is NotReady - this should be investigated separately but does not block Phase 2.

---

## Phase 1: GitLab Runner Cache - COMPLETE

Phase 1 has been successfully completed:
- runner-vg volume group created on sda1
- runner-cache LV (477GB) mounted at /var/lib/gitlab-runner/cache
- Currently 2% used (9.2GB of 468GB available)
- Added to /etc/fstab with noatime option

---

## Phase 2: RKE2 Volume Migration - CORRECTED APPROACH

### Problem Statement

The original Phase 2 plan to create an LV in runner-vg **FAILED** due to a critical planning error:

| Assumption | Reality |
|------------|---------|
| runner-vg has 468GB VFree | runner-vg has **0 bytes VFree** |
| Can create 200GB rancher LV | **IMPOSSIBLE** - no space |

**Root Cause**: The plan confused **filesystem available space** (468GB inside XFS) with **LVM VFree** (0 bytes). The entire 477GB VG was allocated to runner-cache in Phase 1.

### Options Evaluated

| Option | Feasibility | Risk | Complexity |
|--------|-------------|------|------------|
| 1. Shrink runner-cache LV | **IMPOSSIBLE** | N/A | XFS cannot shrink |
| 2. Delete/recreate runner-cache smaller | Medium | Medium | High |
| 3. **Bind mount from /home** | **HIGH** | **LOW** | **LOW** |
| 4. Symlink from /home | Medium | Medium | SELinux issues |
| 5. Reclaim swap LV (32GB) | Low | Low | Only 32GB, not enough |

### Recommended Solution: Bind Mount from /home

**Rationale**:
- /home has **3.2TB available** on rl-home
- Same pattern Docker already uses (/home/docker-data)
- No LVM modifications required
- SELinux compatible (bind mounts preserve contexts)
- Quick, reversible, low-risk

### Implementation Script

A migration script has been created: `docs/infrastructure/honey-rke2-migration.sh`

**To execute** (requires interactive sudo on honey):

```bash
# Copy script to honey
scp docs/infrastructure/honey-rke2-migration.sh honey:/tmp/

# SSH to honey and run
ssh honey
sudo bash /tmp/honey-rke2-migration.sh
```

### Manual Implementation Steps

If you prefer to run commands manually:

#### Pre-Migration Checklist
```bash
# Verify current state
ssh honey "df -h / /home"
ssh honey "du -sh /var/lib/rancher"
```

#### Step 1: Stop RKE2 (2 min)
```bash
sudo systemctl stop rke2-server
sleep 10
systemctl is-active rke2-server  # Should say "inactive"
```

#### Step 2: Create Target and Copy Data (5 min)
```bash
sudo mkdir -p /home/rancher-data
sudo rsync -avP --xattrs /var/lib/rancher/ /home/rancher-data/
sudo du -sh /home/rancher-data  # Verify ~558MB copied
```

#### Step 3: Switch to Bind Mount (2 min)
```bash
sudo mv /var/lib/rancher /var/lib/rancher.old
sudo mkdir /var/lib/rancher
echo '/home/rancher-data /var/lib/rancher none bind 0 0' | sudo tee -a /etc/fstab
sudo mount /var/lib/rancher
df -h /var/lib/rancher  # Should show 3.6TB on rl-home
```

#### Step 4: Restore SELinux and Start Services (5 min)
```bash
sudo restorecon -Rv /var/lib/rancher /home/rancher-data
sudo systemctl start rke2-server
sleep 60
systemctl is-active rke2-server
sudo /var/lib/rancher/rke2/bin/kubectl --kubeconfig /etc/rancher/rke2/rke2.yaml get nodes
```

#### Step 5: Cleanup (after 24-48h verification)
```bash
sudo rm -rf /var/lib/rancher.old
```

### Rollback Procedure

```bash
sudo systemctl stop rke2-server
sudo umount /var/lib/rancher
sudo rmdir /var/lib/rancher
sudo mv /var/lib/rancher.old /var/lib/rancher
sudo sed -i '/rancher-data.*bind/d' /etc/fstab
sudo systemctl start rke2-server
```

### Success Criteria

| Criterion | Expected |
|-----------|----------|
| /var/lib/rancher mounted | On rl-home (3.6TB) |
| RKE2 service | active (running) |
| Kubernetes node honey | Ready |
| Root partition usage | ~68% (unchanged initially) |
| Available rancher space | ~3.2TB |

### Verification Commands

```bash
# Disk layout
df -h /var/lib/rancher
mount | grep rancher

# Service health
systemctl is-active rke2-server
sudo /var/lib/rancher/rke2/bin/kubectl --kubeconfig /etc/rancher/rke2/rke2.yaml get nodes

# GitLab runner
gitlab-runner list 2>&1
```

---

## Risk Assessment

### Identified Risks (Corrected Approach)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| RKE2 fails to start | Low | High | Keep .old backup |
| Bind mount not persistent | Low | Medium | Verify fstab entry |
| SELinux denials | Low | Medium | Run restorecon |

### Timeline

- **Total Duration**: ~15 minutes
- **RKE2 Downtime**: ~5-10 minutes
- **GitLab Runner**: No interruption needed

---

## Phase 3: Docker Volume Quota (Optional, Future)

This phase is optional and can be done later without downtime.

See original plan section for XFS project quota setup.

---

## Schedule

| Phase | Status | Duration | Downtime | Notes |
|-------|--------|----------|----------|-------|
| Phase 0 | COMPLETE | 30 min | None | Backup done |
| Phase 1 | COMPLETE | 15 min | None | Runner cache on sda |
| Phase 2 | READY | 15 min | RKE2 restart (~5-10 min) | Bind mount approach |
| Phase 3 | FUTURE | 10 min | None | Optional quota |

---

## Appendix: Quick Reference Commands

```bash
# Check disk usage
df -h / /var/lib/rancher /var/lib/gitlab-runner/cache /home

# Check LVM
sudo vgs && sudo lvs

# Check RKE2
systemctl status rke2-server
/var/lib/rancher/rke2/bin/kubectl --kubeconfig /etc/rancher/rke2/rke2.yaml get nodes

# Check GitLab Runner
systemctl status gitlab-runner
gitlab-runner list 2>&1

# Check mounts
mount | grep -E 'rancher|runner'

# Check fstab
grep -E 'rancher|runner' /etc/fstab
```

---

## Change Log

| Date | Change |
|------|--------|
| 2026-01-26 | Initial plan created |
| 2026-01-27 | Phase 1 verified complete, Phase 2 detailed plan added |
| 2026-01-27 | Updated to use runner-vg instead of shrinking rl-home (XFS limitation) |
| 2026-01-27 | **CORRECTED**: runner-vg has 0 VFree, cannot create new LV. Changed to bind mount approach from /home |
