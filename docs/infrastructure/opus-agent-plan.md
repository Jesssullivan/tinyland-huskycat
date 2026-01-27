# Infrastructure Opus Agent Execution Plan

**Created**: 2026-01-27
**Status**: READY FOR EXECUTION - Research complete
**Last Updated**: 2026-01-27 09:30 EST

## Executive Summary

This plan coordinates 2 phases of 2 Opus agents each to address:
1. HuskyCat CI pipeline optimization and stabilization
2. Attic-cache Nix binary cache deployment
3. Honey server infrastructure improvements
4. Cross-cutting integration and monitoring

### Key Research Findings

| Area | Finding | Impact |
|------|---------|--------|
| **Honey Phase 1** | ALREADY COMPLETE - runner-cache volume exists (477GB) | Agent 2.2 scope reduced |
| **Shellcheck** | Optimized: 624s → 13.4s (46x faster) | CI builds faster |
| **ContainerFile** | /go/bin typo fixed (commit 1b313ad) | Build should pass |
| **Attic Blockers** | CNPG CRDs missing, ingress_class wrong, Cloudflare provider issue | Phase 1.2 critical |
| **K8s Control Plane** | CrashLoopBackOff on kube-controller-manager/scheduler | Monitor but don't block |
| **RKE2 Data** | Only 558MB (not 30GB estimated) | Phase 2 disk migration less urgent |

---

## Research Agent Results (All Complete)

| Agent ID | Focus Area | Status | Key Findings |
|----------|------------|--------|--------------|
| a813f0d | HuskyCat CI | COMPLETE | Docker: 67GB images, 29GB build cache; shellcheck optimization working |
| a1761d1 | Attic-cache | COMPLETE | 3 blockers: CNPG CRDs, ingress_class, Cloudflare provider |
| aa655f3 | Honey Server | COMPLETE | Phase 1 done; RKE2 only 558MB; K8s control plane issues |
| a2abf45 | Cross-cutting | COMPLETE | Runner architecture mapped; MCP topology documented |
| ac5985e | Pipeline Monitor | COMPLETE | Found /go/bin typo causing build failure |

---

## Phase 1: Foundation & CI Stabilization

**Objective**: Stabilize CI infrastructure and prepare deployment prerequisites

### Agent 1.1: CI Pipeline Optimizer
**Focus**: HuskyCat CI/CD pipeline optimization

**Tasks**:
1. **ContainerFile Optimization** (PARTIALLY COMPLETE)
   - [x] Replace shellcheck apk install with binary download (13.4s vs 624s)
   - [x] Fix /go/bin typo (commit 1b313ad)
   - [ ] Implement layer caching improvements
   - [ ] Add build timing instrumentation

2. **CI Configuration Cleanup**
   - [ ] Remove any remaining SaaS runner references
   - [ ] Standardize runner tag requirements across all jobs
   - [ ] Add retry logic for transient failures

3. **Runner Infrastructure Validation**
   - [ ] Verify honey DinD runner configuration
   - [ ] Check Docker cleanup and disk space (67GB images, 45GB reclaimable)
   - [ ] Validate concurrent job limits

**Inputs** (from research):
- ContainerFile: Binary downloads working, typo fixed
- Docker resources: 67GB images, 29GB build cache, 45GB reclaimable
- Runner tags: `dind`, `x86_64` for Linux builds

**Outputs**:
- Optimized ContainerFile (verify build passes)
- Updated CI configuration files
- Runner health verification report

### Agent 1.2: Kubernetes Prerequisite Installer
**Focus**: Prepare Civo cluster for Attic deployment

**CRITICAL BLOCKERS IDENTIFIED**:

1. **CloudNativePG CRDs Missing**
   ```bash
   # CRDs not installed - tofu plan fails
   kubectl get crd clusters.postgresql.cnpg.io
   # Error: the server doesn't have a resource type "clusters"
   ```

2. **Ingress Class Mismatch**
   ```hcl
   # terraform.tfvars has:
   ingress_class = "traefik"
   # But cluster only has nginx:
   kubectl get ingressclass
   # NAME    CONTROLLER             PARAMETERS   AGE
   # nginx   k8s.io/ingress-nginx   <none>       38d
   ```

3. **Cloudflare Provider Issue**
   ```hcl
   # main.tf requires Cloudflare API token even when dns_provider="external-dns"
   # Need conditional provider loading
   ```

**Tasks**:
1. **CloudNativePG Operator Installation**
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.22/releases/cnpg-1.22.0.yaml
   kubectl wait --for=condition=available deployment/cnpg-controller-manager -n cnpg-system --timeout=120s
   ```

2. **Provider Configuration Fix**
   - Add conditional Cloudflare provider to main.tf
   - Make DNS module work with external-dns only
   - Test tofu plan succeeds

3. **Cluster Prerequisites Verification**
   - [x] cert-manager: Installed (fuzzy-dev namespace)
   - [ ] external-dns: Needs verification
   - [x] nginx ingress: Installed (not traefik)

**Outputs**:
- CNPG operator deployed and healthy
- Fixed provider configuration (PR to attic-cache)
- terraform.tfvars corrected: `ingress_class = "nginx"`

---

## Phase 2: Deployment & Integration

**Objective**: Deploy Attic cache and complete infrastructure improvements

### Agent 2.1: Attic Deployment Executor
**Focus**: Complete Attic Nix binary cache deployment

**Prerequisites** (from Phase 1.2):
- [x] CNPG operator installed
- [x] ingress_class corrected to "nginx"
- [x] Cloudflare provider made conditional

**Tasks**:
1. **Tofu Apply Execution**
   ```bash
   cd /home/jsullivan2/git/attic-cache/tofu/stacks/attic
   tofu init
   tofu plan -out=tfplan
   tofu apply tfplan
   ```

2. **Token Generation & Distribution**
   - Generate CI tokens for repositories
   - Create root admin token
   - Store tokens in GitLab CI variables

3. **DNS & TLS Configuration**
   - Verify DNS record: nix-cache.fuzzy-dev.tinyland.dev
   - Validate TLS certificate issuance (Let's Encrypt)
   - Test HTTPS access

**Outputs**:
- Attic deployment complete
- Tokens generated and stored
- nix-cache.fuzzy-dev.tinyland.dev accessible

### Agent 2.2: Honey Infrastructure Monitor (SCOPE REDUCED)
**Focus**: Monitor and optimize honey server (disk migration mostly complete)

**STATUS UPDATE**: Phase 1 disk migration ALREADY COMPLETE
- sda repurposed as GitLab Runner cache: `/var/lib/gitlab-runner/cache` (477GB)
- runner-vg/runner-cache LV active and mounted
- fstab entry present with noatime option

**Remaining Tasks**:
1. **Monitor K8s Control Plane Issues**
   - kube-controller-manager: CrashLoopBackOff (1174 restarts)
   - kube-scheduler: CrashLoopBackOff (1148 restarts)
   - Investigate root cause (may be blahaj node NotReady)

2. **Docker Cleanup**
   ```bash
   ssh honey "docker system prune -af --volumes"
   # Expected reclaim: ~45GB
   ```

3. **Phase 2 Disk Migration (DEFERRED)**
   - RKE2 data only 558MB (not 30GB estimated)
   - Root partition at 68% - stable
   - Only proceed if root exceeds 80%

**Outputs**:
- K8s control plane health report
- Docker cleanup executed
- Phase 2 disk migration deferred unless needed

---

## Dependency Graph

```
Phase 1 (Run in Parallel):
  Agent 1.1 (CI Optimizer) ──────────► CI stable, builds passing
  Agent 1.2 (K8s Prereqs)  ──────────► Cluster ready for Attic

                    │
                    ▼ (wait for both)

Phase 2 (Run in Parallel):
  Agent 2.1 (Attic Deploy) ──────────► Nix cache live
  Agent 2.2 (Honey Monitor) ─────────► Infrastructure optimized
```

---

## Risk Assessment (Updated)

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| CNPG operator install fails | Blocks Attic | Low | Use Neon external DB as fallback |
| K8s control plane unstable | Medium | Current | Monitor, don't block on fix |
| CI build still fails | Medium | Low | /go/bin fix should resolve |
| ingress_class mismatch | Blocks Attic | Resolved | Change traefik→nginx |
| Cloudflare provider error | Blocks tofu | Medium | Add conditional provider |

---

## Execution Commands

### Phase 1.1: CI Optimizer
```bash
# Verify container build passes (background monitor running)
glab ci status --live | grep container:build

# If still failing, check job logs
glab ci view --job container:build:amd64

# Runner cleanup (if needed)
ssh honey "docker system prune -af --volumes"
```

### Phase 1.2: K8s Prerequisites
```bash
# Install CNPG operator
kubectl apply -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.22/releases/cnpg-1.22.0.yaml

# Verify installation
kubectl get pods -n cnpg-system
kubectl get crd | grep cnpg

# Fix terraform.tfvars
cd ~/git/attic-cache/tofu/stacks/attic
sed -i 's/ingress_class = "traefik"/ingress_class = "nginx"/' terraform.tfvars

# Test tofu plan
tofu plan
```

### Phase 2.1: Attic Deployment
```bash
cd ~/git/attic-cache/tofu/stacks/attic
tofu init
tofu plan -out=tfplan
tofu apply tfplan

# Verify deployment
kubectl get pods -n attic
curl -s https://nix-cache.fuzzy-dev.tinyland.dev/health
```

### Phase 2.2: Honey Monitoring
```bash
# Check K8s control plane
ssh honey "KUBECONFIG=/etc/rancher/rke2/rke2.yaml kubectl get pods -n kube-system | grep -E 'controller|scheduler'"

# Check disk usage
ssh honey "df -h / /var/lib/gitlab-runner/cache"

# Docker cleanup
ssh honey "docker system df"
```

---

## Notes

- Phase 2.2 disk migration DEFERRED - Phase 1 already complete, RKE2 only 558MB
- K8s control plane issues on honey should be investigated but don't block Attic deployment
- Background pipeline monitor (ab9d05c) watching container:build:amd64
- All research agents completed successfully

---

*Plan ready for Phase 1 agent execution.*
