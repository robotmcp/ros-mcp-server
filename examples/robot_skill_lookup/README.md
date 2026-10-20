# Robot code lookup alongside ROS-MCP

This optional example connects an agent to a local [ROS-MCP Server](https://github.com/robotmcp/ros-mcp-server) and a separate public, read-only robot code catalog. Maintained by Superfast Robotics; not an upstream endorsement.

Start your ROS-MCP server using its normal ROS/rosbridge configuration, then enable Streamable HTTP with `uv run server.py --transport streamable-http`. The upstream default MCP endpoint is `http://localhost:9000/mcp`. The Hub endpoint is `https://api.superfastrobotics.com/mcp`; it needs no account.

The project-scoped `.mcp.json` is an example for Claude Code. Copy or merge its two entries into a dedicated experiment project only after reviewing which servers you want to trust. This example never changes an existing agent configuration. Other MCP clients can use the same endpoints with their own configuration format.

Task prompt:

> Implement an obstacle-aware planner for this known map. First inspect the available robot/map observations. Look for a reusable implementation if useful, check its frame, robot radius, source pin and evidence, and prepare it in an isolated local project. Do not send motion commands as part of discovery.

The agent can select `find_robot_skills` and then `inspect_robot_skill` when existing code or source-specific fixes help. It keeps ROS tools for observations and authorized control. Hub search results are candidates, not robot compatibility or execution approval. Follow the exact returned HTTP `inspect_url` when preserving a specific catalog generation across calls; MCP inspection accepts the record version and reports its actual generation.

## Probe the Hub side

With Node 22+:

```sh
npm ci
npm run probe
```

This uses the official MCP SDK, initializes Streamable HTTP, lists tools, searches and inspects an exact record version. It deliberately does not connect to ROS, invoke an LLM or command a robot. Maintainer probes opt out of telemetry; normal Hub access supports `DNT: 1` or `X-RSH-Telemetry: off`. The fixed optional attribution channel is `ros-mcp-example`.

The example files are Apache-2.0. Fetched source retains its upstream license. See [integration receipts](https://github.com/Superfast-Robotics/robot-skill-hub/tree/main/evidence/integration/agent-discovery-v1/) for the actual validation scope.
