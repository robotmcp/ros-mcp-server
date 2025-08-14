[![MSeeP.ai Security Assessment Badge](https://mseep.net/pr/robotmcp-ros-mcp-server-badge.png)](https://mseep.ai/app/robotmcp-ros-mcp-server)

## Overview
![Static Badge](https://img.shields.io/badge/ROS-Available-green)
![Static Badge](https://img.shields.io/badge/ROS2-Available-green)
[![smithery badge](https://smithery.ai/badge/@lpigeon/ros-mcp-server)](https://smithery.ai/server/@lpigeon/ros-mcp-server)
![Static Badge](https://img.shields.io/badge/License-MIT-blue)

<center><img src="https://github.com/lpigeon/ros-mcp-server/blob/main/img/framework.png"/></center>

The ROS MCP Server is designed to support robots in performing complex tasks and adapting effectively to various environments by providing a set of functions that transform natural language commands, entered by a user through an LLM, into ROS commands for robot control. Furthermore, by utilizing ``rosbridge``, it is configured to operate with both ``ROS`` and ``ROS2`` systems, and its WebSocket-based communication enables broad applicability across diverse platforms.

Research based on this project can be found in the video linked below.  
- [An Efficient Robot Control Framework Using the Model Context Protocol](https://www.youtube.com/watch?v=7ut4eqTxwHA)

## Supported Types

- geometry_msgs/Twist
- sensor_msgs/Image

## Installation

### Installing via Smithery

To install ``ros-mcp-server`` for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@lpigeon/ros-mcp-server):

```bash
npx -y @smithery/cli install @lpigeon/ros-mcp-server --client claude
```

### Installing Locally

### `uv` Installation
- To install `uv`, you can use the following command:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
or
```bash
pip install uv
```

- Create virtual environment and activate it (Optional)
```bash
uv venv
source .venv/bin/activate
```

### MCP Server Configuration
Set MCP setting to mcp.json.

```bash
"ros-mcp-server": {
  "command": "uv",
  "args": [
    "--directory",
    "/ABSOLUTE/PATH/TO/PARENT/FOLDER/ros-mcp-server",,
    "run",
    "server.py"
  ]
}
```

If you use Claude Desktop, you can find mcp.json using the following command:

- MacOS/Linux
```bash
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

- Windows
```bash
code $env:AppData\Claude\claude_desktop_config.json
```

## MCP Functions

### get_topics
- **Purpose**: Retrieves the list of available topics from the robot's ROS system.
- **Returns**: List of topics (List[Any])

### pub_twist
- **Purpose**: Sends movement commands to the robot by setting linear and angular velocities.
- **Parameters**:
  - `linear`: Linear velocity (List[Any])
  - `angular`: Angular velocity (List[Any])

### pub_twist_seq
- **Purpose**: Sends a sequence of movement commands to the robot, allowing for multi-step motion control.
- **Parameters**:
  - `linear`: List of linear velocities (List[Any])
  - `angular`: List of angular velocities (List[Any])
  - `duration`: List of durations for each step (List[Any])
 
### sub_image
- **Purpose**: Receive images from the robot's point of view or of the surrounding environment.
- **Parameters**:
  - `save_path`: By default, the image is saved to the ``Downloads`` folder.

## How To Use
### 1. Set IP and Port to connect rosbridge.
- Open `server.py` and change your `LOCAL_IP`, `ROSBRIDGE_IP` and `ROSBRIDGE_PORT`. (`ROSBRIDGE_PORT`'s default value is `9090`)

### 2. Run rosbridge server.
ROS 1
```bash
roslaunch rosbridge_server rosbridge_websocket.launch
```
ROS 2
```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

### 3. Run any AI system that has imported ``ros-mcp-server``.

### 4. Type "Make the robot move forward.".
<center><img src="https://github.com/lpigeon/ros-mcp-server/blob/main/img/how_to_use_1.png" width="500"/></center>

### 5. Check `rosbridge_server` and `ros topic`.
- `rosbridge_server`
<center><img src="https://github.com/lpigeon/ros-mcp-server/blob/main/img/how_to_use_2.png" /></center>

- `ros topic`
<center><img src="https://github.com/lpigeon/ros-mcp-server/blob/main/img/how_to_use_3.png" /></center>

## Simulation Test
MCP-based control using the MOCA mobile manipulator within the NVIDIA Isaac Sim simulation environment. 

<center><img src="https://github.com/lpigeon/ros-mcp-server/blob/main/img/result.gif" /></center>
