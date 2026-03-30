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

## 4. Run the Server

You can run the server directly from source with specific transport options:

```bash
uv run server.py --transport streamable-http --host 127.0.0.1 --port 9000
```
See the [HTTP transport](http-transport.md) page for details.

## Next Steps

- [Set up rosbridge on the robot](rosbridge.md)
- [Troubleshooting](troubleshooting.md)
