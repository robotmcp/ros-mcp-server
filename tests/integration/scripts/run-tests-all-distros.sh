#!/bin/bash
# Run integration tests against ALL supported distros.
# Usage: ./tests/integration/scripts/run-tests-all-distros.sh

set -e
cd "$(git rev-parse --show-toplevel)"

DISTROS=(melodic noetic humble jazzy)
PASSED=()
FAILED=()

for distro in "${DISTROS[@]}"; do
    echo ""
    echo "========================================"
    echo "  Testing: $distro"
    echo "========================================"
    echo ""
    if ./tests/integration/scripts/run-tests.sh "$distro"; then
        PASSED+=("$distro")
    else
        FAILED+=("$distro")
    fi
done

echo ""
echo "========================================"
echo "  RESULTS"
echo "========================================"
echo "Passed: ${PASSED[*]:-none}"
echo "Failed: ${FAILED[*]:-none}"
echo ""

if [ ${#FAILED[@]} -gt 0 ]; then
    exit 1
fi
