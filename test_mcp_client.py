#!/usr/bin/env python3
"""Minimal test client for ros-mcp when using streamable-http transport."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import random

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9999  # streamable-http port chosen when starting ros-mcp
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/mcp"


async def call_tool(session: ClientSession, tool_name: str, arguments: dict | None = None) -> dict:
    """Call a tool via MCP protocol."""
    result = await session.call_tool(tool_name, arguments or {})
    response = result.model_dump()

    # Return structured content if available, otherwise parse from text
    if response.get("structuredContent"):
        return response["structuredContent"]
    elif response.get("content") and len(response["content"]) > 0:
        text_content = response["content"][0].get("text", "{}")
        import json
        return json.loads(text_content)
    return response


def load_tree(example_name: str) -> dict:
    """Load a behavior tree from the examples file."""
    examples = json.loads(
        Path("examples/5_docker_turtlesim/example_behavior_tree.json").read_text()
    )
    for entry in examples.get("examples", []):
        if entry.get("name") == example_name:
            return entry["tree"]
    raise ValueError(f"No example named '{example_name}' found")


async def main() -> None:
    """Main test routine using MCP protocol."""
    async with streamablehttp_client(BASE_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()

            # List available tools (optional, for debugging)
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}\n")

            # Connect to robot
            input("Ready to connect to robot ...")
            connection = await call_tool(session, "connect_to_robot", {
                "ip": "127.0.0.1",
                "port": 9090,
            })
            print("Connect result:\n", json.dumps(connection, indent=2))

            # View available actions
            input("Available actions ...")
            actions = await call_tool(session, "get_actions", {})
            actions_list = actions["actions"]
            for idx, name in enumerate(actions_list):
                action_type = await call_tool(session, "get_action_type", {"action": name})
                print(f"Action: {name}, Type: {action_type['type']}")

            while True:
                x, y = random.randint(0,5), random.randint(0,5)
                # After connecting and listing actions, before/after the BT flow:
                input(f"Ready to send a single action to ({x}, {y})")
                goal = {
                    "x": x,
                    "y": y,
                    "theta": 0.0,
                }
                action_result = await call_tool(session, "send_action_goal", {
                    "action_name": "/turtle1/goto_pose",
                    "action_type": "turtlesim_custom_actions/action/GoToPose",
                    "goal": goal,
                    "timeout": 10.0,
                })
                print("Action Result:\n", json.dumps(action_result, indent=2))

                b = input("Send another action or break with 'b'\t")
                if b == "b" or b == "break":
                    break

            # Load and visualize behavior tree
            input("Ready to visualize BT ...")
            tree = load_tree("Draw Square")
            visualized = await call_tool(session, "visualize_behavior_tree", {
                "tree_definition": tree,
                "tree_name": "cli_draw_square"
            })
            tree_id = visualized["tree_id"]
            print("\nVisualization:\n", visualized["visualization"])

            # Execute behavior tree
            input("Ready to execute BT ...")
            result = await call_tool(session, "execute_behavior_tree", {"tree_id": tree_id})
            print("\nExecution Result:\n", json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
