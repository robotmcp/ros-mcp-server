# Installation from Source

This guide is for developers who need to modify the ROS-MCP server source code. For most users, we recommend the standard [installation via uvx](clients/claude-code.md).

## 1. Clone the Repository

```bash
git clone https://github.com/robotmcp/ros-mcp-server.git
```

> **WSL Users**: Clone in your WSL home directory (e.g., `/home/username/`), not the Windows filesystem mount (e.g., `/mnt/c/Users/username/`). The native Linux filesystem provides better performance and avoids permission issues.

## 2. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

See the [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/) for other platforms or troubleshooting.

## 3. Install Dependencies

```bash
cd ros-mcp-server
uv sync
```

## 4. Test the Server

```bash
uv run server.py --help
```

If this prints the help output, the server is installed correctly and ready to run.

## 5. Configure Your AI Client

When running from source, use `uv run server.py` with the path to the cloned repository instead of `uvx ros-mcp`.

The recommended approach is to use [HTTP transport](http-transport.md), which runs the server as a standalone process:

```bash
uv run server.py --transport streamable-http --host 127.0.0.1 --port 9000
```

Then point your AI client to `http://127.0.0.1:9000/mcp`. See the [HTTP transport](http-transport.md) page for client configuration details.

Alternatively, you can configure your client to launch the server directly via stdio. For example, with Claude Code:

```bash
claude mcp add ros-mcp -- uv --directory /<path-to>/ros-mcp-server run server.py --transport=stdio
```

For clients that use a JSON config file:
```json
{
  "command": "uv",
  "args": [
    "--directory", "/<path-to>/ros-mcp-server",
    "run", "server.py", "--transport=stdio"
  ]
}
```

## Next Steps

- [Set up your AI client](installation.md#step-1-set-up-your-ai-client)
- [Set up rosbridge on the robot](rosbridge.md)

---

[Back to Installation Guide](installation.md) | [Troubleshooting](troubleshooting.md)
