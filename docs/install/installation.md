# Installation Guide

The ROS-MCP server lets any [MCP-compatible](https://modelcontextprotocol.io/) AI assistant control a robot running ROS — even from a different machine on the network.

Setup spans two machines on the **same local network** (or one machine if your AI client runs alongside ROS on the same hardware). A VPN is a great option for connecting over the internet.

| Machine | What to install | Prerequisites | Purpose |
|---------|----------------|---------------|---------|
| **Your machine** (laptop/desktop) | An AI client + the ROS-MCP server | An account with an AI provider (e.g., Claude, Codex, Gemini) | Runs the language model and the MCP server |
| **The robot's machine** | rosbridge | ROS installed | Bridges ROS over WebSocket for the MCP server to connect to |

Follow the three steps below to get up and running. Each step includes quick inline commands and a link to a more detailed guide.

---

## Step 1: Set Up Your AI Client


Quick setup with Claude Code:

```bash
# On your machine:
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

Install and launch rosbridge on the machine where ROS is running. See the [Step 2: Rosbridge setup guide](rosbridge.md) for detailed instructions. Quick setup below:

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

See the [Step 3: Connect and explore](connect.md) guide for connecting to your robot and sample commands. For a quick start, launch your AI assistant and type:
```
Connect to the robot on <ip address> and tell me what topics and services you see.
```

---

## Additional Resources

- [Troubleshooting](troubleshooting.md) — common issues and debug commands
- [Examples](../../examples/) — tutorials for turtlesim, Unitree Go2, LIMO, TurtleBot3, and more
- [ROS-MCP Demos](https://github.com/robotmcp/demos-ros-mcp-server) — advanced demos with simulated robots in Gazebo
