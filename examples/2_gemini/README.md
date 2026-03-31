# Demo, Gemini-CLI with ROS-MCP-Server

## Prerequisite
- Installation of Gemini-CLI. [https://github.com/google-gemini/gemini-cli]
- Installation of ROS or ROS2. Test if ROS is installed by running Turtlesim. If you are not sure, follow, this toturial [https://wiki.ros.org/ROS/Tutorials]
- Installation of ROS-MCP-Server except Section II (installation/settings of Claude desktop)  [Installation Guide](../../docs/install/installation.md). For Gemini CLI-specific setup, see the [Gemini CLI setup guide](../../docs/install/clients/gemini-cli.md)

## Update Gemini CLI MCP settings

- Open `settings.json` file of Gemini CLI, located `~/.gemini/settings.json`
- Add "mcpServer" setting below in the `settings.json`
```json
{
  "mcpServers": {
    "ros-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/<ABSOLUTE_PATH>/ros-mcp-server",
        "run",
        "server.py"
      ]
    }
  }
}
```

## Demo Environment
- Ubuntu 20.04
- ROS Noetic

## Demo Video 

[![Gemini Demo with ROS MCP Server](./image/gemini-demo-ros-mcp.jpeg)](https://youtu.be/UAEG0qTADDk)
