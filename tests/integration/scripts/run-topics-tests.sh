#!/bin/bash
# Run topics integration tests against a specific ROS distro.
# Usage: ./tests/integration/scripts/run-topics-tests.sh <distro>
exec "$(dirname "$0")/run-tests.sh" "${1:?Usage: $0 <melodic|noetic|humble|jazzy>}" topics
