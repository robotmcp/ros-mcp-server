#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_TAG="ros-mcp-noetic-debug:local"

cd "$REPO_ROOT"

echo "[1/3] Building Docker image: $IMAGE_TAG"
sudo docker build -f docker/Dockerfile.noetic-debug -t "$IMAGE_TAG" .

echo "[2/3] Running practical ROS1 debug test in container"
sudo docker run --rm \
  --cap-add=SYS_PTRACE \
  --security-opt seccomp=unconfined \
  -v "$REPO_ROOT":/work \
  -w /work \
  "$IMAGE_TAG" \
  bash -lc "python3 scripts/practical_noetic_debug.py"

echo "[3/3] Done. Results: $REPO_ROOT/practical_noetic_results.json"
