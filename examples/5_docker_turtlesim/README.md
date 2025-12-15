# Example - TurtleSim in Docker

For users who want to test the MCP server without needing to install ROS, this is an example that provides a dockerized ROS2 container preinstalled with the simplest possible 'robot' in the ROS ecosystem - TurtleSim.

Turtlesim is a lightweight simulator for learning ROS / ROS 2. It illustrates what ROS does at the most basic level to give you an idea of what you will do with a real robot or a robot simulation later on.

## Prerequisites

✅ **Cross-Platform Support:** This tutorial works on Linux, macOS, and Windows with proper X11/display forwarding setup. Each platform has specific requirements detailed below.

Before starting this tutorial, make sure you have the following installed:

### All Platforms
- **Docker**: [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose**: Usually comes with Docker Desktop, or install separately

### Platform-Specific Requirements

#### macOS
- **XQuartz**: Install from [XQuartz website](https://www.xquartz.org/)
- **Important**: XQuartz setup can be complex - see [macOS Setup](#macos-setup) section below for detailed instructions

#### Linux
- **X11 forwarding**: `sudo apt-get install x11-apps`
- Usually works out of the box with minimal setup

#### Windows
- **X Server**: Install [X410](https://x410.dev/), [VcXsrv](https://sourceforge.net/projects/vcxsrv/), or another X Server from Microsoft Store
- **WSL recommended**: Works best with Windows Subsystem for Linux

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

### 2. Launch Turtlesim

#### Automatic Setup (Recommended)

The easiest way to launch turtlesim with proper X11 setup:

```bash
./scrips/launch.sh
```

This script automatically detects your OS and handles all platform-specific X11 configuration. It will:
- **macOS**: Start XQuartz, detect display, configure IP-based forwarding
- **Linux**: Set up X11 permissions with `xhost +local:docker`
- **Windows**: Configure X server connection via `host.docker.internal`

#### Manual Setup (Advanced)

If you prefer manual control or the automatic script doesn't work:

**macOS:**
```bash
./scripts/launch_macos.sh
```

**Linux (or Windows WSL):**
```bash
./scripts/launch_linux.sh
```

**Windows:**
```bash
./scripts/launch_windows.sh
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

And attach to the container:
```bash
docker exec -it ros2-turtlesim bash
```

Once inside the container, you can manually launch turtle teleop to control the turtle:

```bash
source /opt/ros/${ROS_DISTRO}$/setup.bash
ros2 run turtlesim turtle_teleop_key
```

This will allow you to use arrow keys or WASD to manually move the turtle around the turtlesim window.

## Integration with MCP Server

Once turtlesim and rosbridge are running, you can connect the MCP server to control the turtle programmatically.
Follow the [installation guide](../../docs/installation.md) for full setup instructions if you haven't already set up the MCP server.

Since it is running on the same machine, you can tell the LLM to connect to the robot on localhost.

## Platform-Specific Setup

<details>
<summary><strong>macOS Setup</strong></summary>

macOS requires special X11 forwarding setup. Follow these steps carefully:

### Step 1: Install XQuartz
Download and install from [XQuartz website](https://www.xquartz.org/)

### Step 2: Configure XQuartz
1. **Start XQuartz**: `open -a XQuartz`
2. **Wait for it to fully load** (you'll see an xterm window)

### Step 3: Detect Your Setup
```bash
# Check if XQuartz is running and which display it's using
ps aux | grep -i xquartz

# You should see something like:
# /opt/X11/bin/Xquartz :1 -listen tcp ...
# The `:1` or `:0` is your display number
```

### Step 4: Get Your Machine IP
```bash
# Get your machine's IP address
ifconfig en0 | grep inet | awk '$1=="inet" {print $2}'
# Example output: 10.1.56.72
```

### Step 5: Set Up Environment
```bash
# Set DISPLAY for your Mac (use the display number from Step 3)
export DISPLAY=:1  # or :0 depending on what you found

# Allow X11 connections
xhost +

# Set DISPLAY for Docker (use your IP from Step 4 + display number)
export DOCKER_DISPLAY=<YOUR_IP>  # Replace with your actual IP
```
</details>

## Troubleshooting

### macOS Display Issues

<details>
<summary><strong>Problem: <code>qt.qpa.xcb: could not connect to display</code></strong></summary>

**Solutions**:

1. **Check XQuartz is running**:
   ```bash
   ps aux | grep X11
   ```

2. **Verify display number**:
   ```bash
   # Look for :0 or :1 in the Xquartz process
   ps aux | grep Xquartz | grep -o ":[0-9]"
   ```

3. **Check your IP address**:
   ```bash
   ifconfig en0 | grep inet
   ```

4. **Set correct DOCKER_DISPLAY**:
   ```bash
   export DOCKER_DISPLAY="YOUR_IP:DISPLAY_NUMBER"
   # Example: export DOCKER_DISPLAY="10.1.56.72:1"
   ```

5. **Allow X11 connections**:
   ```bash
   export DISPLAY=:1  # Use your display number
   xhost +
   ```
</details>

<details>
<summary><strong>Problem: <code>xhost: unable to open display ":0"</code></strong></summary>

**Solution**: XQuartz might be using `:1` instead of `:0`:

```bash
export DISPLAY=:1
xhost +
```
</details>

### Linux Display Issues

<details>
<summary><strong>Display issues on Linux</strong></summary>

If you encounter display issues on Linux, run:

```bash
xhost +local:docker
```
</details>

### Windows Display Issues

<details>
<summary><strong>Display issues on Windows</strong></summary>

For Windows users, make sure you install an X Server (X410) and set the DISPLAY:

```bash
$env:DOCKER_DISPLAY="host.docker.internal:0.0"
```
</details>

### General Issues

<details>
<summary><strong>Problem: Container starts but no window appears</strong></summary>

**Solutions**:
1. Check if the window is hidden behind other windows
2. Look in Mission Control (macOS) or Alt+Tab (Windows/Linux)
3. Verify your DOCKER_DISPLAY is set correctly for your platform
</details>

<details>
<summary><strong>Problem: <code>libGL error: No matching fbConfigs or visuals found</code></strong></summary>

**Solution**: This is just a warning and doesn't prevent the GUI from working. The turtlesim window should still appear.
</details>

## Manual Launch (Alternative)

If the automatic launch isn't working or you prefer to launch turtlesim manually, you can run these commands inside the container:

```bash
# Access the container
docker exec -it ros2-turtlesim bash

# Source ROS2 environment
source /opt/ros/${ROS_DISTRO}$/setup.bash

# Start turtlesim in one terminal
ros2 run turtlesim turtlesim_node

# In another terminal, start the teleop node
ros2 run turtlesim turtle_teleop_key
```

## Testing Turtlesim

If you need to verify that turtlesim is working correctly:

### ROS2 Topic Inspection

In a separate terminal, you can inspect the ROS2 topics:

```bash
# Access the container
docker exec -it ros2-turtlesim bash

# Source ROS2 environment
source /opt/ros/${ROS_DISTRO}$/setup.bash

# List all topics
ros2 topic list

# Echo turtle position
ros2 topic echo /turtle1/pose

# Echo turtle velocity commands
ros2 topic echo /turtle1/cmd_vel
```

### ROS Bridge WebSocket Server

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