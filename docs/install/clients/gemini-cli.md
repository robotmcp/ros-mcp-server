# Step 1: Gemini CLI Setup

[Gemini CLI](https://github.com/google-gemini/gemini-cli) is Google's CLI for Gemini. It supports MCP servers through a JSON settings file. If you don't have it yet, see the [installation instructions](https://github.com/google-gemini/gemini-cli#installation).

## 1. Install uv

[uv](https://docs.astral.sh/uv/) is needed to run the MCP server via `uvx`.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

See the [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/) for other platforms or troubleshooting.

## 2. Add the MCP Server

Edit your Gemini CLI settings file at `~/.gemini/settings.json` and add the MCP server:

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

> **Tip:** If you're having trouble with the config file, ask Gemini to help set it up. Tell it that the command to run the MCP server is `uvx ros-mcp` and it can generate the correct configuration.

## 3. Verify the Setup

Start Gemini CLI and ask it to connect to a robot:

```bash
gemini
```

```
Connect to the robot on localhost using the ros-mcp server
```

The MCP server will attempt to reach a robot on the same machine. It should report that the IP is reachable but the rosbridge port is closed — this confirms the MCP server is set up correctly.

> **Tip:** If your AI assistant can't find the ros-mcp server, exit and restart Gemini CLI so it picks up the new configuration.

To complete the connection, [set up rosbridge](../rosbridge.md) on your robot.

## Next Step

Set up rosbridge on the machine where ROS is running: [Step 2: Rosbridge Setup](../rosbridge.md)

---

### Advanced

- [HTTP transport](../http-transport.md) — run the MCP server as a standalone HTTP service instead of stdio
- Alternate installation methods:
  - [Install via pip](../pip.md) — traditional `pip install` or install from source with pip
  - [Install from source](../from-source.md) — for developers who need to modify the server code

---

[Back to Installation Guide](../installation.md) | [Troubleshooting](../troubleshooting.md)
