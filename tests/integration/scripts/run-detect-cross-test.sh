#!/bin/bash
# Cross-test: start one distro's container, tell pytest it's a DIFFERENT distro.
# The test should FAIL because the detector sees the real distro.
#
# Usage: ./tests/integration/scripts/run-detect-cross-test.sh <real_distro> <fake_distro>
# Example: ./tests/integration/scripts/run-detect-cross-test.sh noetic humble
#   → Starts Noetic, runs pytest with --ros-distro humble → should FAIL

set -e
cd "$(git rev-parse --show-toplevel)"

REAL_DISTRO="${1:?Usage: $0 <real_distro> <fake_distro>}"
FAKE_DISTRO="${2:?Usage: $0 <real_distro> <fake_distro>}"
COMPOSE="tests/integration/docker-compose.yml"

if [ "$REAL_DISTRO" = "$FAKE_DISTRO" ]; then
    EXPECT_PASS=true
else
    EXPECT_PASS=false
fi

declare -A DOCKERFILES=(
    [melodic]="Dockerfile.ros1-melodic"
    [noetic]="Dockerfile.ros1-noetic"
    [humble]="Dockerfile.ros2-humble"
    [jazzy]="Dockerfile.ros2-jazzy"
)

declare -A CONTAINERS=(
    [melodic]="integration-ros-melodic"
    [noetic]="integration-ros-noetic"
    [humble]="integration-ros2-humble"
    [jazzy]="integration-ros2-jazzy"
)

DOCKERFILE="${DOCKERFILES[$REAL_DISTRO]}"
CONTAINER="${CONTAINERS[$REAL_DISTRO]}"

if [ -z "$DOCKERFILE" ]; then
    echo "Unknown distro: $REAL_DISTRO (valid: melodic, noetic, humble, jazzy)"
    exit 1
fi

echo "=== Cross-test: running $REAL_DISTRO, claiming $FAKE_DISTRO ==="
if $EXPECT_PASS; then
    echo "Expected: pytest PASSES (same distro)"
else
    echo "Expected: pytest FAILS on distro/version mismatch"
fi
echo ""

# Start the REAL container
ROS_DOCKERFILE="$DOCKERFILE" ROS_CONTAINER_NAME="$CONTAINER" \
    docker compose -f "$COMPOSE" down --volumes 2>/dev/null || true
ROS_DOCKERFILE="$DOCKERFILE" ROS_CONTAINER_NAME="$CONTAINER" \
    docker compose -f "$COMPOSE" up --build -d --wait

echo ""
echo "--- Running pytest --ros-distro $FAKE_DISTRO --skip-compose ---"
echo ""

# Run pytest with the FAKE distro but skip compose (use the already-running REAL container)
if uv run pytest tests/integration/test_detect_version.py -v \
    --ros-distro "$FAKE_DISTRO" --skip-compose; then
    PYTEST_PASSED=true
else
    PYTEST_PASSED=false
fi

echo ""
if $EXPECT_PASS && $PYTEST_PASSED; then
    echo "PASS — pytest passed as expected (same distro)"
    EXIT=0
elif $EXPECT_PASS && ! $PYTEST_PASSED; then
    echo "!!! UNEXPECTED FAIL — pytest should have passed for matching distro !!!"
    EXIT=1
elif ! $EXPECT_PASS && ! $PYTEST_PASSED; then
    echo "PASS — pytest failed as expected (detector saw $REAL_DISTRO, not $FAKE_DISTRO)"
    EXIT=0
else
    echo "!!! UNEXPECTED PASS — detector did not catch the mismatch !!!"
    EXIT=1
fi

# Tear down
ROS_DOCKERFILE="$DOCKERFILE" ROS_CONTAINER_NAME="$CONTAINER" \
    docker compose -f "$COMPOSE" down --volumes 2>/dev/null || true

exit $EXIT
