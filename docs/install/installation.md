# Installation Guide

The ROS-MCP server connects any AI assistant that supports the [MCP protocol](https://modelcontextprotocol.io/) to a robot running ROS.

It is built to work across machines, supporting having the AI assistant on the user's laptop interact with robots on the local network. 

## What You'll Need

Installation involves two machines (Both parts can be installed on the same machine  if your AI client runs directly on the robot):

| Machine | What to install | Prerequisites | Purpose |
|---------|----------------|---------------|---------|
| **Your machine** (laptop/desktop) | An AI client + the ROS-MCP server | An account with an AI provider (e.g., Claude, Codex, Gemini) | Runs the language model and the MCP server |
| **The robot's machine** | rosbridge | ROS installed | Creates a WebSocket to ROS for the MCP server to reach |

Both machines must be on the **same local network**. Using a VPN is a great option if you want to connect to robots over the internet.

## Quickstart

The fastest way to get started using [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) (recommended):



```bash
# 4. Start Claude Code. Once it launches, give it your robot IP and tell it to connect.
claude
```

For detailed steps, follow the links below.

---

## Step 1: Set Up Your AI Client


Quick instructions for setup with Claude Code (recommended) are below:

```bash
# On the user's machine:
# 1.1. Install uv (Python package runner)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 1.2. Add the MCP server to Claude Code
claude mcp add ros-mcp -- uvx ros-mcp --transport=stdio
```

For more detailed instructions and verification, choose your AI client and follow its detailed setup guide. 


| Client | Description | Guide |
|--------|-------------|-------|
| **Claude Code** (Recommended) | Anthropic's CLI for Claude | [Setup guide](clients/claude-code.md) |
| Claude Desktop | Anthropic's desktop app | *Coming soon* |
| Codex CLI | OpenAI's CLI agent | *Coming soon* |
| Gemini CLI | Google's CLI for Gemini | *Coming soon* |
| Cursor | AI-powered IDE | *Coming soon* |
| ChatGPT | OpenAI's desktop app | *Coming soon* |
| Robot MCP Client | Lightweight terminal client | *Coming soon* |
| Custom / Programmatic | Python MCP SDK | *Coming soon* |

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
