# Step 1: ChatGPT Setup

[ChatGPT Desktop](https://chatgpt.com/download) is OpenAI's desktop application. It supports MCP servers through its Connectors settings. Download it from [chatgpt.com/download](https://chatgpt.com/download) or the Microsoft Store.

> **Recommended alternative:** ChatGPT's MCP setup is more complex than other clients because it requires an ngrok tunnel. For a simpler experience, consider using [Codex CLI](codex-cli.md) or [Claude Code](claude-code.md) instead. 

> **Note:** ChatGPT Desktop requires a public HTTPS URL to connect to MCP servers, so you'll need to run the MCP server in HTTP mode with an [ngrok](https://ngrok.com) tunnel. See the [HTTP transport](../http-transport.md) guide for details on the transport layer.

## 1. Install uv

[uv](https://docs.astral.sh/uv/) is needed to run the MCP server via `uvx`.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

See the [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/) for other platforms or troubleshooting.

## 2. Install and Configure ngrok

[ngrok](https://ngrok.com) creates a public HTTPS tunnel to your local MCP server.

1. Install ngrok from [ngrok.com/download](https://ngrok.com/download)
2. Create an account and add your authtoken:
   ```bash
   ngrok config add-authtoken <YOUR_AUTHTOKEN>
   ```
3. Get a free static domain from the [ngrok dashboard](https://dashboard.ngrok.com/domains) (e.g., `abc123-xyz789.ngrok-free.app`)

## 3. Start the MCP Server and Tunnel

Start the MCP server in HTTP mode:
```bash
uvx ros-mcp --transport streamable-http --host 127.0.0.1 --port 9000
```

In a separate terminal, start the ngrok tunnel:
```bash
ngrok http --url=<your-domain>.ngrok-free.app 9000
```

Verify the tunnel is working:
```bash
curl https://<your-domain>.ngrok-free.app/mcp
```

## 4. Configure ChatGPT

1. Open ChatGPT Desktop
2. Go to **Settings** (bottom left) > **Connectors**
3. Create a new connector:
   - **Name:** ROS-MCP Server
   - **MCP Server URL:** `https://<your-domain>.ngrok-free.app/mcp`
   - **Authentication:** No authentication
   - Check **I trust this application**
4. In a new chat, click **+** > **Developer Mode** > **Add sources** > Activate **ROS-MCP Server**

## 5. Verify the Setup

Ask ChatGPT:

```
Connect to the robot on localhost using the ros-mcp server
```

The MCP server will attempt to reach a robot on the same machine. It should report that the IP is reachable but the rosbridge port is closed — this confirms the MCP server is set up correctly.

> **Tip:** If your AI assistant can't find the ros-mcp server, make sure both the MCP server and ngrok tunnel are still running, then restart ChatGPT Desktop.

To complete the connection, [set up rosbridge](../rosbridge.md) on your robot.

## Next Step

Set up rosbridge on the machine where ROS is running: [Step 2: Rosbridge Setup](../rosbridge.md)

---

### Advanced

- Alternate installation methods:
  - [Install via pip](../pip.md) — traditional `pip install` or install from source with pip
  - [Install from source](../from-source.md) — for developers who need to modify the server code

---

[Back to Installation Guide](../installation.md) | [Troubleshooting](../troubleshooting.md)
