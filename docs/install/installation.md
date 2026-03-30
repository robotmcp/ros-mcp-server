# Installation Guide

The ROS-MCP server connects any AI assistant that supports the [MCP protocol](https://modelcontextprotocol.io/) to a robot running ROS. It is built to work across machines, supporting having the AI assistant on the user's laptop connect with robots on the local network.

Installation involves two machines (both parts can be installed on the same machine if your AI client runs directly on the robot):

| Machine | What to install | Prerequisites | Purpose |
|---------|----------------|---------------|---------|
| **Your machine** (laptop/desktop) | An AI client + the ROS-MCP server | An account with an AI provider (e.g., Claude, Codex, Gemini) | Runs the language model and the MCP server |
| **The robot's machine** | rosbridge | ROS installed | Creates a WebSocket to ROS for the MCP server to reach |

Both machines must be on the **same local network**. Using a VPN is a great option if you want to connect to robots over the internet.

Follow the three steps below to get up and running. Each step includes quick inline commands and a link to a more detailed guide.

---

## Step 1: Set Up Your AI Client


Quick instructions for setup with Claude Code are below:

```bash
# On the user's machine:
# 1.1. Install uv (Python package runner)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 1.2. Add the MCP server to Claude Code
claude mcp add ros-mcp -- uvx ros-mcp --transport=stdio
```

For detailed instructions or to set up a different AI client, follow the guide for your client below.


| Client | Description | Guide |
|--------|-------------|-------|
| **Claude Code** (Recommended) | Anthropic's CLI for Claude | [Setup guide](clients/claude-code.md) |
| Codex CLI | OpenAI's CLI agent | [Setup guide](clients/codex-cli.md) |
| Gemini CLI | Google's CLI for Gemini | [Setup guide](clients/gemini-cli.md) |
| Claude Desktop | Anthropic's desktop app | [Setup guide](clients/claude-desktop.md) |
| ChatGPT | OpenAI's desktop app | [Setup guide](clients/chatgpt.md) |
| Cursor | AI-powered IDE | [Setup guide](clients/cursor.md) |
| Robot MCP Client | Lightweight terminal client | [Setup guide](clients/robot-mcp-client.md) |
| Custom / Programmatic | Python MCP SDK | [Setup guide](clients/custom-client.md) |

## Step 2: Set Up Rosbridge on the Robot

Rosbridge runs on the robot's machine (wherever ROS is running). It provides a WebSocket interface that the MCP server on your machine connects to over the network.

Follow the [Step 2: Rosbridge setup guide](rosbridge.md) for detailed instructions and verification. Quick instructions for it are below:

```bash
# On the robot:
# 2.1. Install Rosbridge
sudo apt update
sudo apt install ros-<your ros distro>-rosbridge-server
```
```bash
# 2.2. Launch Rosbridge
source /<path to ros WS>/install/setup.bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```



## Step 3: Connect to Your Robot

Now that your AI client has the MCP server configured and rosbridge is running on the robot, you're ready to connect.


Follow the detailed [Step 3: Connect to your robot and explore](connect.md) guide for connecting and for sample commands. For a quick start, launch your AI assistant and type:
```bash
Connect to the robot on <ip address> and tell me what topics and services you see.
```

---

## Additional Resources

- [Troubleshooting](troubleshooting.md) — common issues and debug commands
- [Examples](../../examples/) — tutorials for turtlesim, Unitree Go2, LIMO, TurtleBot3, and more
- [ROS-MCP Demos](https://github.com/robotmcp/demos-ros-mcp-server) — advanced demos with simulated robots in Gazebo
