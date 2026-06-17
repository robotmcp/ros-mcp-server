# Troubleshooting

[Back to Installation Guide](installation.md)

## MCP Server Not Appearing in Client

**Symptoms:** The ros-mcp-server doesn't show up in your AI client's tool list.

**Solutions:**
1. **Restart your client completely** — some clients cache MCP server state on startup.
2. **Test the server manually** to check for install issues:
   ```bash
   uvx ros-mcp --help
   ```
3. **Check your client's logs** for error messages related to MCP server initialization.

## macOS: "Could not attach to MCP server" / `uvx` Not Found

**Symptoms:** On macOS, Claude Desktop reports "Could not attach to MCP server ros-mcp-server", even though `uvx ros-mcp --help` works fine in your terminal.

**Cause:** The default macOS config launches the server with `zsh -lc`, which starts a **login, non-interactive** shell. That sources `~/.zprofile` but **not** `~/.zshrc`. The `uv` installer adds `~/.local/bin` to your `PATH` in `~/.zshrc` only, so the subprocess Claude Desktop spawns can't find `uvx`.

Reproduce the clean-subprocess environment Claude Desktop uses:
```bash
env -i HOME="$HOME" USER="$USER" zsh -lc 'which uvx'
# "uvx not found" → you are hitting this issue
```

**Solutions** (pick one):

1. **Make `~/.local/bin` available to login shells** — add it to `~/.zprofile` (which `zsh -lc` *does* source):
   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zprofile
   ```
   Then fully restart Claude Desktop.

2. **Use the absolute path to `uvx`** in `claude_desktop_config.json` instead of going through a shell. Find it with `which uvx` (usually `~/.local/bin/uvx`):
   ```json
   {
     "mcpServers": {
       "ros-mcp-server": {
         "command": "/Users/<you>/.local/bin/uvx",
         "args": ["ros-mcp", "--transport=stdio"]
       }
     }
   }
   ```

## Connection Refused / Cannot Reach Rosbridge

**Symptoms:** "Connection refused", "No valid session ID provided", or timeout errors when trying to interact with ROS.

**Solutions:**
1. **Verify rosbridge is running** on the robot's machine:
   ```bash
   # ROS 2
   ros2 topic list

   # ROS 1
   rostopic list
   ```
2. **Test rosbridge directly** from the robot's machine:
   ```bash
   curl -I http://localhost:9090
   ```
3. **Check the IP address** — if the robot is on a different machine, make sure you're using the correct IP and that both machines are on the same network.
4. **Check firewall rules** — ensure port 9090 (rosbridge default) is open on the robot's machine.

## WSL-Specific Issues

**Symptoms:** Issues when running on Windows with WSL.

**Solutions:**
1. **Use the correct WSL distribution name** in your MCP config (e.g., `"Ubuntu-22.04"` not `"Ubuntu"`). Check with:
   ```bash
   wsl --list --verbose
   ```
2. **Clone repos in the Linux filesystem** — use `/home/username/`, not `/mnt/c/Users/username/`. The Windows filesystem mount has poor performance and can cause permission issues.
3. **Test the server in WSL directly:**
   ```bash
   uvx ros-mcp --help
   ```

## HTTP Transport Issues

**Symptoms:** HTTP transport not working or connection timeouts.

**Solutions:**
1. **Check the server is running** — HTTP transport requires starting the server manually:
   ```bash
   uvx ros-mcp --transport streamable-http --host 127.0.0.1 --port 9000
   ```
2. **Verify port availability:**
   ```bash
   netstat -tulpn | grep :9000
   ```
3. **Test the endpoint directly:**
   ```bash
   curl http://localhost:9000/mcp
   ```
4. **Check firewall rules** if accessing from another machine.

## Debug Commands

| What to check | Command |
|---------------|---------|
| ROS 2 topics | `ros2 topic list` |
| ROS 1 topics | `rostopic list` |
| Rosbridge reachable | `curl -I http://localhost:9090` |
| MCP server works | `uvx ros-mcp --help` |
| Running processes | `ps aux \| grep rosbridge` |
| WSL distributions | `wsl --list --verbose` |

## Still Having Issues?

1. **Check logs** — look for error messages in your AI client and MCP server output. Running logs through an LLM can help with debugging.
2. **Test with turtlesim** — verify basic functionality with the [Turtlesim Tutorial](../../examples/1_turtlesim/README.md).
3. **Open an issue** on the [GitHub repository](https://github.com/robotmcp/ros-mcp-server/issues) with:
   - Your operating system
   - ROS version
   - AI client being used
   - Error messages
   - Steps to reproduce
