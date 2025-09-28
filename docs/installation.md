# Installation Guide

> ⚠️ **Prerequisite**: You need either ROS installed locally on your machine OR access over the network to a robot/computer with ROS installed. This MCP server connects to ROS systems on a robot, so a running ROS environment is required.

Installation includes the following steps:
- Install the MCP server
  - Clone this repository
  - Install uv (Python virtual environment manager)
- Install and configure the Language model client
  - Install any language model client (We demo with Claude Desktop)
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

<details>
<summary><strong>Linux (Ubuntu)</strong></summary>

## 2.1. Download Claude Desktop 
- Follow the installation instruction from the community-supported [claude-desktop-debian](https://github.com/aaddrick/claude-desktop-debian)

## 2.2. Configure Claude Desktop to launch the MCP server
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

## 2.3. Test the connection
- Launch Claude Desktop and check connection status. 
- The ros-mcp-server should be visible in your list of tools.

<p align="center">
  <img src="https://github.com/robotmcp/ros-mcp-server/blob/main/docs/images/connected_mcp.png" width="500"/>
</p>

## 2.4. Troubleshooting
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

<details>
<summary><strong>MacOS</strong></summary>

## 2.1. Download Claude Desktop 
- Download from [claude.ai](https://claude.ai/download)

## 2.2. Configure Claude Desktop to launch the MCP server
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

## 2.3. Test the connection
- Launch Claude Desktop and check connection status. 
- The ros-mcp-server should be visible in your list of tools.

<p align="center">
  <img src="https://github.com/robotmcp/ros-mcp-server/blob/main/docs/images/connected_mcp.png" width="500"/>
</p>

</details>

<details>
<summary><strong>Windows (Using WSL)</strong></summary>


## 2.1. Download Claude Desktop 
This will have Claude running on Windows and the MCP server running on WSL. We assume that you had cloned the repository and installed UV on your [WSL](https://apps.microsoft.com/detail/9pn20msr04dw?hl=en-US&gl=US) 

- Download from [claude.ai](https://claude.ai/download)

## 2.2. Configure Claude Desktop to launch the MCP server
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
        "/home/youruser/.local/bin/uv",
        "--directory",
        "/<ABSOLUTE_PATH>/ros-mcp-server",
        "run",
        "server.py"
      ]
    }
  }
}
```

## 2.3. Test the connection
- Launch Claude Desktop and check connection status. 
- The ros-mcp-server should be visible in your list of tools.

<p align="center">
  <img src="https://github.com/robotmcp/ros-mcp-server/blob/main/docs/images/connected_mcp.png" width="500"/>
</p>

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

```bash
sudo apt install ros-humble-rosbridge-server
```



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
