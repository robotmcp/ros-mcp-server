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
