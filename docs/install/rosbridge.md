# Step 2: Setting Up Rosbridge

Rosbridge runs on the **robot's machine** (wherever ROS is running). It provides a WebSocket interface that the MCP server on your machine connects to over the network.

> **Prerequisite:** ROS must already be installed on the robot's machine. If you don't have ROS installed and want to try things out quickly, see the [Turtlesim Docker example](../../examples/5_docker_turtlesim/README.md) which runs ROS and rosbridge in a container.

> **Important — rosbridge *and* rosapi are both required.** ros-mcp-server needs `rosbridge_server` (the WebSocket interface) **and** `rosapi` (the introspection services behind `get_nodes`, `get_topics`, `get_services`, `detect_ros_version`, parameter tools, etc.). The **launch file** used below starts both automatically. Do **not** start rosbridge with `ros2 run rosbridge_server ...` / `rosrun rosbridge_server ...` — those bring up the WebSocket *without* `rosapi`, and every introspection tool will fail with "Service does not exist". The `ros-<distro>-rosbridge-server` package pulls `rosapi` in as a dependency; if in doubt, install the full `ros-<distro>-rosbridge-suite` metapackage.

## Install rosbridge_server

For ROS 2 Jazzy:
```bash
# Update package list
sudo apt update
# Install rosbridge for ROS2 Jazzy
sudo apt install ros-jazzy-rosbridge-server
```

For other ROS 2 distros:
```bash
# Install rosbridge for ROS2 Humble
sudo apt install ros-humble-rosbridge-server
```
```bash
# Install for other ROS distros
sudo apt install ros-<your-distro>-rosbridge-server
```

> Using ROS 1? See [ROS 1 instructions](#ros-1-end-of-life) at the bottom of this page.

## Launch rosbridge
`source` your ROS workspace first to ensure that the rosbridge has access to your ROS system.

```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

> Don't forget to `source` your ROS workspace before launching, especially if you're using custom messages or services.

## Verify rosbridge is running

From the robot's machine:
```bash
curl -I http://localhost:9090
```

A successful response confirms rosbridge is listening on its default port (9090).

Also confirm `rosapi` is running — its services must be present for the MCP tools to work:
```bash
# ROS 2
ros2 service list | grep rosapi

# ROS 1
rosservice list | grep rosapi
```
If this prints nothing, you launched rosbridge without `rosapi` — use the `ros2 launch` / `roslaunch` command above rather than `ros2 run` / `rosrun`.

## Next Step

Connect to your robot and test it out: [Step 3: Connect](connect.md)

---

### Advanced

<details>
<summary><strong>ROS 1 (End of Life)</strong></summary>

#### Install rosbridge_server

For ROS Noetic:
```bash
sudo apt install ros-noetic-rosbridge-server
```

For other ROS 1 distros:
```bash
sudo apt install ros-<your-distro>-rosbridge-server
```

#### Launch rosbridge

```bash
roslaunch rosbridge_server rosbridge_websocket.launch
```

> Don't forget to `source` your ROS workspace before launching, especially if you're using custom messages or services.

</details>

---

[Back to Installation Guide](installation.md) | [Troubleshooting](troubleshooting.md)
