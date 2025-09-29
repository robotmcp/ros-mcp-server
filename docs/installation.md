# Installation Guide

> ⚠️ **Prerequisite**: You need either ROS installed locally on your machine OR access over the network to a robot/computer with ROS installed. This MCP server connects to ROS systems on a robot, so a running ROS environment is required.

Installation includes the following steps:
- Install the MCP server
  - Clone this repository
  - Install uv (Python virtual environment manager)
- Install and configure the Language Model Client
  - Install any language model client (We demonstrate with Claude Desktop)
  - Configure the client to run the MCP server and connect automatically on launch.
- Install and launch Rosbridge


Below are detailed instructions for each of these steps. 

---
# 1. Install the MCP server (On the host machine where the LLM will be running)

## 1.1. Clone the Repository

```bash
git clone https://github.com/robotmcp/ros-mcp-server.git
```

Note the **absolute path** to the cloned directory — you’ll need this later when configuring your language model client.

---

## 1.2. Install UV (Python Virtual Environment Manager)

You can install [`uv`](https://github.com/astral-sh/uv) using one of the following methods:

<details>
<summary><strong>Option A: Shell installer</strong></summary>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

</details>

<details>
<summary><strong>Option B: Using pip</strong></summary>

```bash
pip install uv
```

</details>

---

# 2. Install and configure a Language Model Client 

Any LLM client that supports MCP can be used. We use **Claude Desktop** for testing and development.



## 2.1. Download Claude Desktop 
<details>
<summary><strong>Linux (Ubuntu)</strong></summary>

- Follow the installation instructions from the community-supported [claude-desktop-debian](https://github.com/aaddrick/claude-desktop-debian)

</details>

<details>
<summary><strong>MacOS</strong></summary>

- Download from [claude.ai](https://claude.ai/download)

</details>

<details>
<summary><strong>Windows (Using WSL)</strong></summary>

This will have Claude running on Windows and the MCP server running on WSL. We assume that you have cloned the repository and installed UV on your [WSL](https://apps.microsoft.com/detail/9pn20msr04dw?hl=en-US&gl=US) 

- Download from [claude.ai](https://claude.ai/download)

</details>


## 2.2. Configure Claude Desktop to launch the MCP server
<details>
<summary><strong>Linux (Ubuntu)</strong></summary>

- Locate and edit the `claude_desktop_config.json` file:
- (If the file does not exist, create it)
```bash
~/.config/Claude/claude_desktop_config.json
```

- Add the following to the `"mcpServers"` section of the JSON file
- Make sure to replace `<ABSOLUTE_PATH>` with the **full absolute path** to your `ros-mcp-server` folder (note: `~` for home directory may not work in JSON files):

```json
{
  "mcpServers": {
    "ros-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/<ABSOLUTE_PATH>/ros-mcp-server",
        "run",
        "server.py"
      ]
    }
  }
}
```

</details>


<details>
<summary><strong>MacOS</strong></summary>

- Locate and edit the `claude_desktop_config.json` file:
- (If the file does not exist, create it)
```bash
~/Library/Application\ Support/Claude/claude_desktop_config.json
```

- Add the following to the `"mcpServers"` section of the JSON file
- Make sure to replace `<ABSOLUTE_PATH>` with the **full absolute path** to your `ros-mcp-server` folder (note: `~` for home directory may not work in JSON files):

```json
{
  "mcpServers": {
    "ros-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/<ABSOLUTE_PATH>/ros-mcp-server",
        "run",
        "server.py"
      ]
    }
  }
}
```

</details>


<details>
<summary><strong>Windows (Using WSL)</strong></summary>

- Locate and edit the `claude_desktop_config.json` file:
- (If the file does not exist, create it)
```bash
~/.config/Claude/claude_desktop_config.json
```

- Add the following to the `"mcpServers"` section of the JSON file
- Make sure to replace `<ABSOLUTE_PATH>` with the **full absolute path** to your `ros-mcp-server` folder (note: `~` for home directory may not work in JSON files):
- Set the **full WSL path** to your `uv` installation (e.g., `/home/youruser/.local/bin/uv`)
- Use the correct **WSL distribution name** (e.g., `"Ubuntu-22.04"`)

```json
{
  "mcpServers": {
    "ros-mcp-server": {
      "command": "wsl",
      "args": [
        "-d", "Ubuntu-22.04",
        "/home/<YOUR_USER>/.local/bin/uv",
        "--directory",
        "/<ABSOLUTE_PATH>/ros-mcp-server",
        "run",
        "server.py"
      ]
    }
  }
}
```

</details>

---

<details>
<summary><strong> Alternate Configuration - HTTP Transport</strong></summary>

The above configurations sets up the MCP server using the default STDIO transport layer, which launches the server as a plugin automatically on launching Claude. 

It is also possible to configure the MCP server using the http transport layer, which configures Claude to connect to the MCP server when it is launched as a standalone application. 

For HTTP transport, the configuration is the same across all platforms. First start the MCP server manually:

**Linux/macOS/Windows(WSL):**
```bash
cd /<ABSOLUTE_PATH>/ros-mcp-server
export MCP_TRANSPORT=streamable-http
export MCP_HOST=127.0.0.1
export MCP_PORT=9000
uv run server.py
```

Then configure Claude Desktop to connect to the HTTP server (same for all platforms):

```json
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

</details>

<details>
<summary> Comparison between default (STDIO) and HTTP Transport</summary>

#### STDIO Transport (Default)
- **Best for**: Local development, single-user setups
- **Pros**: Simple setup, no network configuration needed
- **Cons**: MCP server and LLM/MCP client need to be running on the local machine.
- **Use case**: Running MCP server directly with your LLM client

#### HTTP/Streamable-HTTP Transport
- **Best for**: Remote access, multiple clients, production deployments
- **Pros**: Network accessible, multiple clients can connect
- **Cons**: Requires network configuration, MCP server needs to be run independently.
- **Use case**: Remote robots, team environments, web-based clients

</details>


## 2.3. Test the connection
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
<summary><strong> Examples and setup instructions for other LLMs</strong></summary>

#### 3.2.1. Cursor IDE
For detailed Cursor setup instructions, see our [Cursor Tutorial](../examples/7_cursor/README.md).

#### 3.2.2. ChatGPT
For detailed ChatGPT setup instructions, see our [ChatGPT Tutorial](../examples/6_chatgpt/README.md).

#### 3.2.3. Google Gemini
For detailed Gemini setup instructions, see our [Gemini Tutorial](../examples/2_gemini/README.md).

<details>
<summary><strong>Custom MCP Client</strong></summary>

#### 3.2.1. Using the MCP Server Programmatically
You can also use the MCP server directly in your Python code:

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

## 6.1. Common Issues

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
1. **Check environment variables**: Ensure MCP_TRANSPORT, MCP_HOST, and MCP_PORT are set correctly
2. **Verify port availability**: Check if the port is already in use:

```bash
# Check if port is in use
netstat -tulpn | grep :9000
```

3. **Test HTTP endpoint**: Try accessing the HTTP endpoint directly:

```bash
curl http://localhost:9000
```

4. **Check firewall**: Ensure firewall allows the configured port

</details>

## 6.2. Debug Commands

```bash
# Test ROS connectivity
ros2 topic list  # For ROS 2
rostopic list   # For ROS 1

# Test rosbridge
curl -I http://localhost:9090

# Test MCP server manually
cd /<ABSOLUTE_PATH>/ros-mcp-server
uv run server.py

# Check processes
ps aux | grep rosbridge
ps aux | grep ros-mcp
```

## 6.3. Getting Help

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