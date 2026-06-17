# Step 1: Claude Desktop Setup

[Claude Desktop](https://claude.ai/download) is Anthropic's desktop application for Claude. It supports MCP servers through a JSON configuration file.

- **Linux**: Install via the community-supported [claude-desktop-debian](https://github.com/aaddrick/claude-desktop-debian)
- **macOS / Windows**: Download from [claude.ai/download](https://claude.ai/download)

## 1. Install uv

[uv](https://docs.astral.sh/uv/) is needed to run the MCP server via `uvx`.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

See the [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/) for other platforms or troubleshooting.

## 2. Add the MCP Server

> ⚠️ **Important**: Quit Claude Desktop **completely** before editing `claude_desktop_config.json`. If the app is running in the background when you save the file, your changes can be silently overwritten the moment you enter a chat. Terminate the process first:
>
> - **Linux:** `pkill -f claude-desktop`
> - **macOS:** Right-click the dock icon → Quit, or `pkill -f -i claude` in Terminal
> - **Windows:** End the `Claude` task in Task Manager (Ctrl+Shift+Esc → find *Claude* → End task)

Locate and edit the `claude_desktop_config.json` file (create it if it doesn't exist):

| OS | Config file path |
|----|-----------------|
| Linux | `~/.config/Claude/claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

Add the following to the file:

**Linux:**
```json
{
  "mcpServers": {
    "ros-mcp-server": {
      "command": "bash",
      "args": ["-lc", "uvx ros-mcp --transport=stdio"]
    }
  }
}
```

**macOS:**
```json
{
  "mcpServers": {
    "ros-mcp-server": {
      "command": "zsh",
      "args": ["-lc", "uvx ros-mcp --transport=stdio"]
    }
  }
}
```

> **macOS: "Could not attach to MCP server"?** `zsh -lc` sources `~/.zprofile` but not `~/.zshrc`, where the `uv` installer puts `~/.local/bin` on your `PATH` — so the subprocess can't find `uvx`. Fix it by adding `~/.local/bin` to `~/.zprofile`, or by using the absolute path to `uvx`. See [Troubleshooting](../troubleshooting.md#macos-could-not-attach-to-mcp-server--uvx-not-found).

**Windows (WSL):**
```json
{
  "mcpServers": {
    "ros-mcp-server": {
      "command": "wsl",
      "args": [
        "-d", "Ubuntu-22.04",
        "bash", "-lc",
        "uvx ros-mcp --transport=stdio"
      ]
    }
  }
}
```

> **WSL users**: Replace `"Ubuntu-22.04"` with your actual WSL distribution name. Check with `wsl --list --verbose`.

## 3. Verify the Setup

1. Completely restart Claude Desktop — the MCP server list is cached on startup. If it doesn't appear, fully terminate the app and relaunch:
   - **Linux:** `pkill -f claude-desktop && claude-desktop`
   - **macOS:** Right-click the dock icon > Quit, or use Activity Monitor to force quit
   - **Windows:** End the task in Task Manager, then relaunch
2. Check that **ros-mcp-server** appears in your list of tools.

> **Tip:** If you're having trouble with the config file, ask Claude to help set it up. Tell it that the command to run the MCP server is `uvx ros-mcp` and it can generate the correct configuration for your OS.

Once the server appears, try asking Claude:

```
Connect to the robot on localhost using the ros-mcp server
```

The MCP server will attempt to reach a robot on the same machine. It should report that the IP is reachable but the rosbridge port is closed — this confirms the MCP server is set up correctly.

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
