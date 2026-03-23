#!/bin/bash
# Run detect_version integration tests against a specific ROS distro.
# Usage: ./tests/integration/scripts/run-detect_version-tests.sh <distro>
exec "$(dirname "$0")/run-tests.sh" "${1:?Usage: $0 <melodic|noetic|humble|jazzy>}" detect_version
