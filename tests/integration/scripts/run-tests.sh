#!/bin/bash
# Run integration tests against a specific ROS distro.
# Usage: ./tests/integration/scripts/run-tests.sh <distro>
# Example: ./tests/integration/scripts/run-tests.sh noetic

set -e
cd "$(git rev-parse --show-toplevel)"

DISTRO="${1:?Usage: $0 <melodic|noetic|humble|jazzy>}"
COMPOSE="tests/integration/docker-compose.yml"

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

DOCKERFILE="${DOCKERFILES[$DISTRO]}"
CONTAINER="${CONTAINERS[$DISTRO]}"

if [ -z "$DOCKERFILE" ]; then
    echo "Unknown distro: $DISTRO"
    echo "Valid options: melodic, noetic, humble, jazzy"
    exit 1
fi

echo "=== Testing $DISTRO ==="
echo "Dockerfile: $DOCKERFILE"
echo "Container:  $CONTAINER"
echo ""

# Tear down any previous container
ROS_DOCKERFILE="$DOCKERFILE" ROS_CONTAINER_NAME="$CONTAINER" \
    docker compose -f "$COMPOSE" down --volumes 2>/dev/null || true

# Build and start
echo "--- Starting container ---"
ROS_DOCKERFILE="$DOCKERFILE" ROS_CONTAINER_NAME="$CONTAINER" \
    docker compose -f "$COMPOSE" up --build -d --wait

# Run quick detect
echo ""
echo "--- Quick detect ---"
uv run python tests/integration/test_quick_detect.py

# Run pytest
echo ""
echo "--- Pytest ---"
uv run pytest tests/integration/ -v --ros-distro "$DISTRO" --skip-compose

# Tear down
echo ""
echo "--- Tearing down ---"
ROS_DOCKERFILE="$DOCKERFILE" ROS_CONTAINER_NAME="$CONTAINER" \
    docker compose -f "$COMPOSE" down --volumes
