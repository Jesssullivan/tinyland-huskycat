#!/bin/bash
# Test script to verify fast mode implementation
set -e

echo "=== Testing HuskyCat Fast Mode Implementation ==="
echo ""

# Navigate to test repo
TEST_REPO="/tmp/test-gitops-repo"
if [[ ! -d "$TEST_REPO" ]]; then
    echo "ERROR: Test repo not found at $TEST_REPO"
    echo "Run the bootstrap test first to create it"
    exit 1
fi

cd "$TEST_REPO"
echo "Working directory: $(pwd)"
echo ""

# Setup: Add HuskyCat to PATH
export PYTHONPATH="/Users/jsullivan2/git/huskycats-bates/src:$PYTHONPATH"

# Test 1: Run auto-devops WITHOUT fast mode (verbose)
echo "=== Test 1: auto-devops (normal mode) ==="
echo "Should run helm template and kubectl --dry-run (if available)"
echo ""
uv run --directory /Users/jsullivan2/git/huskycats-bates python -m src.huskycat auto-devops . -vv

echo ""
echo "=== Test 2: auto-devops --fast ==="
echo "Should skip helm template and kubectl --dry-run"
echo ""
uv run --directory /Users/jsullivan2/git/huskycats-bates python -m src.huskycat auto-devops . --fast -vv

echo ""
echo "=== Test 3: Verify hook uses --fast ==="
cat .git/hooks/pre-push | grep -A 5 "auto-devops"

echo ""
echo "✅ Fast mode tests complete!"
