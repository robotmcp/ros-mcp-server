# Step 1: Claude Code Setup

[Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) is Anthropic's CLI tool for working with Claude. It supports MCP servers natively. If you don't have it yet, see the [installation instructions](https://docs.anthropic.com/en/docs/claude-code/overview#getting-started).

## 1. Install uv

[uv](https://docs.astral.sh/uv/) is needed to run the MCP server via `uvx`.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

See the [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/) for other platforms or troubleshooting.

## 2. Add the MCP Server

Add the ROS-MCP server to Claude Code:

```bash
claude mcp add ros-mcp -- uvx ros-mcp --transport=stdio
```

This registers the server so that Claude Code will launch it automatically when needed.

## 3. Verify the Setup

Verify the server was added:

```bash
claude mcp list
```

You should see `ros-mcp` in the output.

Now start Claude Code and ask it to connect to a robot:

```bash
claude
```

```
Connect to the robot on localhost using the ros-mcp server
```

The MCP server will attempt to reach a robot on the same machine. It should report that the IP is reachable but the rosbridge port is closed — this confirms the MCP server is set up correctly. 

> **Tip:** If your AI assistant can't find the ros-mcp server, exit and restart Claude Code so it picks up the new configuration.

To complete the connection, [set up rosbridge](../rosbridge.md) on your robot.

## Next Step

Set up rosbridge on the machine where ROS is running: [Step 2: Rosbridge Setup](../rosbridge.md)

---

### Advanced

- [HTTP transport](../http-transport.md) — run the MCP server as a standalone HTTP service using the MCP http transport instead of default stdio transport.
- Alternate installation methods:
  - [Install via pip](../pip.md) — traditional `pip install` or install from source with pip
  - [Install from source](../from-source.md) — for developers who need to modify the server code

---

[Back to Installation Guide](../installation.md) | [Troubleshooting](../troubleshooting.md)
