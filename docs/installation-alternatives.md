# Alternate Installation and Configuration Options

This document covers alternative methods for installing the ROS-MCP server, configuring it with different transport options, and using it with different LLM clients.

---

## Alternative Installation Options

### Option A: Install using pip
For users who prefer traditional pip installation:

```bash
pip install ros-mcp
```
> **⚠️ Important**: This package requires pip version 23.0 or higher. Check your pip version with `pip --version` and upgrade if needed:
> **⚠️ Important**: This package requires python version 3.10 or higher. Check your python version with `python3 --version` and upgrade if needed:
```bash
python3 -m pip install --upgrade pip
```

### Option B: Install from Source
For developers or advanced users who need to modify the source code, see [Installation from Source](installation-from-source.md).

### Option C: Install from Source using pip
For developers who want to install from source but still use pip:

```bash
# Clone the repository
git clone https://github.com/robotmcp/ros-mcp-server.git
cd ros-mcp-server

# Install from source using pip
pip install .
```

> **⚠️ Important**: This package requires pip version 23.0 or higher. Check your pip version with `pip --version` and upgrade if needed:
> **⚠️ Important**: This package requires python version 3.10 or higher. Check your python version with `python3 --version` and upgrade if needed:
```bash
python3 -m pip install --upgrade pip
```

---

## Alternate Configuration - HTTP Transport

The default configurations set up the MCP server using the STDIO transport layer, which launches the server as a plugin automatically on launching Claude.

It is also possible to configure the MCP server using the HTTP transport layer, which configures Claude to connect to the MCP server when it is launched as a standalone application.

For HTTP transport, the configuration is the same across all platforms. First start the MCP server manually:

**Linux/macOS/Windows(WSL):**
```bash
cd /<ABSOLUTE_PATH>/ros-mcp-server
# Using command line arguments (recommended)
ros-mcp --transport streamable-http --host 127.0.0.1 --port 9000

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

---

## Comparison between default (STDIO) and HTTP Transport

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

---

## Alternate Clients

### Cursor IDE
For detailed Cursor setup instructions, see our [Cursor Tutorial](../examples/7_cursor/README.md).

### ChatGPT
For detailed ChatGPT setup instructions, see our [ChatGPT Tutorial](../examples/6_chatgpt/README.md).

### Google Gemini
For detailed Gemini setup instructions, see our [Gemini Tutorial](../examples/2_gemini/README.md).

### Custom MCP Client
You can also use the MCP server directly in your Python code. 
<details>
<summary>Here is a python example of how to integrate it programmatically</summary>

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="uv",
        args=["--directory", "/path/to/ros-mcp-server", "run", "server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Use the MCP server
            result = await session.call_tool("get_topics", {})
            print(result)
```

</details>

