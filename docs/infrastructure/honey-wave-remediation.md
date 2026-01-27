# Honey Infrastructure Remediation Plan

## Waveguide Execution: 2 Waves, 6 Agents

**Target**: honey.tinyland.ts (100.77.196.50)
**Platform**: Rocky Linux 10, Dual Socket Xeons, 22GB+ RAM
**Role**: Primary CI/CD build machine for Tinyland lab

---

## Problem Statement

Honey is experiencing severe I/O contention due to:
1. **RKE2 + Docker coexistence** - documented incompatibility
2. **Shared root filesystem** - all workloads hitting 70GB rl-root
3. **inotify exhaustion risk** - cgroupv2 creates 1 instance per container
4. **cgroup driver mismatch** - Docker uses cgroupfs, RKE2 uses systemd

**Impact**: 15-16% I/O wait, load average 17+, 10 pipelines stuck/slow

---

## Wave 1: Immediate Stabilization

**Goal**: Reduce I/O contention without service disruption
**Duration**: ~30 minutes
**Risk Level**: LOW

### Agent 1.1: System Tuning Specialist

**Focus**: Apply sysctl and ulimit fixes for immediate relief

**Tasks**:
1. Increase inotify limits:
   ```bash
   sudo tee /etc/sysctl.d/99-container-limits.conf << 'EOF'
   fs.file-max = 2097152
   fs.nr_open = 1048576
   fs.inotify.max_user_watches = 524288
   fs.inotify.max_user_instances = 512
   net.core.somaxconn = 65535
   EOF
   sudo sysctl -p /etc/sysctl.d/99-container-limits.conf
   ```

2. Increase systemd service limits:
   ```bash
   sudo mkdir -p /etc/systemd/system/docker.service.d
   sudo tee /etc/systemd/system/docker.service.d/limits.conf << 'EOF'
   [Service]
   LimitNOFILE=1048576
   LimitNPROC=infinity
   LimitCORE=infinity
   EOF

   sudo mkdir -p /etc/systemd/system/rke2-server.service.d
   sudo tee /etc/systemd/system/rke2-server.service.d/limits.conf << 'EOF'
   [Service]
   LimitNOFILE=1048576
   LimitNPROC=infinity
   LimitCORE=infinity
   EOF

   sudo systemctl daemon-reload
   ```

3. Verify limits applied:
   ```bash
   cat /proc/sys/fs/inotify/max_user_instances
   grep "Max open files" /proc/$(pgrep -x dockerd)/limits
   ```

**Success Criteria**:
- [ ] inotify.max_user_instances = 512
- [ ] Docker/RKE2 LimitNOFILE = 1048576
- [ ] No service restarts required for sysctl

---

### Agent 1.2: cgroup Alignment Specialist

**Focus**: Align Docker and RKE2 cgroup drivers to reduce conflicts

**Tasks**:
1. Check current cgroup configuration:
   ```bash
   docker info | grep -i cgroup
   cat /sys/fs/cgroup/cgroup.controllers  # cgroupv2 check
   ```

2. Configure Docker to use systemd cgroup driver:
   ```bash
   sudo tee /etc/docker/daemon.json << 'EOF'
   {
     "data-root": "/home/docker-data",
     "storage-driver": "overlay2",
     "exec-opts": ["native.cgroupdriver=systemd"],
     "cgroup-parent": "docker.slice",
     "log-driver": "json-file",
     "log-opts": {
       "max-size": "100m",
       "max-file": "3"
     },
     "default-ulimits": {
       "nofile": {
         "Name": "nofile",
         "Hard": 65536,
         "Soft": 65536
       }
     }
   }
   EOF
   ```

3. Restart Docker (during low-activity window):
   ```bash
   sudo systemctl restart docker
   docker info | grep -i cgroup  # Verify: "Cgroup Driver: systemd"
   ```

**Success Criteria**:
- [ ] Docker Cgroup Driver = systemd
- [ ] RKE2 Cgroup Driver = systemd (already default)
- [ ] No cgroup accounting errors in journalctl

---

### Agent 1.3: Wave 1 Gap Analyst

**Focus**: Verify stabilization before Phase 2

**Wait Period**: 5 minutes after Agents 1.1 and 1.2 complete

**Verification Tasks**:
1. System metrics check:
   ```bash
   vmstat 1 5  # I/O wait should decrease
   uptime      # Load average should stabilize
   ```

2. Service health:
   ```bash
   systemctl status docker rke2-server
   docker ps | wc -l
   kubectl get pods -A --no-headers | wc -l
   ```

3. Pipeline check:
   ```bash
   gitlab-runner list 2>&1
   # Check if jobs are progressing
   ```

**GO/NO-GO Criteria**:
| Criterion | GO | NO-GO |
|-----------|-----|-------|
| I/O wait | < 10% | > 20% |
| Load average | < 10 | > 20 |
| Docker running | Yes | No |
| RKE2 running | Yes | No |
| Runners responding | Yes | No |

**Decision**:
- **GO**: Proceed to Wave 2 (RKE2 volume separation)
- **CONDITIONAL**: Proceed with caution, monitor closely
- **NO-GO**: Rollback sysctl changes, investigate further

---

## Wave 2: Storage Isolation

**Goal**: Separate RKE2 data to dedicated volume
**Duration**: ~45 minutes
**Risk Level**: MEDIUM
**Prerequisite**: Wave 1 GO decision

### Agent 2.1: LVM Preparation Specialist

**Focus**: Create dedicated logical volume for RKE2

**Tasks**:
1. Check available space in runner-vg:
   ```bash
   sudo vgdisplay runner-vg
   sudo lvs runner-vg
   ```

2. Create RKE2 logical volume (50GB initial):
   ```bash
   sudo lvcreate -L 50G -n rancher runner-vg
   sudo mkfs.xfs /dev/runner-vg/rancher
   ```

3. Create mount point and test mount:
   ```bash
   sudo mkdir -p /mnt/rancher-new
   sudo mount /dev/runner-vg/rancher /mnt/rancher-new
   df -h /mnt/rancher-new
   ```

**Success Criteria**:
- [ ] LV created: /dev/runner-vg/rancher
- [ ] Filesystem: XFS
- [ ] Test mount successful

---

### Agent 2.2: RKE2 Migration Specialist

**Focus**: Migrate RKE2 data to new volume with minimal downtime

**CRITICAL**: This requires RKE2 downtime. Schedule during low-activity period.

**Tasks**:
1. Pre-migration backup:
   ```bash
   sudo tar -czf /home/rancher-backup-$(date +%Y%m%d).tar.gz /var/lib/rancher
   ```

2. Stop RKE2:
   ```bash
   sudo systemctl stop rke2-server
   sleep 10
   sudo systemctl status rke2-server  # Confirm stopped
   ```

3. Sync data to new volume:
   ```bash
   sudo rsync -avP /var/lib/rancher/ /mnt/rancher-new/
   ```

4. Update mount configuration:
   ```bash
   # Move old directory
   sudo mv /var/lib/rancher /var/lib/rancher.old

   # Create new mount point
   sudo mkdir -p /var/lib/rancher

   # Add to fstab
   echo '/dev/runner-vg/rancher /var/lib/rancher xfs defaults 0 0' | sudo tee -a /etc/fstab

   # Mount
   sudo umount /mnt/rancher-new
   sudo mount /var/lib/rancher
   ```

5. Start RKE2:
   ```bash
   sudo systemctl start rke2-server
   sleep 30
   sudo systemctl status rke2-server
   kubectl get nodes
   kubectl get pods -A
   ```

6. Cleanup (after verification):
   ```bash
   # Only after confirmed working for 1+ hour
   sudo rm -rf /var/lib/rancher.old
   sudo rmdir /mnt/rancher-new
   ```

**Rollback Procedure**:
```bash
sudo systemctl stop rke2-server
sudo umount /var/lib/rancher
sudo rmdir /var/lib/rancher
sudo mv /var/lib/rancher.old /var/lib/rancher
# Remove fstab entry
sudo systemctl start rke2-server
```

**Success Criteria**:
- [ ] RKE2 running on new volume
- [ ] All pods healthy
- [ ] kubectl commands responsive

---

### Agent 2.3: Wave 2 Gap Analyst

**Focus**: Final verification and performance assessment

**Wait Period**: 10 minutes after RKE2 migration

**Verification Tasks**:
1. Storage isolation confirmed:
   ```bash
   df -h | grep -E "(rancher|runner-cache|root)"
   # Should show 3 separate mount points
   ```

2. I/O separation test:
   ```bash
   # Run during CI activity
   iostat -x 5 3
   # Look for separate I/O on different devices
   ```

3. Performance comparison:
   ```bash
   vmstat 1 10
   # Compare to pre-remediation baseline
   ```

4. CI pipeline test:
   ```bash
   # Trigger a test pipeline
   # Monitor job pickup and execution time
   ```

**Final Assessment**:
| Metric | Before | After | Target |
|--------|--------|-------|--------|
| I/O wait % | 15-16% | ? | < 5% |
| Load average | 17+ | ? | < 5 |
| Root usage | 68% | ? | < 60% |
| Pipeline time | Stuck | ? | Normal |

**Decision**:
- **GO**: Remediation complete, document and close
- **CONDITIONAL**: Working but needs monitoring
- **NO-GO**: Rollback required, escalate

---

## Execution Schedule

### Recommended Window
- **Day**: Weekday evening or weekend
- **Duration**: 2-3 hours total
- **Notification**: Alert team before starting

### Sequence
```
T+0:00  - Wave 1 start
T+0:15  - Agent 1.1 complete (sysctl)
T+0:25  - Agent 1.2 complete (cgroup)
T+0:30  - Agent 1.3 Gap Analysis
T+0:35  - Wave 1 GO/NO-GO decision

T+0:40  - Wave 2 start (if GO)
T+0:50  - Agent 2.1 complete (LVM)
T+1:30  - Agent 2.2 complete (migration)
T+1:40  - Agent 2.3 Gap Analysis
T+1:50  - Wave 2 GO/NO-GO decision

T+2:00  - Monitoring period begins
T+3:00  - Final sign-off
```

---

## Risk Mitigation

### Wave 1 Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Docker restart fails | Low | High | Test daemon.json syntax first |
| sysctl breaks networking | Very Low | Medium | Changes are conservative |

### Wave 2 Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| RKE2 won't start after move | Low | High | Full backup, tested rollback |
| Data corruption during rsync | Very Low | Critical | Use rsync checksums |
| Space exhaustion on new LV | Low | Medium | Monitor, can resize LV |

---

## Post-Remediation Monitoring

### Daily Checks (Week 1)
```bash
# Quick health check script
ssh honey "uptime && vmstat 1 3 | tail -3 && df -h | grep -E '(rancher|runner|root)'"
```

### Alerts to Configure
- Root partition > 80%
- I/O wait > 10% sustained
- RKE2 service restarts
- Docker service restarts

---

## References

- RKE2 Known Issues: https://docs.rke2.io/known_issues
- Docker cgroup driver: https://docs.docker.com/engine/daemon/
- Linux inotify limits: https://www.baeldung.com/linux/inotify-upper-limit-reached
- Previous plan: docs/infrastructure/honey-disk-reconfig-plan.md
