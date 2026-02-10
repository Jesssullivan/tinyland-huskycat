# Container Usage

HuskyCat provides container images for Docker, Podman, and Kubernetes environments.

## Container Variants

| Image | Base | Size | Use Case |
|-------|------|------|----------|
| `registry.gitlab.com/tinyland/ai/huskycat:latest` | Alpine + Python | ~200MB | Standard usage |
| `registry.gitlab.com/tinyland/ai/huskycat:latest-nix` | nix2container | ~150MB | Reproducible builds |

## Quick Start

### Docker

```bash
# Validate current directory
docker run --rm -v "$(pwd):/workspace" \
  registry.gitlab.com/tinyland/ai/huskycat:latest \
  validate /workspace

# Validate staged files
docker run --rm -v "$(pwd):/workspace" -w /workspace \
  registry.gitlab.com/tinyland/ai/huskycat:latest \
  validate --staged

# Run with custom config
docker run --rm \
  -v "$(pwd):/workspace" \
  -v "$HOME/.huskycat.yaml:/etc/huskycat/huskycat.yaml:ro" \
  registry.gitlab.com/tinyland/ai/huskycat:latest \
  validate /workspace
```

### Podman

```bash
# Same syntax as Docker
podman run --rm -v "$(pwd):/workspace:Z" \
  registry.gitlab.com/tinyland/ai/huskycat:latest \
  validate /workspace
```

## CI/CD Integration

### GitLab CI

```yaml
validate:
  image: registry.gitlab.com/tinyland/ai/huskycat:latest
  script:
    - huskycat validate . --all
```

### GitHub Actions

```yaml
jobs:
  validate:
    runs-on: ubuntu-latest
    container:
      image: registry.gitlab.com/tinyland/ai/huskycat:latest
    steps:
      - uses: actions/checkout@v4
      - run: huskycat validate . --all
```

## Docker Compose

For projects that want HuskyCat as a CI validation service:

```yaml
# docker-compose.yml
services:
  huskycat:
    image: registry.gitlab.com/tinyland/ai/huskycat:latest
    volumes:
      - .:/workspace:ro
    command: validate /workspace --all
    profiles:
      - validate
```

Run with:

```bash
docker compose run --rm huskycat
```

## Kubernetes

### Validation Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: huskycat-validate
spec:
  template:
    spec:
      containers:
        - name: huskycat
          image: registry.gitlab.com/tinyland/ai/huskycat:latest
          args: ["validate", "/workspace", "--all", "--json"]
          volumeMounts:
            - name: source
              mountPath: /workspace
              readOnly: true
      volumes:
        - name: source
          persistentVolumeClaim:
            claimName: source-code
      restartPolicy: Never
```

### CronJob for Scheduled Validation

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: huskycat-nightly
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: huskycat
              image: registry.gitlab.com/tinyland/ai/huskycat:latest
              args: ["validate", "/workspace", "--all", "--json"]
              volumeMounts:
                - name: source
                  mountPath: /workspace
          volumes:
            - name: source
              persistentVolumeClaim:
                claimName: source-code
          restartPolicy: Never
```

## Volume Mounts

| Host Path | Container Path | Purpose |
|-----------|---------------|---------|
| `$(pwd)` | `/workspace` | Source code to validate |
| `~/.huskycat.yaml` | `/etc/huskycat/huskycat.yaml` | Custom configuration |
| `~/.cache/huskycat` | `/root/.cache/huskycat` | Validation cache |

## Image Tags

| Tag Pattern | Example | Description |
|-------------|---------|-------------|
| `latest` | `huskycat:latest` | Latest main branch build |
| `<sha>` | `huskycat:abc1234` | Specific commit |
| `<version>` | `huskycat:2.0.0` | Tagged release |
| `latest-nix` | `huskycat:latest-nix` | nix2container variant |
| `<sha>-nix` | `huskycat:abc1234-nix` | nix2container at commit |

## Building the Container Locally

### Using Docker/Podman

```bash
docker build -f ContainerFile -t huskycat:local .
docker run --rm -v "$(pwd):/workspace" huskycat:local validate /workspace
```

### Using Nix

```bash
nix build .#packages.x86_64-linux.container
# Result is a container archive at ./result
docker load < ./result
```
