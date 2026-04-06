#!/bin/bash
# Run connection integration tests against a specific ROS distro.
# Usage: ./tests/integration/scripts/run-connection-tests.sh <distro>
exec "$(dirname "$0")/run-tests.sh" "${1:?Usage: $0 <melodic|noetic|humble|jazzy>}" connection
