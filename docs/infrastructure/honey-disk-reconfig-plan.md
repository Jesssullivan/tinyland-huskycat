# Honey Disk Reconfiguration Plan

**Created**: 2026-01-26
**Status**: DRAFT - Awaiting Review
**Risk Level**: Medium (requires RKE2 restart, potential data loss if done incorrectly)

## Current State

### Hardware
- **CPU**: Dual-socket (unknown model)
- **RAM**: 219GB
- **Storage**: 2x SSDs

### Disk Layout

| Disk | Size | Current Use | Notes |
|------|------|-------------|-------|
| sda | 476GB | Old Proxmox LVM | Legacy cruft, VMs not in use |
| sdb | 3.6TB | Rocky Linux | Active system disk |

### Current sdb (3.6TB) Partitioning

| Partition | Size | Mount | Purpose |
|-----------|------|-------|---------|
| sdb1 | 600MB | /boot/efi | EFI System |
| sdb2 | 1GB | /boot | Boot |
| sdb3 (LVM) | 3.6TB | - | LVM PV |

### Current LVM Layout (rl VG on sdb3)

| LV | Size | Mount | Current Use |
|----|------|-------|-------------|
| rl-root | 70GB | / | OS + RKE2 (/var/lib/rancher) |
| rl-swap | 32GB | swap | Swap |
| rl-home | 3.5TB | /home | User data + Docker (/home/docker-data) |

### Current Service Data Locations

| Service | Path | Partition | Size Used |
|---------|------|-----------|-----------|
| RKE2 | /var/lib/rancher | rl-root (/) | ~30GB |
| Docker | /home/docker-data | rl-home (/home) | ~70GB |
| GitLab Runner | /home/jess/.gitlab-runner | rl-home (/home) | ~5GB |
| GitLab Runner Cache | (none dedicated) | - | - |

## Problems with Current Setup

1. **RKE2 on root (/)**: Only 70GB, 68% used - risk of disk exhaustion
2. **Docker + RKE2 contention**: Both use overlay2, can conflict
3. **No dedicated runner cache**: Builds slower than necessary
4. **sda wasted**: 476GB of usable SSD sitting idle
5. **No separation**: All workloads compete for same I/O

## Target State

### Goal: Separation of Concerns

| Service | Dedicated Storage | Size | Source |
|---------|------------------|------|--------|
| OS + System | rl-root | 70GB | Keep as-is |
| RKE2 + K8s | New: rl-rancher | 500GB | Carve from rl-home |
| Docker | /home/docker-data | 500GB | Limit via quota |
| GitLab Runner Cache | sda (repurposed) | 476GB | Wipe sda |
| User Home | rl-home (reduced) | ~2.5TB | Remainder |

### Target LVM Layout

```
sda (476GB) - Dedicated GitLab Runner
├── runner-vg
│   └── runner-cache (476GB) → /var/lib/gitlab-runner/cache

sdb (3.6TB) - System + RKE2 + Docker
├── sdb1 (600MB) → /boot/efi
├── sdb2 (1GB) → /boot
└── sdb3 (LVM: rl VG)
    ├── rl-root (70GB) → /
    ├── rl-swap (32GB) → swap
    ├── rl-rancher (500GB) → /var/lib/rancher [NEW]
    └── rl-home (~2.9TB) → /home (reduced)
```

## Implementation Phases

### Phase 0: Preparation (No Changes)

**Estimated Time**: 30 minutes

1. **Backup current configs**
   ```bash
   mkdir -p /home/jess/honey-backup-$(date +%Y%m%d)
   cp -a /etc/docker /home/jess/honey-backup-$(date +%Y%m%d)/
   cp -a /etc/rancher /home/jess/honey-backup-$(date +%Y%m%d)/
   cp -a /var/lib/rancher/rke2/server/manifests /home/jess/honey-backup-$(date +%Y%m%d)/
   tar czf /home/jess/honey-backup-$(date +%Y%m%d)/gitlab-runner.tar.gz /etc/gitlab-runner /home/jess/.gitlab-runner
   ```

2. **Document current state**
   ```bash
   lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE > /home/jess/honey-backup-$(date +%Y%m%d)/lsblk.txt
   vgdisplay > /home/jess/honey-backup-$(date +%Y%m%d)/vgdisplay.txt
   lvdisplay > /home/jess/honey-backup-$(date +%Y%m%d)/lvdisplay.txt
   pvdisplay > /home/jess/honey-backup-$(date +%Y%m%d)/pvdisplay.txt
   df -h > /home/jess/honey-backup-$(date +%Y%m%d)/df.txt
   ```

3. **Verify sda is not in use**
   ```bash
   # Check for active mounts
   mount | grep sda
   # Check for active LVM
   pvs | grep sda
   lvs | grep pve
   # Check for processes using old PVE paths
   lsof +D /dev/pve-OLD-53B0DA72 2>/dev/null
   ```

### Phase 1: Repurpose sda for GitLab Runner Cache

**Estimated Time**: 15 minutes
**Risk**: LOW (sda is unused)
**Rollback**: Remove new VG, no other changes needed

1. **Wipe old Proxmox LVM**
   ```bash
   # Deactivate all LVs in old VG
   sudo vgchange -an pve-OLD-53B0DA72

   # Remove the VG
   sudo vgremove -f pve-OLD-53B0DA72

   # Remove the PV
   sudo pvremove /dev/sda3

   # Wipe partition table
   sudo wipefs -a /dev/sda
   ```

2. **Create new partition and LVM for runner cache**
   ```bash
   # Create single partition
   sudo parted /dev/sda --script mklabel gpt
   sudo parted /dev/sda --script mkpart primary 0% 100%

   # Create PV
   sudo pvcreate /dev/sda1

   # Create VG
   sudo vgcreate runner-vg /dev/sda1

   # Create LV
   sudo lvcreate -l 100%FREE -n runner-cache runner-vg

   # Format
   sudo mkfs.xfs /dev/runner-vg/runner-cache
   ```

3. **Mount and configure**
   ```bash
   # Create mount point
   sudo mkdir -p /var/lib/gitlab-runner/cache

   # Add to fstab
   echo '/dev/runner-vg/runner-cache /var/lib/gitlab-runner/cache xfs defaults,noatime 0 2' | sudo tee -a /etc/fstab

   # Mount
   sudo mount /var/lib/gitlab-runner/cache

   # Set permissions
   sudo chown -R gitlab-runner:gitlab-runner /var/lib/gitlab-runner/cache
   ```

4. **Update GitLab Runner config**
   ```bash
   # Edit /etc/gitlab-runner/config.toml
   # Add cache configuration pointing to /var/lib/gitlab-runner/cache
   ```

**Rollback Phase 1**:
```bash
sudo umount /var/lib/gitlab-runner/cache
sudo lvremove -f runner-vg/runner-cache
sudo vgremove runner-vg
sudo pvremove /dev/sda1
# Remove fstab entry
```

### Phase 2: Create Dedicated RKE2 Volume

**Estimated Time**: 45 minutes (includes RKE2 restart)
**Risk**: MEDIUM (requires RKE2 stop/start, data migration)
**Rollback**: Restore from backup, revert bind mount

1. **Stop RKE2 and Docker**
   ```bash
   sudo systemctl stop gitlab-runner
   sudo systemctl stop docker
   sudo systemctl stop rke2-server  # or rke2-agent
   ```

2. **Shrink rl-home to make space**
   ```bash
   # Unmount /home (requires single-user or rescue mode)
   # This is the risky part - must be done carefully

   # Option A: Online resize (if supported)
   # XFS cannot shrink online - must use Option B

   # Option B: Create new LV from free space in VG
   # Check free space first
   sudo vgs rl

   # If no free space, we need to:
   # 1. Backup /home/docker-data
   # 2. Delete some data from /home
   # 3. Shrink rl-home in rescue mode
   ```

3. **Create rl-rancher LV** (if space available)
   ```bash
   sudo lvcreate -L 500G -n rl-rancher rl
   sudo mkfs.xfs /dev/rl/rl-rancher
   ```

4. **Migrate RKE2 data**
   ```bash
   # Mount new volume temporarily
   sudo mkdir -p /mnt/new-rancher
   sudo mount /dev/rl/rl-rancher /mnt/new-rancher

   # Copy data
   sudo rsync -avP /var/lib/rancher/ /mnt/new-rancher/

   # Verify
   sudo diff -r /var/lib/rancher /mnt/new-rancher

   # Unmount
   sudo umount /mnt/new-rancher
   ```

5. **Update fstab and mount**
   ```bash
   # Backup original
   sudo mv /var/lib/rancher /var/lib/rancher.old
   sudo mkdir /var/lib/rancher

   # Add to fstab
   echo '/dev/rl/rl-rancher /var/lib/rancher xfs defaults,noatime 0 2' | sudo tee -a /etc/fstab

   # Mount
   sudo mount /var/lib/rancher
   ```

6. **Start services**
   ```bash
   sudo systemctl start rke2-server  # or rke2-agent
   # Wait for RKE2 to be healthy
   sudo /var/lib/rancher/rke2/bin/kubectl --kubeconfig /etc/rancher/rke2/rke2.yaml get nodes

   sudo systemctl start docker
   sudo systemctl start gitlab-runner
   ```

7. **Cleanup old data**
   ```bash
   # Only after confirming everything works
   sudo rm -rf /var/lib/rancher.old
   ```

**Rollback Phase 2**:
```bash
sudo systemctl stop rke2-server
sudo umount /var/lib/rancher
sudo rm -rf /var/lib/rancher
sudo mv /var/lib/rancher.old /var/lib/rancher
# Remove fstab entry
sudo systemctl start rke2-server
```

### Phase 3: Docker Volume Quota (Optional)

**Estimated Time**: 10 minutes
**Risk**: LOW

1. **Set XFS project quota on /home/docker-data**
   ```bash
   # Enable project quotas on /home (requires remount)
   # Add 'prjquota' to /etc/fstab for /home

   # Create project
   echo "1:/home/docker-data" | sudo tee -a /etc/projects
   echo "docker:1" | sudo tee -a /etc/projid

   # Set 500GB limit
   sudo xfs_quota -x -c 'project -s docker' /home
   sudo xfs_quota -x -c 'limit -p bhard=500g docker' /home
   ```

## Verification Checklist

After each phase:

- [ ] All services started successfully
- [ ] `kubectl get nodes` shows Ready
- [ ] `docker info` shows correct paths
- [ ] GitLab runner picks up jobs
- [ ] No errors in `journalctl -u rke2-server`
- [ ] No errors in `journalctl -u docker`
- [ ] Disk usage as expected (`df -h`)

## Schedule

| Phase | When | Duration | Downtime |
|-------|------|----------|----------|
| Phase 0 | Anytime | 30 min | None |
| Phase 1 | Anytime | 15 min | None |
| Phase 2 | Maintenance window | 45 min | RKE2 restart |
| Phase 3 | Anytime | 10 min | None |

## Emergency Contacts

- RKE2 Issues: Check `/var/lib/rancher/rke2/server/logs/`
- Docker Issues: `journalctl -u docker -f`
- Disk Issues: `dmesg | tail -50`

## Notes

- Phase 2 is the most complex and risky
- Consider doing Phase 2 during a maintenance window
- Have console access ready (not just SSH) in case of boot issues
- The 476GB sda as runner cache will significantly speed up CI builds
