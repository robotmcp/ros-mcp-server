# Example - TurtleSim in Docker
For users who want to test the MCP server without needing to install ROS, this is an example that provides a dockerized ROS2  container preinstalled with the simplest possible 'robot' in the ROS ecosystem - TurtleSim. 

Turtlesim is a lightweight simulator for learning ROS / ROS 2. It illustrates what ROS does at the most basic level to give you an idea of what you will do with a real robot or a robot simulation later on.

## Prerequisites

✅ **Note:** This tutorial is designed to be run on linux and has been tested with Ubuntu as well as [Ubuntu running on WSL](https://apps.microsoft.com/detail/9pn20msr04dw?hl=en-US&gl=US). Being a dockerized container, it is likely to work on other OS versions as well with the correct X11 forwarding settings. 

Before starting this tutorial, make sure you have the following installed:

- **Docker**: [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose**: Usually comes with Docker Desktop, or install separately
- **X Server** (for Windows): Install [X410](https://x410.dev/) or another X Server from Microsoft Store
- **X11 forwarding** (for Linux): `sudo apt-get install x11-apps`
- **XQuartz** (for macOS): Install from [XQuartz website](https://www.xquartz.org/)

**Note:** If your OS is Windows, take a look at the following:
<details>
<summary><strong>PowerShell and WSL (Windows)</strong></summary>

- Install Docker from [installer](https://docs.docker.com/desktop/setup/install/windows-install) or Microsoft Store
- Open Docker Desktop > Settings > Resources > WSL Integration
- Enable your distro (e.g., Ubuntu 22.04)
- Verify installation: in PowerShell `docker --version` and in WSL `docker --version`
</details>

## Quick Start

### 1. Build the Container

Navigate to the turtlesim example directory and build the Docker container:

```bash
cd examples/5_docker_turtlesim
docker compose build --no-cache turtlesim
```

### 2. Start the Container

Launch the turtlesim container

```bash
docker compose up
```

If your OS is Windows and you want to launch docker in PowerShell, you first need to set the DISPLAY:
```bash
$env:DISPLAY="host.docker.internal:0.0"
```

If your OS is Ubuntu/WSL and the docker doesn't run successfully, consider:

```bash
dos2unix docker/scripts/launch_turtlesim.sh
```

The container will automatically start both turtlesim and rosbridge websocket server. You should see:

- A turtlesim window appear with a turtle
- ROS Bridge WebSocket server running on `ws://localhost:9090`
- Turtle teleop ready for keyboard input

### 3. Access the Container (Optional)

If you need to access the container for debugging or additional commands:

Launch the container in the background:
```bash
docker compose up -d
```
And attach to the container

```bash
docker exec -it ros2-turtlesim bash
```

Once inside the container, you can manually launch turtle teleop to control the turtle:

```bash
source /opt/ros/humble/setup.bash
ros2 run turtlesim turtle_teleop_key
```

This will allow you to use arrow keys or WASD to manually move the turtle around the turtlesim window.

## Integration with MCP Server

Once turtlesim and rosbridge are running, you can connect the MCP server to control the turtle programmatically.
Follow the [installation guide](../../docs/installation.md) for full setup instructions if you haven't already set up the MCP server. 

Since it is running on the same machine, you can tell the LLM to connect to the robot on localhost. 


## Troubleshooting

### Display Issues (Linux)

If you encounter display issues on Linux, run:

```bash
xhost +local:docker
```

### Display Issues (macOS)

For macOS users, make sure XQuartz is running and configured:

```bash
# Start XQuartz
open -a XQuartz

# Allow connections from localhost
xhost +localhost
```

### Display Issues (Windows/PowerShell)
For Windows users, make sure you install an X Server (X410) and set the DISPLAY:

```bash
$env:DISPLAY="host.docker.internal:0.0"
```

### Container Networking

If you need to access the container from outside, the container uses host networking mode, so ROS2 topics should be accessible on localhost.

### Manual Launch (Alternative)

If the automatic launch isn't working or you prefer to launch turtlesim manually, you can run these commands inside the container:

```bash
# Access the container
docker exec -it ros2-turtlesim bash

# Source ROS2 environment
source /opt/ros/humble/setup.bash

# Start turtlesim in one terminal
ros2 run turtlesim turtlesim_node

# In another terminal, start the teleop node
ros2 run turtlesim turtle_teleop_key
```

### Testing Turtlesim

If you need to verify that turtlesim is working correctly:

#### ROS2 Topic Inspection

In a separate terminal, you can inspect the ROS2 topics:

```bash
# Access the container
docker exec -it ros2-turtlesim bash

# Source ROS2 environment
source /opt/ros/humble/setup.bash

# List all topics
ros2 topic list

# Echo turtle position
ros2 topic echo /turtle1/pose

# Echo turtle velocity commands
ros2 topic echo /turtle1/cmd_vel
```

#### ROS Bridge WebSocket Server

The rosbridge websocket server is automatically started and available at `ws://localhost:9090`. You can test the connection using a WebSocket client or the MCP server.

To verify rosbridge is running, you can check the container logs:

```bash
docker logs ros2-turtlesim
```

## Cleanup

To stop and remove the container:

```bash
docker-compose down
```

To remove the built image:

```bash
docker rmi ros-mcp-server_turtlesim
```

## Next Steps

Now that you have turtlesim running, you can:


1. **Try more complex commands** like drawing shapes or following paths
2. **Install ROS Locally** to add more nodes and services
3. **Explore other examples in this repository**


This example provides a foundation for understanding how the MCP server can interact with ROS2 systems, from simple simulators like turtlesim to complex robotic platforms. 
