#!/bin/bash
# Run cross-tests: verify each distro is detected as the correct ROS version.
# Usage: ./tests/integration/scripts/run-all-cross-tests.sh

set -e
cd "$(git rev-parse --show-toplevel)"

PASSED=()
FAILED=()

run_check() {
    local distro="$1"
    local expected="$2"
    echo ""
    echo "========================================"
    echo "  $distro → expecting $expected"
    echo "========================================"
    if ./tests/integration/scripts/run-cross-test.sh "$distro" "$expected"; then
        PASSED+=("$distro=$expected")
    else
        FAILED+=("$distro=$expected")
    fi
}

# Correct expectations — all should PASS
run_check melodic ROS1
run_check noetic  ROS1
run_check humble  ROS2
run_check jazzy   ROS2

echo ""
echo "========================================"
echo "  RESULTS"
echo "========================================"
echo "Passed: ${PASSED[*]:-none}"
echo "Failed: ${FAILED[*]:-none}"

if [ ${#FAILED[@]} -gt 0 ]; then
    exit 1
fi
