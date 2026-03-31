# Step 1: Custom / Programmatic Client

You can use the ROS-MCP server directly in your Python code using the [MCP SDK](https://github.com/modelcontextprotocol/python-sdk).

## Example

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="uvx",
        args=["ros-mcp", "--transport=stdio"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(tools)

            # Call a tool
            result = await session.call_tool("get_topics", {})
            print(result)
```

## Prerequisites

- **uv** installed — see [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/)
- **MCP Python SDK** — `pip install mcp`

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
