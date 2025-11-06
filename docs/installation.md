# Installation Guide

> ⚠️ **Prerequisite**: You need either ROS installed locally on your machine OR access over the network to a robot/computer with ROS installed. This MCP server connects to ROS systems on a robot, so a running ROS environment is required.

Installation includes the following steps:
- On the Host Machine (Where the LLM will run)
  - Install the ROS-MCP server
  - Install any language model client (We demonstrate with Claude Desktop)
  - Configure the client to run the MCP server automatically on launch.
- On the Robot (Where ROS will be running)
  - Install and launch rosbridge


Below are detailed instructions for each of these steps. 

---

# On The Host Machine (Where Your LLM Will Run)

The ROS MCP server is capable of connecting any LLM client that supports the MCP protocol, and can also do so via multiple transport protocols (stdio, streamable http, etc.)

For the primary installation guide, we demonstrate using **Claude Desktop** and the default stdio transport layer. We use uvx for installation and management of dependencies.

We also have examples for different LLM clients (Cursor, Gemini, and ChatGPT) and other transport protocols (streamable http)


For alternate clients, transport protocols, and installation methods, see [Alternate Installation and Configuration Options](installation-alternatives.md#alternative-installation-options).

---
Expand the OS below for installation instructions

<details>
<summary><strong>Linux (Ubuntu)</strong></summary>

## 1. Install the MCP server

### 1.1 Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Look up [documentation from uv](https://docs.astral.sh/uv/getting-started/installation/) for more information or in the case of any errors.

### 1.2 Test run ROS-MCP using uvx

```bash
# Test that the ROS-MCP server can be accessed in the venv
uvx ros-mcp --help
```

## 2. Install and configure a Language Model Client

### 2.1 Download
- Follow the installation instructions from the community-supported [claude-desktop-debian](https://github.com/aaddrick/claude-desktop-debian)

### 2.2 Configure
- Locate and edit the `claude_desktop_config.json` file:
- (If the file does not exist, create it)
```bash
~/.config/Claude/claude_desktop_config.json
```

- Add the following to the `"mcpServers"` section of the JSON file:

```json
{
  "mcpServers": {
    "ros-mcp-server": {
      "command": "bash",
      "args": [
        "-lc", 
        "uvx ros-mcp --transport=stdio"
      ]
    }
  }
}
```

### 2.3 Test the connection
- Launch Claude Desktop and check connection status. 
- The ros-mcp-server should be visible in your list of tools.

<p align="center">
  <img src="https://github.com/robotmcp/ros-mcp-server/blob/main/docs/images/connected_mcp.png" width="500"/>
</p>

<details>
<summary><strong> Troubleshooting </strong></summary>

- If the `ros-mcp-server` doesn't appear even after correctly configuring `claude_desktop_config.json`, try completely shutting down Claude Desktop using the commands below and then restarting it. This could be a Claude Desktop caching issue.
```bash
# Completely terminate Claude Desktop processes
pkill -f claude-desktop
# Or alternatively
killall claude-desktop

# Restart Claude Desktop
claude-desktop
```

</details>

</details>

<details>
<summary><strong>MacOS</strong></summary>

## 1. Install the MCP server

### 1.1 Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Look up [documentation from uv](https://docs.astral.sh/uv/getting-started/installation/) for more information or in the case of any errors.

### 1.2 Test run ROS-MCP using uvx

```bash
# Test that the ROS-MCP server can be accessed in the venv
uvx ros-mcp --help
```

## 2. Install and configure a Language Model Client

### 2.1 Download
- Download from [claude.ai](https://claude.ai/download)

### 2.2 Configure
- Locate and edit the `claude_desktop_config.json` file:
- (If the file does not exist, create it)
```bash
~/Library/Application\ Support/Claude/claude_desktop_config.json
```

- Add the following to the `"mcpServers"` section of the JSON file:

```json
{
  "mcpServers":{
    "ros-mcp-server": {
      "command": "zsh",
      "args": [
        "-lc", 
        "uvx ros-mcp --transport=stdio"
      ]
    }
  }
}
```

### 2.3 Test the connection
- Launch Claude Desktop and check connection status. 
- The ros-mcp-server should be visible in your list of tools.

<p align="center">
  <img src="https://github.com/robotmcp/ros-mcp-server/blob/main/docs/images/connected_mcp.png" width="500"/>
</p>

<details>
<summary><strong> Troubleshooting </strong></summary>

- If the `ros-mcp-server` doesn't appear even after correctly configuring `claude_desktop_config.json`, try completely shutting down Claude Desktop using the commands below and then restarting it. This could be a Claude Desktop caching issue.
```bash
# Completely terminate Claude Desktop processes
pkill -f claude-desktop
# Or alternatively
killall claude-desktop

# Restart Claude Desktop
claude-desktop
```

</details>

</details>

<details>
<summary><strong>Windows (Using WSL)</strong></summary>

## 1. Install the MCP server

### 1.1 Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Look up [documentation from uv](https://docs.astral.sh/uv/getting-started/installation/) for more information or in the case of any errors.

### 1.2 Test run ROS-MCP using uvx

```bash
# Test that the ROS-MCP server can be accessed in the venv
uvx ros-mcp --help
```

## 2. Install and configure a Language Model Client

### 2.1 Download
- Download from [claude.ai](https://claude.ai/download)

This will have Claude running on Windows and the MCP server running on WSL. We assume that you have installed uv on your [WSL](https://apps.microsoft.com/detail/9pn20msr04dw?hl=en-US&gl=US)

### 2.2 Configure
- Locate and edit the `claude_desktop_config.json` file:
- (If the file does not exist, create it)
```bash
~/.config/Claude/claude_desktop_config.json
```

- Add the following to the `"mcpServers"` section of the JSON file:
- Use the correct **WSL distribution name** (e.g., `"Ubuntu-22.04"`)

```json
{
  "mcpServers":{
    "ros-mcp-server": {
      "command": "wsl",
        "args": [
          "-d", 
          "Ubuntu-22.04", 
          "bash", 
          "-lc", 
          "uvx ros-mcp --transport=stdio"
        ]
    }
  }
}
```


### 2.3 Test the connection
- Launch Claude Desktop and check connection status. 
- The ros-mcp-server should be visible in your list of tools.

<p align="center">
  <img src="https://github.com/robotmcp/ros-mcp-server/blob/main/docs/images/connected_mcp.png" width="500"/>
</p>

<details>
<summary><strong> Troubleshooting </strong></summary>

- If the `ros-mcp-server` doesn't appear even after correctly configuring `claude_desktop_config.json`, try completely shutting down Claude Desktop using the commands below and then restarting it. This could be a Claude Desktop caching issue.
```bash
# Completely terminate Claude Desktop processes
pkill -f claude-desktop
# Or alternatively
killall claude-desktop

# Restart Claude Desktop
claude-desktop
```

</details>

</details>

<details>
<summary><strong>Windows (Using PowerShell)</strong></summary>

## 1. Install the MCP server

### 1.1 Install uv

```powershell
# Use the following command in windows powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install ps1 | iex"
```

Look up [documentation from uv](https://docs.astral.sh/uv/getting-started/installation/) for more information or in the case of any errors.

### 1.2 Test run ROS-MCP using uvx

```powershell
# Test that the ROS-MCP server can be accessed in the venv
uvx ros-mcp --help
```

## 2. Install and configure a Language Model Client

### 2.1 Download
- Download from [claude.ai](https://claude.ai/download)

This will have Claude and the MCP server running within Windows.

### 2.2 Configure
- Locate and edit the `claude_desktop_config.json` file:
- (If the file does not exist, create it)
```bash
~/.config/Claude/claude_desktop_config.json
```

- Add the following to the `"mcpServers"` section of the JSON file:

```json
{
  "mcpServers": {
    "ros-mcp-server": {
      "command": "uvx",
      "args": ["ros-mcp", "--transport=stdio"]
    }
  }
}
```

### 2.3 Test the connection
- Launch Claude Desktop and check connection status. 
- The ros-mcp-server should be visible in your list of tools.

<p align="center">
  <img src="https://github.com/robotmcp/ros-mcp-server/blob/main/docs/images/connected_mcp.png" width="500"/>
</p>

<details>
<summary><strong> Troubleshooting </strong></summary>

- If the `ros-mcp-server` doesn't appear even after correctly configuring `claude_desktop_config.json`, try completely shutting down Claude Desktop using the commands below and then restarting it. This could be a Claude Desktop caching issue.
```bash
# Completely terminate Claude Desktop processes
pkill -f claude-desktop
# Or alternatively
killall claude-desktop

# Restart Claude Desktop
claude-desktop
```

</details>

</details>

---

# On The Target Robot (Where ROS Will Be Running)
<details>
<summary><strong>ROS 1</strong></summary>

## 3. Install and run rosbridge
### 3.1. Install `rosbridge_server`

This package is required for MCP to interface with ROS or ROS 2 via WebSocket. It needs to be installed on the same machine that is running ROS.


For ROS Noetic
```bash
sudo apt install ros-noetic-rosbridge-server
```
<details>
<summary>For other ROS Distros</summary>

```bash
sudo apt install ros-${ROS_DISTRO}-rosbridge-server
```
</details>

### 3.2. Launch rosbridge in your ROS environment:


```bash
roslaunch rosbridge_server rosbridge_websocket.launch
```
> ⚠️ Don’t forget to `source` your ROS workspace before launching, especially if you're using custom messages or services.

</details>

<details>
<summary><strong>ROS 2</strong></summary>

## 3. Install and run rosbridge
### 3.1. Install `rosbridge_server`

This package is required for MCP to interface with ROS or ROS 2 via WebSocket. It needs to be installed on the same machine that is running ROS.


For ROS 2 Humble
```bash
sudo apt install ros-humble-rosbridge-server
```
<details>
<summary>For other ROS Distros</summary>

```bash
sudo apt install ros-${ROS_DISTRO}-rosbridge-server
```
</details>

### 3.2. Launch rosbridge in your ROS environment:


```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```
> ⚠️ Don’t forget to `source` your ROS workspace before launching, especially if you're using custom messages or services.

</details>


---


# You're ready to go!

You can test out your server with any robot that you have running. Just tell your AI to connect to the robot using its target IP address. (Default is localhost, so you don't need to tell it to connect if the MCP server is installed on the same machine as your ROS.)

✅ **Tip:** If you don't currently have any robots running, turtlesim is considered the 'hello world' robot for ROS to experiment with. It does not have any simulation dependencies such as Gazebo or IsaacSim.

<details>
<summary><strong>Testing with turtlesim</strong></summary>

For a complete step-by-step tutorial on using turtlesim with the MCP server and for more information on ROS and turtlesim, see our [Turtlesim Tutorial](../examples/1_turtlesim/README.md).

If you have ROS already installed, you can launch turtlesim with the below command:
**ROS1:**
```
rosrun turtlesim turtlesim_node
```

**ROS2:**
```
ros2 run turtlesim turtlesim_node
```

</details>

<details>
<summary><strong>Example Commands</strong></summary>

### Natural language commands

Example:
```plaintext
Make the robot move forward.
```

<p align="center">
  <img src="https://github.com/robotmcp/ros-mcp-server/blob/main/docs/images/how_to_use_1.png" width="500"/>
</p>

### Query your ROS system
Example:  
```plaintext
What topics and services do you see on the robot?
```
<p align="center">
  <img src="https://github.com/robotmcp/ros-mcp-server/blob/main/docs/images/how_to_use_3.png" />
</p>

</details>



## Troubleshooting

<details>
<summary><strong>Common Issues</strong></summary>

Here are some frequently encountered issues and their solutions:

<details>
<summary><strong>MCP Server Not Appearing in Client</strong></summary>

**Symptoms**: The ros-mcp-server doesn't appear in your LLM client's tool list.

**Solutions**:
1. **Restart client**: Completely shut down and restart your LLM client
2. **Check logs**: Look for error messages in your LLM client's logs
3. **Test manually**: Try running the MCP server manually to check for errors:

```bash
uvx ros-mcp
```

</details>

<details>
<summary><strong>Connection Refused Errors</strong></summary>

**Symptoms**: "Connection refused" or "No valid session ID provided" errors.

**Solutions**:
1. **Check ROS is running**: Ensure ROS and rosbridge are running
2. **Verify rosbridge port**: Default is 9090, check if it's different
3. **Test connectivity**: Use the ping tool to test connection:

```bash
# Test if rosbridge is accessible
curl -I http://localhost:9090
```

4. **Check firewall**: Ensure firewall allows the rosbridge port

</details>

<details>
<summary><strong>WSL-Specific Issues</strong></summary>

**Symptoms**: Issues when running on Windows with WSL.

**Solutions**:
1. **Check WSL distribution**: Ensure you're using the correct WSL distribution name
2. **Test manually**: Try running the MCP server manually in WSL:

```bash
uvx ros-mcp
```

</details>

<details>
<summary><strong>HTTP Transport Issues</strong></summary>

**Symptoms**: HTTP transport not working or connection timeouts.

**Solutions**:
1. **Check command line arguments**: Ensure the correct transport, host, and port are specified:
   ```bash
   # Check available options
   uvx ros-mcp --help
   
   # Example with custom settings
   uvx ros-mcp --transport http --host 0.0.0.0 --port 8080
   ```

2. **Check environment variables** (legacy): Ensure MCP_TRANSPORT, MCP_HOST, and MCP_PORT are set correctly

3. **Verify port availability**: Check if the port is already in use:

```bash
# Check if port is in use
netstat -tulpn | grep :9000
```

4. **Test HTTP endpoint**: Try accessing the HTTP endpoint directly:

```bash
curl http://localhost:9000
```

5. **Check firewall**: Ensure firewall allows the configured port

</details>

<details>
<summary><strong>If you're still having issues:</strong></summary>

1. **Check the logs**: Look for error messages in your LLM client and MCP server logs. Running the logs through an LLM (ChatGPT or Claude) can greatly help debugging!
2. **Test with turtlesim**: Try the [turtlesim tutorial](../examples/1_turtlesim/README.md) to verify basic functionality
3. **Open an issue**: Create an issue on the [GitHub repository](https://github.com/robotmcp/ros-mcp-server/issues) with:
   - Your operating system
   - ROS version
   - LLM client being used
   - Error messages
   - Steps to reproduce

</details>

---

</details>

<details>
<summary><strong>Debug Commands</strong></summary>

Test ROS connectivity
```bash
ros2 topic list  # For ROS 2
rostopic list   # For ROS 1
```

Test rosbridge
```bash
curl -I http://localhost:9090
```

Test MCP server manually
```bash
uvx ros-mcp --transport=stdio
```

Check running processes
```bash
ps aux | grep rosbridge
ps aux | grep ros-mcp
```

</details>


---