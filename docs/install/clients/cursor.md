# Step 1: Cursor Setup

[Cursor](https://cursor.com) is an AI-powered IDE. It supports MCP servers through its settings. If you don't have it yet, download it from [cursor.com/downloads](https://cursor.com/downloads).

## 1. Install uv

[uv](https://docs.astral.sh/uv/) is needed to run the MCP server via `uvx`.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

See the [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/) for other platforms or troubleshooting.

## 2. Add the MCP Server

In Cursor, go to **Settings > MCP > New MCP Server** and edit the `mcp.json` file:

**Linux / macOS:**
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

**Windows (WSL):**
```json
{
  "mcpServers": {
    "ros-mcp-server": {
      "command": "wsl",
      "args": [
        "-d", "Ubuntu",
        "/home/<YOUR_USER>/.local/bin/uvx",
        "ros-mcp", "--transport=stdio"
      ]
    }
  }
}
```

> **WSL users**: Replace `<YOUR_USER>` with your WSL username and `"Ubuntu"` with your distribution name. Verify the path to uvx with `wsl -- which uvx`.

> **Tip:** If you're having trouble with the config file, ask Cursor to help set it up. Tell it that the command to run the MCP server is `uvx ros-mcp` and it can generate the correct configuration.

## 3. Verify the Setup

Open a new chat in Cursor and ask:

```
Connect to the robot on localhost using the ros-mcp server
```

The MCP server will attempt to reach a robot on the same machine. It should report that the IP is reachable but the rosbridge port is closed — this confirms the MCP server is set up correctly.

> **Tip:** If your AI assistant can't find the ros-mcp server, restart Cursor so it picks up the new configuration.

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
