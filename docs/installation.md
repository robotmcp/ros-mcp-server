# Installation Guide

> ⚠️ **Prerequisite**: You need either ROS installed locally on your machine OR access over the network to a robot/computer with ROS installed. This MCP server connects to ROS systems on a robot, so a running ROS environment is required.

Installation includes the following steps:
- Install the MCP server using uvx
- Install and configure the Language Model Client
  - Install any language model client (We demonstrate with Claude Desktop)
  - Configure the client to run the MCP server and connect automatically on launch.
- Install and launch Rosbridge


Below are detailed instructions for each of these steps. 

---
# 1. Install the MCP server (On the host machine where the LLM will be running)

## Install using uvx (recommended for isolated installation):

### 1.1 Install uv 
<details>
<summary><strong>Linux, Mac, or WSL</strong></summary>

```bash
# Use the following command in windows powershell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

</details>

<details>
<summary><strong>Windows</strong></summary>

```powershell
# Use the following command in windows powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install ps1 | iex"
```

</details>

Look up [documentation from uv](https://docs.astral.sh/uv/getting-started/installation/) for more information or in the case of any errors

### 1.2 Test run ROS-MCP using uvx

```bash
# Test that the ROS-MCP server can be accessed in the venv
uvx ros-mcp --help
```
<details>
<summary><strong>Why use uvx?</strong></summary>

**Benefits of uvx:**
- Isolated installation in its own virtual environment
- Automatically downloads and installs all dependencies

</details>

For alternative installation methods (pip, source installation), see [Alternate Installation and Configuration Options](installation-alternatives.md#alternative-installation-options).

---

# 2. Install and configure a Language Model Client 

Any LLM client that supports MCP can be used. We use **Claude Desktop** for testing and development.


<details>
<summary><strong>Linux (Ubuntu)</strong></summary>

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

For alternative configuration options (HTTP transport), see [Alternate Installation and Configuration Options](installation-alternatives.md#alternate-configuration---http-transport).

</details>

<details>
<summary><strong>MacOS</strong></summary>

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

For alternative configuration options (HTTP transport), see [Alternate Installation and Configuration Options](installation-alternatives.md#alternate-configuration---http-transport).

</details>

<details>
<summary><strong>Windows (Using WSL)</strong></summary>

### 2.1 Download
- Download from [claude.ai](https://claude.ai/download)

This will have Claude running on Windows and the MCP server running on WSL. We assume that you have installed UV on your [WSL](https://apps.microsoft.com/detail/9pn20msr04dw?hl=en-US&gl=US)

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

For alternative configuration options (HTTP transport), see [Alternate Installation and Configuration Options](installation-alternatives.md#alternate-configuration---http-transport).

</details>

<details>
<summary><strong>Windows (Using PowerShell)</strong></summary>

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

For alternative configuration options (HTTP transport), see [Alternate Installation and Configuration Options](installation-alternatives.md#alternate-configuration---http-transport).

</details>

## 2.2. Test the connection
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


---

# 3. Install and run rosbridge (On the target robot where ROS will be running)
<details>
<summary><strong>ROS 1</strong></summary>

## 3.1. Install `rosbridge_server`

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

## 3.2. Launch rosbridge in your ROS environment:


```bash
roslaunch rosbridge_server rosbridge_websocket.launch
```
> ⚠️ Don’t forget to `source` your ROS workspace before launching, especially if you're using custom messages or services.

</details>

<details>
<summary><strong>ROS 2</strong></summary>


## 3.1. Install `rosbridge_server`

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


## 3.2. Launch rosbridge in your ROS environment:


```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```
> ⚠️ Don’t forget to `source` your ROS workspace before launching, especially if you're using custom messages or services.

</details>


---


# 4. You're ready to go!
You can test out your server with any robot that you have running. Just tell your AI to connect to the robot using its target IP address. (Default is localhost, so you don't need to tell it to connect if the MCP server is installed on the same machine as your ROS)

✅ **Tip:** If you don't currently have any robots running, turtlesim is considered the 'hello world' robot for ROS to experiment with. It does not have any simulation dependencies such as Gazebo or IsaacSim. 

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

---

# 5. Alternate Clients (ChatGPT, Gemini, Cursor)
<details>
<summary><strong>Examples and setup instructions for other LLM Hosts and Clients</strong></summary>

## 5.1. Cursor IDE
For detailed Cursor setup instructions, see our [Cursor Tutorial](../examples/7_cursor/README.md).

## 5.2. ChatGPT
For detailed ChatGPT setup instructions, see our [ChatGPT Tutorial](../examples/6_chatgpt/README.md).

## 5.3. Google Gemini
For detailed Gemini setup instructions, see our [Gemini Tutorial](../examples/2_gemini/README.md).

## 5.4. Custom MCP Client
You can also use the MCP server directly in your Python code. 
<details>
<summary>Here is a python example of how to integrate it programmatically</summary>

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="uv",
        args=["--directory", "/path/to/ros-mcp-server", "run", "server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Use the MCP server
            result = await session.call_tool("get_topics", {})
            print(result)
```

</details>

</details>


---

# 6. Troubleshooting

<details>
<summary><strong>6.1. Common Issues</strong></summary>

Here are some frequently encountered issues and their solutions:

<details>
<summary><strong>MCP Server Not Appearing in Client</strong></summary>

**Symptoms**: The ros-mcp-server doesn't appear in your LLM client's tool list.

**Solutions**:
1. **Check file paths**: Ensure all paths in your configuration are absolute and correct
2. **Restart client**: Completely shut down and restart your LLM client
3. **Check logs**: Look for error messages in your LLM client's logs
4. **Test manually**: Try running the MCP server manually to check for errors:

```bash
cd /<ABSOLUTE_PATH>/ros-mcp-server
uv run server.py
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
2. **Verify uv path**: Check that the uv path in WSL is correct:

```bash
# In WSL
which uv
```

3. **Test WSL connectivity**: Ensure Windows can reach WSL services
4. **Check WSL networking**: For HTTP transport, use `0.0.0.0` instead of `127.0.0.1`

</details>

<details>
<summary><strong>HTTP Transport Issues</strong></summary>

**Symptoms**: HTTP transport not working or connection timeouts.

**Solutions**:
1. **Check command line arguments**: Ensure the correct transport, host, and port are specified:
   ```bash
   # Check available options
   python server.py --help
   
   # Example with custom settings
   python server.py --transport http --host 0.0.0.0 --port 8080
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

1. **Check the logs**: Look for error messages in your LLM client and MCP server logs
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
<summary><strong>6.2. Debug Commands</strong></summary>

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
ros-mcp --transport=stdio
```

Check running processes
```bash
ps aux | grep rosbridge
ps aux | grep ros-mcp
```

</details>


---