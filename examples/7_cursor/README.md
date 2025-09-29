# Cursor Desktop with ROS-MCP-Server

## Prerequisites

### Prepare host machine (MCP Server)

* Installation of Cursor Desktop. Download [here](https://cursor.com/downloads).
* Installation of WSL on Windows

### Prepare target robot (ROS)

* Installation of Ubuntu or WSL (Windows Subsystem for Linux) on Windows.
* Installation of ROS or ROS2. Test if ROS is installed by running Turtlesim. If you are not sure, follow, this tutorial. See [here](https://wiki.ros.org/ROS/Tutorials).

# Tutorial

## Quick Start (For Experienced Users)

1. **Install dependencies**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. **Clone repository**: `cd ~ && git clone https://github.com/robotmcp/ros-mcp-server.git && cd ros-mcp-server`
3. **Configure Cursor**: Add stdio transport to `mcp.json` (see Option 2 below)
4. **Start ROS**: `ros2 launch rosbridge_server rosbridge_websocket_launch.xml & ros2 run turtlesim turtlesim_node`
5. **Test**: Ask Cursor to "List ROS topics"

## 1.1 Installation on Host Machine

### Install dependencies

* Install [`uv`](https://github.com/astral-sh/uv) using one of the following methods:

    <details>
	<summary><strong>Option A: PowerShell (Windows)</strong></summary>

	```bash
	winget install --id=astral-sh.uv -e
	```
	or
	```bash
	pip install uv
	```
	
	</details>

 	<details>
	<summary><strong>Option B: WSL (Linux) </strong></summary>

	```bash
	curl -LsSf https://astral.sh/uv/install.sh | sh
	```
	or (not recommended)
	```bash
	pip install uv
	```
	or (not recommended)
	```bash
	sudo snap install --classic astral-uv
	```
	</details>



### Install ROS-MCP Server

*  On your Host Machine, clone the repository and navigate to the ROS-MCP Server folder.

```bash
cd ~
git clone https://github.com/robotmcp/ros-mcp-server.git
cd ros-mcp-server
```

## 1.4 Connect ROS-MCP to Cursor

* Open Cursor Desktop
* Navigate to Settings (gear icon top right)
* Open MCP > New MCP Server 
* Modify the `mcp.json` as follows:

### Option 1: HTTP Transport (Network-based)

**Note**: For HTTP transport, you need to manually start the MCP server first.

* Start the MCP server in WSL:
```bash
wsl
cd ros-mcp-server
uv run server.py --transport http
```

* Configure Cursor with the following:
```
{
  "mcpServers": {
    "ros-mcp-server-http": {
      "name": "ROS-MCP Server (http)",
      "transport": "http",
      "url": "http://127.0.0.1:9000/mcp"
    }
  }
}
```

### Option 2: Stdio Transport (Direct WSL execution) - **Recommended**

**Benefits of stdio transport:**
- No need to manually start the server
- Direct communication with WSL
- More reliable and faster
- Automatic server management

**Important Configuration Notes:**
- Make sure to move ros-mcp-server folder to your `/home/<YOUR_USER>` (note: ~ for home directory may not work in JSON files)
```
"/home/<YOUR_USER>/ros-mcp-server" # Linux home directory
"/mnt/c/Users/<YOUR_USER>/ros-mcp-server" # WSL home directory
```
- Use the correct WSL distribution name (e.g., "Ubuntu" or "Ubuntu-22.04")
- Make sure to replace `<YOUR_USER>` with your actual WSL username

- Ensure uv is installed at `/home/<YOUR_USER>/.local/bin/uv`, if not modify the installation directory (`which uv` can help locate.)

```
{
  "mcpServers": {
    "ros-mcp-server": {
      "name": "ROS-MCP Server (stdio)",
      "transport": "stdio",
      "command": "wsl",
      "args": [
        "-d", "Ubuntu",
        "/home/<YOUR_USER>/.local/bin/uv",
        "--directory",
        "/home/<YOUR_USER>/ros-mcp-server",
        "run",
        "server.py"
      ]
  }
}
```

### Option 3: Both HTTP and Stdio (Complete Configuration)

You can copy-paste the mcp.json in this folder and modify <YOUR_USER> accordingly:

```
{
  "mcpServers": {
    "ros-mcp-server-http": {
      "name": "ROS-MCP Server (http)",
      "transport": "http",
      "url": "http://127.0.0.1:9000/mcp"
    },
    "ros-mcp-server-stdio": {
      "name": "ROS-MCP Server (stdio)",
      "transport": "stdio",
      "command": "wsl",
      "args": [
        "-d", "Ubuntu",
        "/home/<YOUR_USER>/.local/bin/uv",
        "--directory",
        "/home/<YOUR_USER>/ros-mcp-server",
        "run",
        "server.py"
      ]
    }
  }
}
```

## 1.5 Run ROS on Target Machine

In WSL, launch `rosbridge` and `turtlesim`

```bash
source /opt/ros/jazzy/setup.bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml & ros2 run turtlesim turtlesim_node
```

or

```bash
launch_ros.sh
```

## 1.6 Test Your Setup

Once everything is configured, test your connection:

1. **Start a new chat in Cursor**
2. **Try a simple ROS command** like:
   - "List all available ROS topics"
   - "Show me the current ROS node information"
   - "What robots are available in the specifications?"

3. **Verify the connection** - you should see ROS-related responses from the MCP server

## 2. Troubleshooting

### Common Issues

**MCP Server not connecting:**
- Verify WSL is running: `wsl --list --verbose`
- Check if uv is installed: `wsl -- which uv`
- Ensure the ros-mcp-server directory exists in WSL

**ROS Bridge connection failed:**
- Make sure ROS is running: `ros2 node list`
- Verify rosbridge is active: `ros2 launch rosbridge_server rosbridge_websocket_launch.xml`
- Check if port 9090 is available

**Stdio transport not working:**
- Verify the WSL distribution name is correct
- Check if the uv path is accurate: `/home/<YOUR_USER>/.local/bin/uv`
- Ensure the ros-mcp-server directory is in the correct location `/home/<YOUR_USER>/ros-mcp-server`

### Debug Commands

```bash
# Test WSL connection
wsl --list --verbose

# Test uv installation
wsl -- which uv

# Test ROS installation
wsl -- ros2 node list

# Test rosbridge
wsl -- ros2 topic list
```

## 3. Usage Examples

Once connected, you can use natural language to interact with your ROS system:

- **"Move the turtle forward"** - Controls turtlesim
- **"What topics are currently publishing?"** - Lists active topics
- **"Show me the robot specifications"** - Displays available robot configs
- **"Connect to robot at IP 192.168.1.100"** - Connects to remote robot
- **"Take a picture with the camera"** - Captures camera data

## 4. Advanced Configuration

### Environment Variables

You can customize the MCP server behavior with these environment variables:

```bash
# ROS Bridge settings
export ROSBRIDGE_IP="127.0.0.1"  # Default: localhost
export ROSBRIDGE_PORT="9090"     # Default: 9090

# MCP Transport settings
export MCP_TRANSPORT="streamable-http"  # For ChatGPT: streamable-http
export MCP_TRANSPORT="stdio"            # For Cursor: stdio (recommended)
export MCP_HOST="127.0.0.1"             # For HTTP transport
export MCP_PORT="9000"                  # For HTTP transport
```

### Custom Robot Specifications

Add your own robot configurations in `utils/robot_specifications/`:

```yaml
# utils/robot_specifications/my_robot.yaml
name: "My Custom Robot"
ip: "192.168.1.100"
port: 9090
description: "My custom robot configuration"
```

### Multiple Robot Support

You can connect to multiple robots by switching configurations:

```bash
# Connect to different robots
export ROSBRIDGE_IP="192.168.1.100"  # Robot 1
export ROSBRIDGE_IP="192.168.1.101"  # Robot 2
```

## 5. FAQ

**Q: Can I run multiple MCP servers?**
A: Yes, you can configure multiple servers in your mcp.json file.

**Q: Is stdio transport faster than HTTP?**
A: Yes, stdio transport is generally faster and more reliable as it eliminates network overhead.

**Q: Can I use this without WSL?**
A: The current setup requires WSL for ROS compatibility on Windows. Linux and macOS users can run directly.

## 6. Tested Configurations

### Host Machine
* Windows 11
* WSL with Ubuntu 22.04
* Cursor Desktop

### Target Machine
* WSL with Ubuntu 22.04
* ROS 2 Jazzy

## 7. Support and Contributing

### Getting Help
- **Issues**: Report bugs and request features on [GitHub Issues](https://github.com/robotmcp/ros-mcp-server/issues)
- **Documentation**: Check the main [README.md](../../README.md) for additional information
- **Community**: Join discussions in the project's GitHub Discussions

### Contributing
We welcome contributions! Please see our [Contributing Guide](../../docs/contributing.md) for details on:
- Setting up a development environment
- Code style guidelines
- Submitting pull requests
- Testing procedures