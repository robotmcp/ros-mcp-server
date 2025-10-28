# Installation from Source

> ⚠️ **Prerequisite**: You need either ROS installed locally on your machine OR access over the network to a robot/computer with ROS installed. This MCP server connects to ROS systems on a robot, so a running ROS environment is required.

This guide covers installing the ROS MCP Server from source code. For most users, we recommend using the [pip install method](installation.md) instead.

## 1. Clone the Repository

```bash
git clone https://github.com/robotmcp/ros-mcp-server.git
```

> ⚠️ **WSL Users**: Clone the repository in your WSL home directory (e.g., `/home/username/`) instead of the Windows filesystem mount (e.g., `/mnt/c/Users/username/`). Using the native Linux filesystem provides better performance and avoids potential permission issues.

Note the **absolute path** to the cloned directory — you'll need this later when configuring your language model client.

## 2. Install UV (Python Virtual Environment Manager)

You can install [`uv`](https://github.com/astral-sh/uv) using one of the following methods:

<details>
<summary><strong>Option A: Shell installer</strong></summary>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

</details>

<details>
<summary><strong>Option B: Using pip</strong></summary>

```bash
pip install uv
```

</details>

## 3. Install Dependencies

Navigate to the cloned repository and install dependencies:

```bash
cd ros-mcp-server
uv sync
```

## 4. Configure Language Model Client

Any LLM client that supports MCP can be used. We use **Claude Desktop** for testing and development.

### 4.1. Download Claude Desktop

<details>
<summary><strong>Linux (Ubuntu)</strong></summary>

- Follow the installation instructions from the community-supported [claude-desktop-debian](https://github.com/aaddrick/claude-desktop-debian)

</details>

<details>
<summary><strong>MacOS</strong></summary>

- Download from [claude.ai](https://claude.ai/download)

</details>

<details>
<summary><strong>Windows (Using WSL)</strong></summary>

This will have Claude running on Windows and the MCP server running on WSL. We assume that you have cloned the repository and installed UV on your [WSL](https://apps.microsoft.com/detail/9pn20msr04dw?hl=en-US&gl=US)

- Download from [claude.ai](https://claude.ai/download)

</details>

### 4.2. Configure Claude Desktop to launch the MCP server

<details>
<summary><strong>Linux (Ubuntu)</strong></summary>

- Locate and edit the `claude_desktop_config.json` file:
- (If the file does not exist, create it)
```bash
~/.config/Claude/claude_desktop_config.json
```

- Add the following to the `"mcpServers"` section of the JSON file
- Make sure to replace `<ABSOLUTE_PATH>` with the **full absolute path** to your `ros-mcp-server` folder (note: `~` for home directory may not work in JSON files):

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

</details>

<details>
<summary><strong>MacOS</strong></summary>

- Locate and edit the `claude_desktop_config.json` file:
- (If the file does not exist, create it)
```bash
~/Library/Application\ Support/Claude/claude_desktop_config.json
```

- Add the following to the `"mcpServers"` section of the JSON file
- Make sure to replace `<ABSOLUTE_PATH>` with the **full absolute path** to your `ros-mcp-server` folder (note: `~` for home directory may not work in JSON files):

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

</details>

<details>
<summary><strong>Windows (Using WSL)</strong></summary>

- Locate and edit the `claude_desktop_config.json` file:
- (If the file does not exist, create it)
```bash
~/.config/Claude/claude_desktop_config.json
```

- Add the following to the `"mcpServers"` section of the JSON file
- Make sure to replace `<ABSOLUTE_PATH>` with the **full absolute path** to your `ros-mcp-server` folder (note: `~` for home directory may not work in JSON files):
- Set the **full WSL path** to your `uv` installation (e.g., `/home/youruser/.local/bin/uv`)
- Use the correct **WSL distribution name** (e.g., `"Ubuntu-22.04"`)

```json
{
  "mcpServers": {
    "ros-mcp-server": {
      "command": "wsl",
      "args": [
        "-d", "Ubuntu-22.04",
        "/home/<YOUR_USER>/.local/bin/uv",
        "--directory",
        "/<ABSOLUTE_PATH>/ros-mcp-server",
        "run",
        "server.py"
      ]
    }
  }
}
```

</details>

### 4.3. Alternative Configuration - HTTP Transport

The above configurations sets up the MCP server using the default STDIO transport layer, which launches the server as a plugin automatically on launching Claude.

It is also possible to configure the MCP server using the http transport layer, which configures Claude to connect to the MCP server when it is launched as a standalone application.

For HTTP transport, the configuration is the same across all platforms. First start the MCP server manually:

**Linux/macOS/Windows(WSL):**
```bash
cd /<ABSOLUTE_PATH>/ros-mcp-server
# Using command line arguments (recommended)
uv run server.py --transport streamable-http --host 127.0.0.1 --port 9000

# Or using environment variables (legacy)
export MCP_TRANSPORT=streamable-http
export MCP_HOST=127.0.0.1
export MCP_PORT=9000
uv run server.py
```

Then configure Claude Desktop to connect to the HTTP server (same for all platforms):

```json
{
  "mcpServers": {
    "ros-mcp-server-http": {
      "name": "ROS-MCP Server (http)",
      "transport": "http",
      "url": "http://127.0.0.1:9000/mcp"
    }
  }
}
```

<details>
<summary> Comparison between STDIO and HTTP Transport</summary>

#### STDIO Transport (Default)
- **Best for**: Local development, single-user setups
- **Pros**: Simple setup, no network configuration needed
- **Cons**: MCP server and LLM/MCP client need to be running on the local machine.
- **Use case**: Running MCP server directly with your LLM client

#### HTTP/Streamable-HTTP Transport
- **Best for**: Remote access, multiple clients, production deployments
- **Pros**: Network accessible, multiple clients can connect
- **Cons**: Requires network configuration, MCP server needs to be run independently.
- **Use case**: Remote robots, team environments, web-based clients

</details>

### 4.4. Test the connection
- Launch Claude Desktop and check connection status.
- The ros-mcp-server should be visible in your list of tools.

<p align="center">
  <img src="https://github.com/robotmcp/ros-mcp-server/blob/main/docs/images/connected_mcp.png" width="500"/>
</p>

<details>
<summary><strong> Troubleshooting </strong></summary>

- If the `ros-mcp-server` doesn't appear even after correctly configuring `claude_desktop_config.json`, try completely shutting down Claude Desktop using the commands below and then restarting it. This could be a Claude Desktop caching issue.
```bash
# Completely terminate Claude Desktop processes
pkill -f claude-desktop
# Or alternatively
killall claude-desktop

# Restart Claude Desktop
claude-desktop
```

</details>

## Next Steps

Once you have the MCP server installed from source, continue with the remaining setup steps:

- **Install and run rosbridge** (on the target robot)
- **Test your connection**
- **Troubleshooting** (if needed)

For detailed instructions on these steps, see the [main installation guide](installation.md#3-install-and-run-rosbridge-on-the-target-robot-where-ros-will-be-running).
