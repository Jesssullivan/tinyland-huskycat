# HuskyCat Next Steps: Beta Testing & Distribution
**Last Updated**: 2026-01-18
**Status**: PLANNING
**Scope**: Beta tester workflows, installation flows, IPC integration, Darwin packaging

---

## Executive Summary

HuskyCat v0.9 is feature-complete for beta testing. This document outlines next steps for:

| Area | Priority | Status | Blocking |
|------|----------|--------|----------|
| Beta Testing Workflow | **HIGH** | Ready | None |
| Binary Installation Flow | **HIGH** | Working | None |
| Container Installation Flow | **MEDIUM** | Working | None |
| UV Development Flow | **LOW** | Working | None |
| GPL Sidecar IPC Integration | **MEDIUM** | Partial | Integration needed |
| Darwin Code Signing | **HIGH** | Not started | Apple Developer Account |
| Darwin Notarization | **HIGH** | Not started | Code signing required |

---

## Part 1: Beta Testing Workflow

### 1.1 Current Beta Testing Documentation

**Source of truth**: `docs/BETA_TESTING.md` (396 lines)

Already covers:
- One-line installer (`curl ... | sh`)
- Binary download links by platform
- Troubleshooting common issues
- Bug report templates

### 1.2 Beta Tester Onboarding Checklist

```markdown
## Beta Tester Quickstart

1. **Install HuskyCat** (choose one):
   ```bash
   # Option A: One-line installer (recommended)
   curl -sSL https://huskycat.dev/install.sh | sh

   # Option B: Direct download
   # macOS Apple Silicon:
   curl -LO https://gitlab.com/tinyland/ai/huskycat/-/releases/download/v0.9.0/huskycat-darwin-arm64
   chmod +x huskycat-darwin-arm64
   sudo mv huskycat-darwin-arm64 /usr/local/bin/huskycat

   # Linux x86_64:
   curl -LO https://gitlab.com/tinyland/ai/huskycat/-/releases/download/v0.9.0/huskycat-linux-amd64
   chmod +x huskycat-linux-amd64
   sudo mv huskycat-linux-amd64 /usr/local/bin/huskycat
   ```

2. **Verify installation**:
   ```bash
   huskycat --version
   huskycat status
   ```

3. **Set up git hooks** (optional):
   ```bash
   huskycat setup-hooks
   ```

4. **Run validation**:
   ```bash
   huskycat validate .
   huskycat validate --staged  # For git commits
   ```

5. **Report issues**: https://gitlab.com/tinyland/ai/huskycat/-/issues
```

### 1.3 Beta Testing Metrics to Track

| Metric | Collection Method | Goal |
|--------|-------------------|------|
| Installation success rate | Issue reports | >95% |
| First-run experience | Survey | "Easy" rating >4/5 |
| Git hooks adoption | Optional telemetry | >50% of users |
| Crash/error rate | Error logging | <1% of runs |
| Performance (validate time) | Timing data | <3s for typical project |

### 1.4 Beta Testing Phases

**Phase 1: Internal Dogfooding** (Current)
- HuskyCat validates itself
- Tinyland team projects
- Goal: Verify core functionality

**Phase 2: Closed Beta** (Next)
- 10-20 external testers
- Focus: Installation friction, edge cases
- Duration: 2 weeks

**Phase 3: Open Beta** (After Phase 2)
- Public announcement
- Focus: Scale, diverse environments
- Duration: 4 weeks

---

## Part 2: Installation Flows by Execution Model

### 2.1 Binary Execution (Recommended)

**Target users**: Developers wanting fast git hooks

```
┌──────────────────────────────────────────────────────────────┐
│                    BINARY INSTALLATION                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  curl -sSL install.sh | sh                                   │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │ Detect Platform │                                        │
│  │ darwin-arm64    │                                        │
│  │ darwin-amd64    │                                        │
│  │ linux-amd64     │                                        │
│  │ linux-arm64     │                                        │
│  └────────┬────────┘                                        │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │ Download Binary │───▶│ ~/.local/bin/   │                │
│  │ (~30MB)         │    │ huskycat        │                │
│  └────────┬────────┘    └─────────────────┘                │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │ Extract Tools   │───▶│ ~/.huskycat/    │                │
│  │ (first run)     │    │ tools/          │                │
│  └────────┬────────┘    │   ruff          │                │
│           │             │   mypy          │                │
│           ▼             │   black         │                │
│  ┌─────────────────┐    │   taplo         │                │
│  │ huskycat status │    │   etc.          │                │
│  │ (verify)        │    └─────────────────┘                │
│  └─────────────────┘                                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Code references**:
- Binary entry: `huskycat_main.py:1-50`
- Tool extraction: `unified_validation.py:1870-1920`
- First-run detection: `unified_validation.py:128-148`

**Pros**:
- Single file (~30MB)
- No Python required
- Fast startup (~100ms)
- All bundled tools included

**Cons**:
- No GPL tools (shellcheck, hadolint, yamllint)
- Larger download than package managers
- Updates require re-download

### 2.2 Container Execution

**Target users**: CI pipelines, comprehensive validation

```
┌──────────────────────────────────────────────────────────────┐
│                   CONTAINER INSTALLATION                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  podman pull ghcr.io/tinyland/huskycat:latest                │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │ Main Container  │  ~20MB (thin wrapper)                  │
│  │ huskycat:latest │                                        │
│  └────────┬────────┘                                        │
│           │                                                  │
│           ├────────────────────────────────────────┐        │
│           │                                        │        │
│           ▼                                        ▼        │
│  ┌─────────────────┐                    ┌─────────────────┐ │
│  │ Bundle Tools    │                    │ GPL Sidecar     │ │
│  │ (Apache/MIT)    │                    │ (Optional)      │ │
│  │                 │                    │                 │ │
│  │ ruff, mypy,     │      IPC           │ shellcheck,     │ │
│  │ black, taplo    │◀──────────────────▶│ hadolint,       │ │
│  │                 │   Unix socket      │ yamllint        │ │
│  └─────────────────┘                    └─────────────────┘ │
│                                                              │
│  Usage:                                                      │
│  podman run -v $(pwd):/workspace huskycat validate .         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Code references**:
- Container build: `.gitlab-ci.yml:158-218`
- Container detection: `unified_validation.py:85-170`
- GPL sidecar: `gpl-sidecar/server.py:1-313`

**Pros**:
- Consistent environment
- Includes GPL tools (with sidecar)
- Multi-arch support (amd64, arm64)
- CI-ready

**Cons**:
- Requires container runtime
- Slower startup (~500ms)
- Volume mounts required

### 2.3 UV Development Mode

**Target users**: Contributors, customization

```
┌──────────────────────────────────────────────────────────────┐
│                   UV DEVELOPMENT MODE                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  git clone https://gitlab.com/tinyland/ai/huskycat.git       │
│  cd huskycat && uv sync                                      │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │ UV Environment  │                                        │
│  │ .venv/          │                                        │
│  └────────┬────────┘                                        │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │ Python Packages │    │ System Tools    │                │
│  │ (pyproject.toml)│    │ (PATH lookup)   │                │
│  └────────┬────────┘    └────────┬────────┘                │
│           │                      │                          │
│           ▼                      ▼                          │
│  ┌─────────────────────────────────────────┐               │
│  │     uv run python -m huskycat           │               │
│  │     npm run dev -- validate .           │               │
│  └─────────────────────────────────────────┘               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Code references**:
- Entry point: `src/huskycat/__main__.py:242-296`
- npm scripts: `package.json:8-38`
- Mode detection: `core/mode_detector.py:31-82`

**Pros**:
- Full development environment
- Source modification possible
- All tests and docs available
- npm scripts for common tasks

**Cons**:
- Requires Python 3.10+, UV, npm
- Longer setup time
- Not for end users

---

## Part 3: GPL Sidecar IPC Integration

### 3.1 Current State

| Component | Status | Location |
|-----------|--------|----------|
| IPC Client | ✅ Complete | `src/huskycat/core/gpl_client.py:1-342` |
| IPC Server | ✅ Complete | `gpl-sidecar/server.py:1-313` |
| Container | ✅ Complete | `ContainerFile.gpl-sidecar` |
| Integration | ❌ Not started | `unified_validation.py` needs update |

### 3.2 Integration Plan

**Goal**: When sidecar is available, use it for GPL tools instead of skipping.

```python
# unified_validation.py - proposed integration
from huskycat.core.gpl_client import is_sidecar_available, execute_gpl_tool

class YamlLintValidator(BaseValidator):
    def is_available(self) -> bool:
        # Current: always False in FAST mode
        # New: check sidecar availability
        if self.linting_mode == LintingMode.FAST:
            return is_sidecar_available()
        return True  # Container mode

    def _run_tool(self, file_path: str) -> ValidationResult:
        if is_sidecar_available():
            result = execute_gpl_tool("yamllint", [file_path])
            return self._parse_result(result)
        else:
            return self._run_container(file_path)
```

### 3.3 Integration Tasks

1. **Add sidecar detection** in `unified_validation.py`
   - Import `is_sidecar_available` from `gpl_client`
   - Modify `is_available()` for GPL validators

2. **Route execution** based on context
   - Sidecar available → IPC execution
   - Container context → Direct execution
   - Neither → Skip tool

3. **Add sidecar startup instructions**
   - Document manual startup: `python3 gpl-sidecar/server.py &`
   - Document container startup: `podman-compose up -d gpl-sidecar`

4. **Test coverage**
   - Unit tests: `tests/test_gpl_sidecar.py` (exists)
   - Integration tests: sidecar + validation engine

### 3.4 Sidecar Container Compose

```yaml
# docker-compose.yml or podman-compose.yml
services:
  huskycat:
    image: ghcr.io/tinyland/huskycat:latest
    volumes:
      - .:/workspace
      - huskycat-ipc:/ipc

  gpl-sidecar:
    image: ghcr.io/tinyland/huskycat-gpl:latest
    volumes:
      - .:/workspace
      - huskycat-ipc:/ipc
    command: ["--socket", "/ipc/huskycat-gpl.sock"]

volumes:
  huskycat-ipc:
```

---

## Part 4: Darwin Packaging (macOS Code Signing)

### 4.1 Requirements

| Requirement | Status | Notes |
|-------------|--------|-------|
| Apple Developer Account | ❌ Needed | $99/year |
| Developer ID Certificate | ❌ Needed | From Apple |
| Notarization credentials | ❌ Needed | App-specific password |
| Hardened Runtime | ❌ Needed | Enabled in entitlements |

### 4.2 Code Signing Process

```
┌──────────────────────────────────────────────────────────────┐
│                    DARWIN CODE SIGNING                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. BUILD                                                    │
│     pyinstaller huskycat.spec --target-arch universal2       │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │ dist/huskycat   │  Unsigned binary                       │
│  └────────┬────────┘                                        │
│           │                                                  │
│  2. SIGN                                                     │
│     codesign --sign "Developer ID Application: ..."          │
│              --options runtime                               │
│              --entitlements entitlements.plist               │
│              dist/huskycat                                   │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │ dist/huskycat   │  Signed binary                         │
│  └────────┬────────┘                                        │
│           │                                                  │
│  3. NOTARIZE                                                 │
│     xcrun notarytool submit dist/huskycat.zip                │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │ Apple servers   │  Malware scan                          │
│  │ (~5 min)        │                                        │
│  └────────┬────────┘                                        │
│           │                                                  │
│  4. STAPLE                                                   │
│     xcrun stapler staple dist/huskycat                       │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │ dist/huskycat   │  Notarized + stapled                   │
│  └─────────────────┘  (No Gatekeeper warnings)              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 4.3 Entitlements File

```xml
<!-- entitlements.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-jit</key>
    <false/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <false/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.cs.allow-dyld-environment-variables</key>
    <false/>
</dict>
</plist>
```

### 4.4 CI/CD Integration

```yaml
# .gitlab-ci.yml additions
darwin-sign:
  stage: sign
  tags:
    - macos
    - apple-silicon
  variables:
    APPLE_ID: $APPLE_ID
    APPLE_TEAM_ID: $APPLE_TEAM_ID
    APPLE_PASSWORD: $APPLE_APP_SPECIFIC_PASSWORD
  script:
    # Import certificate from base64-encoded variable
    - echo "$APPLE_CERTIFICATE_BASE64" | base64 -d > cert.p12
    - security create-keychain -p "" build.keychain
    - security import cert.p12 -k build.keychain -P "$APPLE_CERT_PASSWORD"
    - security set-key-partition-list -S apple-tool:,apple: -s -k "" build.keychain

    # Sign the binary
    - codesign --sign "Developer ID Application: Tinyland ($APPLE_TEAM_ID)"
              --options runtime
              --entitlements entitlements.plist
              --force
              dist/huskycat-darwin-arm64

    # Create ZIP for notarization
    - ditto -c -k --keepParent dist/huskycat-darwin-arm64 huskycat.zip

    # Submit for notarization
    - xcrun notarytool submit huskycat.zip
              --apple-id "$APPLE_ID"
              --team-id "$APPLE_TEAM_ID"
              --password "$APPLE_PASSWORD"
              --wait

    # Staple the notarization ticket
    - xcrun stapler staple dist/huskycat-darwin-arm64
```

### 4.5 Universal Binary (Optional)

```bash
# Build fat binary for both Intel and Apple Silicon
pyinstaller huskycat.spec --target-arch x86_64
mv dist/huskycat dist/huskycat-x86_64

pyinstaller huskycat.spec --target-arch arm64
mv dist/huskycat dist/huskycat-arm64

# Combine into universal binary
lipo -create -output dist/huskycat-darwin-universal \
     dist/huskycat-x86_64 dist/huskycat-arm64

# Sign the universal binary
codesign --sign "Developer ID Application: ..." \
         --options runtime \
         dist/huskycat-darwin-universal
```

---

## Part 5: Implementation Priority

### Phase 1: Beta Launch (Week 1)
- [ ] Finalize `BETA_TESTING.md` with installation verification steps
- [ ] Test installer script on all platforms
- [ ] Set up issue templates for bug reports
- [ ] Announce to closed beta group

### Phase 2: GPL Integration (Week 2-3)
- [ ] Integrate `gpl_client` into `unified_validation.py`
- [ ] Add sidecar startup documentation
- [ ] Create `podman-compose.yml` with both containers
- [ ] Test comprehensive mode with sidecar

### Phase 3: Darwin Signing (Week 3-4)
- [ ] Obtain Apple Developer Account
- [ ] Generate Developer ID certificate
- [ ] Create CI job for signing/notarization
- [ ] Test signed binary on fresh macOS

### Phase 4: Open Beta (Week 5+)
- [ ] Public announcement
- [ ] Monitor metrics
- [ ] Iterate based on feedback

---

## Appendix: File References

| Topic | Authoritative Source | Lines |
|-------|---------------------|-------|
| Beta testing | `docs/BETA_TESTING.md` | 1-396 |
| Installation | `docs/installation.md` | 1-436 |
| Binary build | `huskycat.spec` | All |
| Container build | `ContainerFile.wrapper` | 1-153 |
| GPL client | `src/huskycat/core/gpl_client.py` | 1-342 |
| GPL server | `gpl-sidecar/server.py` | 1-313 |
| Tool selection | `src/huskycat/core/tool_selector.py` | 1-498 |
| Mode detection | `src/huskycat/core/mode_detector.py` | 1-82 |
