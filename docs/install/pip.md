# Install via pip

For most users, we recommend installing via [uvx](clients/claude-code.md) instead. This page covers alternative pip-based installation methods.

## pip install

```bash
pip install ros-mcp
```

> **Requirements:** pip 23.0+ and Python 3.10+. Check your versions with `pip --version` and `python3 --version`. Upgrade pip if needed:
> ```bash
> python3 -m pip install --upgrade pip
> ```

## pip install from source

```bash
git clone https://github.com/robotmcp/ros-mcp-server.git
cd ros-mcp-server
pip install .
```

> **Requirements:** pip 23.0+ and Python 3.10+.

## Configuring Your AI Client

When using pip install, the `ros-mcp` command is installed directly into your environment. Use `ros-mcp` instead of `uvx ros-mcp` when configuring your AI client.

For example, with Claude Code:
```bash
claude mcp add ros-mcp -- ros-mcp --transport=stdio
```

For clients that use a JSON config file:
```json
{
  "command": "ros-mcp",
  "args": ["--transport=stdio"]
}
```

## Next Steps

- [Set up your AI client](installation.md#step-1-set-up-your-ai-client)
- [Set up rosbridge on the robot](rosbridge.md)
- [Troubleshooting](troubleshooting.md)

---

[Back to Installation Guide](installation.md) | [Troubleshooting](troubleshooting.md)
