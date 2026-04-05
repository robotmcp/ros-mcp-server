# HTTP Transport

By default, AI clients launch the MCP server automatically using the **stdio** transport. This is the simplest setup and works for most users.

As an alternative, you can run the MCP server as a standalone HTTP service using the **streamable-http** transport. This is useful when the MCP server needs to be accessed by multiple clients, run on a different machine from the AI client (for example run on the robot), or when [installing the MCP server from source](from-source.md).

## When to Use HTTP Transport

| | STDIO (Default) | HTTP/Streamable-HTTP |
|---|---|---|
| **Best for** | Local development, single-user setups | Remote access, multiple clients, production deployments |
| **Pros** | Simple setup, no network configuration needed | Network accessible, multiple clients can connect |
| **Cons** | MCP server and AI client must be on the same machine | Requires network configuration, server must be started manually |
| **Use case** | Running MCP server directly with your AI client | Remote robots, team environments, web-based clients, development |

## Start the MCP Server in HTTP Mode

```bash
uvx ros-mcp --transport streamable-http --host 127.0.0.1 --port 9000
```

The server will start listening at `http://127.0.0.1:9000/mcp`.

To make it accessible from other machines on the network, use `--host 0.0.0.0`.

## Configure Your AI Client

Point your AI client to the MCP server's HTTP endpoint. The configuration varies by client, but the URL is the same:

```
http://<server-ip>:9000/mcp
```

Example JSON configuration (used by Claude Desktop, Cursor, and others):

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

## Environment Variables (Legacy)

The server can also be configured using environment variables instead of command-line arguments:

```bash
export MCP_TRANSPORT=streamable-http
export MCP_HOST=127.0.0.1
export MCP_PORT=9000
uvx ros-mcp
```

Command-line arguments take precedence over environment variables.

---

For the default stdio setup, see the [client setup guides](installation.md#step-1-set-up-your-ai-client).
