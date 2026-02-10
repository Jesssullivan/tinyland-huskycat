# Nix Installation

HuskyCat provides a Nix flake with packages, development shells, a home-manager module, and a nixpkgs overlay.

## Quick Start

### Try Without Installing

```bash
nix run gitlab:tinyland/ai/huskycat -- validate .
```

### Install Imperatively

```bash
nix profile install gitlab:tinyland/ai/huskycat
```

### Run in Development Shell

```bash
# FAST mode (Apache/MIT tools only)
nix develop gitlab:tinyland/ai/huskycat

# COMPREHENSIVE mode (includes GPL tools: shellcheck, hadolint, yamllint)
nix develop gitlab:tinyland/ai/huskycat#ci
```

## Flake Reference

Add to your `flake.nix` inputs:

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    huskycat.url = "gitlab:tinyland/ai/huskycat";
  };
}
```

### Available Outputs

| Output | Description |
|--------|-------------|
| `packages.<system>.default` | HuskyCat package |
| `packages.<system>.container` | nix2container image (Linux only) |
| `apps.<system>.default` | `nix run` entry point |
| `devShells.<system>.default` | FAST mode dev shell |
| `devShells.<system>.ci` | COMPREHENSIVE mode dev shell |
| `homeManagerModules.default` | Home-manager integration |
| `overlays.default` | Nixpkgs overlay |
| `checks.<system>.package` | Build verification |
| `checks.<system>.tests` | Test suite |

### Supported Systems

- `x86_64-linux` (primary)
- `aarch64-linux`
- `x86_64-darwin`
- `aarch64-darwin` (Apple Silicon)

## Overlay Usage

Add HuskyCat to your nixpkgs:

```nix
# In flake.nix
{
  nixpkgs.overlays = [ huskycat.overlays.default ];
}

# Then use it anywhere nixpkgs is available
{ pkgs, ... }: {
  environment.systemPackages = [ pkgs.huskycat ];
}
```

## Home-Manager Module

For declarative configuration with home-manager, see the options below.

### Basic Setup

```nix
# In your home-manager configuration
{ inputs, ... }: {
  imports = [ inputs.huskycat.homeManagerModules.default ];

  tinyland.huskycat = {
    enable = true;
    package = inputs.huskycat.packages.${pkgs.system}.default;
  };
}
```

### Full Configuration

```nix
tinyland.huskycat = {
  enable = true;
  package = inputs.huskycat.packages.${pkgs.system}.default;

  # Linting mode: "fast" (Apache/MIT) or "comprehensive" (includes GPL)
  lintingMode = "fast";

  # Git hooks integration
  hooks = {
    preCommit.validation = true;     # Pre-commit validation
    postCommit.triage = false;       # Post-commit auto-triage
    prepareCommitMsg.branchPrefix = false;  # Branch prefix injection
  };

  # Triage engine
  triage = {
    enable = false;
    platforms = [ "gitlab" "github" "codeberg" ];
    autoIteration = true;
    autoLabel = true;
  };

  # MCP server registration for Claude Code
  mcp = {
    enable = true;
    scope = "user";  # "user" (global) or "project" (per-repo)
  };
};
```

### What the Module Configures

When enabled, the home-manager module:

1. **Installs HuskyCat** to your profile
2. **Registers git hooks** via the `tinyland.globalGitHooks` dispatcher
3. **Registers MCP server** with Claude Code (`~/.claude.json`)
4. **Sets environment variables** (`HUSKYCAT_LINTING_MODE`, etc.)
5. **Creates hook scripts** for post-commit triage and branch prefix injection

## Binary Cache

HuskyCat uses an Attic cache for faster builds:

```
https://nix-cache.fuzzy-dev.tinyland.dev/main
```

This is already configured in the flake's `nixConfig`. If your Nix installation trusts flake configs, builds will automatically use the cache.

### Manual Cache Configuration

If you need to configure the cache manually:

```bash
# Add to /etc/nix/nix.conf or ~/.config/nix/nix.conf
extra-substituters = https://nix-cache.fuzzy-dev.tinyland.dev/main
extra-trusted-public-keys = main:PBDvqG8OP3W2XF4QzuqWwZD/RhLRsE7ONxwM09kqTtw=
```

## Development

### Enter Dev Shell

```bash
cd /path/to/huskycat
nix develop        # FAST mode
nix develop .#ci   # COMPREHENSIVE mode (includes GPL tools)
```

### Build Locally

```bash
nix build
./result/bin/huskycat --version
```

### Verify Flake

```bash
nix flake check
nix flake show
```
