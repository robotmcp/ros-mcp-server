#!/usr/bin/env bash
set -eo pipefail

# Source ROS2 environment
source /opt/ros/humble/setup.bash

echo "Starting ROS Bridge WebSocket server..."
echo "WebSocket server will be available at: ws://localhost:9090"

# Launch rosbridge websocket server in the background
ros2 launch rosbridge_server rosbridge_websocket_launch.xml &

# Wait a moment for rosbridge to start
sleep 3

echo "Starting Turtlesim..."
echo "Turtlesim window should appear shortly"
echo "You can control the turtle using:"
echo "  - Arrow keys or WASD to move"
echo "  - Ctrl+C to stop"

# Launch turtlesim in the background
ros2 run turtlesim turtlesim_node &

# Trap signals to clean up processes
cleanup() {
    # Cleanup when teleop exits
    echo "Stopping turtlesim and rosbridge..."
    pkill -f turtlesim_node
    pkill -f rosbridge_server
    wait
}

trap cleanup SIGINT SIGTERM

wait