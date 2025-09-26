#!/usr/bin/env bash
set -eo pipefail

# Colors
BLUE='\033[1;34m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}Starting ROS 2 environment...${NC}"

# 0. Source ROS 2 environment
echo -e "${GREEN}[ros${ROS_DISTRO}]${NC} Source ROS 2 ${ROS_DISTRO} ..."
source /opt/ros/${ROS_DISTRO}/setup.bash

# 1. Check if rosbridge is already running
if pgrep -f rosbridge_websocket > /dev/null; then
  echo -e "${YELLOW}[rosbridge]${NC} is already running. Killing old instance..."
  ROSBRIDGE_PIDS=($(pgrep -f "rosbridge_websocket"))
  ROSBRIDGE_PID1=${ROSBRIDGE_PIDS[0]:-}
  ROSBRIDGE_PID2=${ROSBRIDGE_PIDS[1]:-}
  [ -n "$ROSBRIDGE_PID1" ] && kill -9 "$ROSBRIDGE_PID1"
  [ -n "$ROSBRIDGE_PID2" ] && kill -9 "$ROSBRIDGE_PID2"
fi

# 3a. Start rosbridge
echo -e "${GREEN}[rosbridge]${NC} Launching rosbridge..."
ros2 launch rosbridge_server rosbridge_websocket_launch.xml port:=9090 &
ROSBRIDGE_PIDS=($(pgrep -f "rosbridge_websocket" | head -n2))

# 3b. Start turtlesim
echo -e "${GREEN}[rosturtle]${NC} Launching turtlesim..."
ros2 run turtlesim turtlesim_node &

sleep 1

# 3c. Store PIDs
echo -e "${GREEN}[rosjazzy]${NC} All services launched.${NC}"

ROSBRIDGE_PIDS=($(pgrep -f "rosbridge_websocket" | head -n2))
ROSBRIDGE_PID1=${ROSBRIDGE_PIDS[0]}
ROSBRIDGE_PID2=${ROSBRIDGE_PIDS[1]}
TURTLESIM_PID=$(pgrep -f turtlesim_node | head -n1)
echo "  • rosbridge PID:   $ROSBRIDGE_PID1"
echo "  • rosbridge PID:   $ROSBRIDGE_PID2"
echo "  • turtlesim PID:   $TURTLESIM_PID"

# 3. Trap to clean up processes on exit
trap "echo -e '${GREEN}[rosjazzy] ${NC}Stopping ROS processes...'; kill -9 $TURTLESIM_PID $ROSBRIDGE_PID1 $ROSBRIDGE_PID2" SIGINT SIGTERM

# 4. Keep script running, showing logs
wait

