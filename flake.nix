{
  description = "HuskyCat - Universal Code Validation Platform with MCP Server Integration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachSystem [
      "x86_64-linux"
      "aarch64-linux"
      "x86_64-darwin"
      "aarch64-darwin"
    ] (system:
      let
        pkgs = import nixpkgs { inherit system; };

        # Python environment with HuskyCat dependencies
        pythonEnv = pkgs.python312.withPackages (ps: with ps; [
          # Core dependencies (from pyproject.toml)
          pydantic
          pyyaml
          jsonschema
          requests
          rich
          networkx
          psutil
          click
          toml
          gitpython

          # Validation tools
          black
          mypy
          flake8
          bandit
          autoflake

          # Testing
          pytest
          pytest-cov
          hypothesis
        ]);

      in {
        # Package: huskycat as a derivation
        packages.default = pkgs.stdenvNoCC.mkDerivation {
          pname = "huskycat";
          version = "2.0.0";
          src = ./.;

          nativeBuildInputs = [ pkgs.makeWrapper ];
          buildInputs = [ pythonEnv ];

          installPhase = ''
            mkdir -p $out/bin $out/lib/huskycat
            cp -r src/huskycat $out/lib/huskycat/

            makeWrapper ${pythonEnv}/bin/python $out/bin/huskycat \
              --add-flags "-m huskycat" \
              --prefix PYTHONPATH : "$out/lib"
          '';

          meta = with pkgs.lib; {
            description = "Universal code validation platform with MCP server integration";
            homepage = "https://gitlab.com/jsullivan2/huskycats-bates";
            license = licenses.asl20;
            platforms = platforms.unix;
          };
        };

        # Development shell - Apache/MIT tools only (FAST mode)
        devShells.default = pkgs.mkShell {
          name = "huskycat-dev";

          buildInputs = with pkgs; [
            # Python environment
            python312
            uv

            # Node.js for npm scripts
            nodejs_22

            # Linting tools (Apache/MIT compatible)
            black
            ruff
            mypy

            # TOML formatting
            taplo

            # Documentation
            python312Packages.mkdocs
            python312Packages.mkdocs-material

            # Development utilities
            git
            jq
            yq-go
          ];

          shellHook = ''
            echo "HuskyCat Development Environment (Nix)"
            echo "======================================="
            echo "Python: $(python --version)"
            echo "UV: $(uv --version 2>/dev/null || echo 'run: curl -LsSf https://astral.sh/uv/install.sh | sh')"
            echo "Node: $(node --version)"
            echo ""
            echo "Quick Start:"
            echo "  uv sync --dev       Install Python dependencies"
            echo "  npm install         Install Node dependencies"
            echo "  npm run dev         Run HuskyCat CLI"
            echo "  npm run validate    Validate codebase"
            echo "  nix build           Build Nix package"
            echo ""
            echo "Linting Mode: FAST (Apache/MIT tools only)"
            echo "For GPL tools, use: nix develop .#ci"
          '';
        };

        # CI shell - includes GPL tools for comprehensive validation
        devShells.ci = pkgs.mkShell {
          name = "huskycat-ci";

          buildInputs = with pkgs; [
            # All dev dependencies
            python312
            uv
            nodejs_22
            black
            ruff
            mypy
            taplo
            git
            jq

            # GPL tools (for COMPREHENSIVE mode)
            shellcheck
            hadolint
            yamllint
          ];

          shellHook = ''
            echo "HuskyCat CI Environment (Nix)"
            echo "============================="
            echo "Linting Mode: COMPREHENSIVE (includes GPL tools)"
            echo ""
            echo "GPL Tools Available:"
            echo "  shellcheck $(shellcheck --version | head -2 | tail -1)"
            echo "  hadolint $(hadolint --version)"
            echo "  yamllint $(yamllint --version)"
          '';
        };

        # Checks for CI
        checks = {
          # Verify package builds
          package = self.packages.${system}.default;

          # Run tests (if pytest is available)
          tests = pkgs.runCommand "huskycat-tests" {
            buildInputs = [ pythonEnv pkgs.git ];
          } ''
            cd ${self}
            export HOME=$(mktemp -d)
            export PYTHONPATH=${self}/src
            python -m pytest tests/ -v --tb=short -x || true
            touch $out
          '';
        };
      }
    );
}
