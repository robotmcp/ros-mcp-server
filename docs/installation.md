# Installation Guide

> ⚠️ **Prerequisite**: You need either ROS installed locally on your machine OR access over the network to a robot/computer with ROS installed. This MCP server connects to ROS systems on a robot, so a running ROS environment is required.

## Table of Contents
1. [Transport Methods](#1-transport-methods)
2. [Install MCP Server](#2-install-mcp-server)
3. [Configure LLM Client](#3-configure-llm-client)
4. [Install and Launch Rosbridge](#4-install-and-launch-rosbridge)
5. [Environment-Specific Setup](#5-environment-specific-setup)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Transport Methods

The ROS MCP server supports two transport methods:

### 1.1. STDIO Transport (Default)
- **Best for**: Local development, single-user setups
- **Pros**: Simple setup, no network configuration needed
- **Cons**: MCP server and LLM/MCP client need to be running on the local machine.
- **Use case**: Running MCP server directly with your LLM client

### 1.2. HTTP/Streamable-HTTP Transport
- **Best for**: Remote access, multiple clients, production deployments
- **Pros**: Network accessible, multiple clients can connect
- **Cons**: Requires network configuration, MCP server needs to be run independently.
- **Use case**: Remote robots, team environments, web-based clients

---

## 2. Install MCP Server

### 2.1. Clone the Repository

```bash
git clone https://github.com/robotmcp/ros-mcp-server.git
cd ros-mcp-server
```

Note the **absolute path** to the cloned directory — you’ll need this later when configuring your language model client.

### 2.2. Install UV (Python Virtual Environment Manager)

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


### 2.3. Install Dependencies

```bash
uv sync
```

---

## 3. Configure LLM Client

The ROS MCP server works with any LLM client that supports MCP. Below are configuration examples for popular clients:

> **💡 Tip**: A template MCP configuration file is available in the `config/` folder of this repository. You can use it as a starting point for your setup.

### 3.1. Claude Desktop (STDIO Transport)

<details>
<summary><strong>Linux (Native)</strong></summary>

#### 3.1.1. Download Claude Desktop
- Follow the installation instruction from the community-supported [claude-desktop-debian](https://github.com/aaddrick/claude-desktop-debian)

#### 3.1.2. Configure Claude Desktop (STDIO Transport)
- Locate and edit the `claude_desktop_config.json` file:
- (If the file does not exist, create it)
```bash
~/.config/Claude/claude_desktop_config.json
```

- Add the following to the `"mcpServers"` section of the JSON file
- Make sure to replace `<ABSOLUTE_PATH>` with the **full absolute path** to your `ros-mcp-server` folder:

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
<summary><strong>macOS</strong></summary>

#### 3.1.1. Download Claude Desktop
- Download from [claude.ai](https://claude.ai/download)

#### 3.1.2. Configure Claude Desktop (STDIO Transport)
- Locate and edit the `claude_desktop_config.json` file:
- (If the file does not exist, create it)
```bash
~/Library/Application\ Support/Claude/claude_desktop_config.json
```

- Add the following to the `"mcpServers"` section of the JSON file
- Make sure to replace `<ABSOLUTE_PATH>` with the **full absolute path** to your `ros-mcp-server` folder:

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

#### 3.1.1. Download Claude Desktop
- Download from [claude.ai](https://claude.ai/download)

#### 3.1.2. Configure Claude Desktop (STDIO Transport via WSL)
- Locate and edit the `claude_desktop_config.json` file:
- (If the file does not exist, create it)
```bash
~/.config/Claude/claude_desktop_config.json
```

- Add the following to the `"mcpServers"` section of the JSON file
- Make sure to replace `<ABSOLUTE_PATH>` with the **full absolute path** to your `ros-mcp-server` folder
- Set the **full WSL path** to your `uv` installation (e.g., `/home/<YOUR_USER>/.local/bin/uv`)
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

### 3.2 Configure Claude Desktop (HTTP Transport)
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

### 3.2. Other LLM Clients

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

### 3.3. Test the Connection
- Launch your LLM client and check connection status
- The ros-mcp-server should be visible in your list of tools

<p align="center">
  <img src="https://github.com/robotmcp/ros-mcp-server/blob/main/docs/images/connected_mcp.png" width="500"/>
</p>

---

## 4. Install and Launch Rosbridge

Rosbridge is required for the MCP server to interface with ROS via WebSocket. It needs to be installed on the same machine that is running ROS.

<details>
<summary><strong>ROS 1</strong></summary>

### 4.1. Install `rosbridge_server`

For ROS Noetic:
```bash
sudo apt install ros-noetic-rosbridge-server
```

<details>
<summary>For other ROS Distros</summary>

```bash
sudo apt install ros-${ROS_DISTRO}-rosbridge-server
```

</details>

### 4.2. Launch rosbridge

```bash
roslaunch rosbridge_server rosbridge_websocket.launch
```

> ⚠️ Don't forget to `source` your ROS workspace before launching, especially if you're using custom messages or services.

</details>

<details>
<summary><strong>ROS 2</strong></summary>

### 4.1. Install `rosbridge_server`

For ROS 2 Humble:
```bash
sudo apt install ros-humble-rosbridge-server
```

<details>
<summary>For other ROS Distros</summary>

```bash
sudo apt install ros-${ROS_DISTRO}-rosbridge-server
```

</details>

### 4.2. Launch rosbridge

```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

> ⚠️ Don't forget to `source` your ROS workspace before launching, especially if you're using custom messages or services.

</details>

---

## 5. Environment-Specific Setup

### 5.1. Linux (Native)
- Follow the standard installation steps above
- No additional configuration needed for STDIO transport
- For HTTP transport, ensure firewall allows the configured port

### 5.2. Windows with WSL
- Install WSL2 with Ubuntu distribution
- Install ROS in WSL environment
- Use WSL paths in MCP client configuration when configuring STDIO transport

### 5.3. macOS
- Follow standard installation steps
- No additional configuration needed for STDIO transport
- For HTTP transport, ensure firewall allows the configured port

---

## 6. Troubleshooting

### 6.1. Common Issues

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

### 6.2. Debug Commands

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

### 6.3. Getting Help

If you're still having issues:

1. **Check the logs**: Look for error messages in your LLM client and MCP server logs
2. **Test with turtlesim**: Try the [turtlesim tutorial](../examples/1_turtlesim/README.md) to verify basic functionality
3. **Open an issue**: Create an issue on the [GitHub repository](https://github.com/robotmcp/ros-mcp-server/issues) with:
   - Your operating system
   - ROS version
   - LLM client being used
   - Error messages
   - Steps to reproduce

---

## 7. You're Ready to Go!

You can test out your server with any robot that you have running. Just tell your AI to connect to the robot on its target IP. (Default is localhost, so you don't need to tell it to connect if the MCP server is installed on the same machine as your ROS)

✅ **Tip:** If you don't currently have any robots running, turtlesim is considered the hello-ROS robot to experiment with. It does not have any simulation depenencies such as Gazebo or IsaacSim. 

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

## **Optional: Using Devcontainer**  
1. Install [VSCode](https://code.visualstudio.com/) and the **Remote - Containers** extension.  
2. Open the `ros-mcp-server` repository in VSCode.  
3. When prompted, **reopen in container**.  
   - The container includes ROS2 Humble, Python 3.10+, `ruff`, `pre-commit`, `uv`, and `git`.  
   - The repository is mounted at `/root/workspace`.  
   - **Note for GUI apps** (`turtlesim`, `rviz`, `Gazebo`): 
     Ensure the container can access your host X server by running the following command once on the host:

     <details>
     <summary> Ubuntu host </summary>

     ```bash
     sudo apt install x11-xserver-utils   # if xhost is not installed
     xhost +local:root                    # allow container user access
     ```
     </details>

     <details>
     <summary> Windows WSL2 host </summary>

     ```bash
     export DISPLAY=$(grep nameserver /etc/resolv.conf | awk '{print $2}'):0
     export QT_X11_NO_MITSHM=1
     xhost +local:root
     ```
     </details>
     

4. You can now control the Turtlesim robot following **Step-2** and **Step-4** from the above given manual installation.
5. Initialize pre-commit hooks (optional but recommended):
   ```bash
   pre-commit install
   pre-commit run --all-files
   ```
5. Check Python code formatting with `ruff`
   ```bash
   ruff check .
   ruff format --check .
   ```
  <details>
  <summary>SSH Agent Setup for Git (click to expand)</summary>

  This should be run on the host side prior to building the devcontainer.
  ```bash
  # Start the SSH agent
  eval "$(ssh-agent -s)"

  # List keys currently loaded
  ssh-add -l
  ```

  If it says “The agent has no identities”, you must load your key, for example:
  ```bash
  ssh-add ~/.ssh/id_ed25519
  ssh-add -l   # confirm fingerprint shows up
  ```
  </details>
  
   **Note:** This setup has been tested and verified on Ubuntu.
