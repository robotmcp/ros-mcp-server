# Repository Restructuring Plan

> **Note**: For detailed implementation steps, see [restructuring_plan.md](restructuring_plan.md)

## Goal

Integrate **ros-mcp-server** (open source) into **simple-mcp-ai** (proprietary) using git submodule approach.

- ros-mcp-server: Apache 2.0 licensed, ROS MCP tools
- simple-mcp-ai: Proprietary, OAuth + Cloudflare tunnel infrastructure

## Approach: Refactor-to-Library + Submodule

### Phase 1: Refactor ros-mcp-server

Make ros-mcp-server importable as a library:

#### Option A: Single tools.py (Simpler)

```
ros-mcp-server/
├── ros_mcp/                    # NEW package
│   ├── __init__.py
│   ├── tools.py                # All @mcp.tool() definitions
│   ├── server.py               # MCP instance + main()
│   └── websocket.py            # From utils/websocket_manager.py
├── server.py                   # Entry point: from ros_mcp.server import main
└── pyproject.toml              # packages = ["ros_mcp", "ros_mcp.utils"]
```

**Pros**: Simpler structure, single file to manage  
**Cons**: Large file (~1500-2000 lines with 37 tools)

#### Option B: Split by Feature (Recommended)

```
ros-mcp-server/
├── ros_mcp/                    # NEW package
│   ├── __init__.py
│   ├── tools.py                # Main registration function (public API)
│   ├── server.py               # MCP instance + main()
│   ├── websocket.py            # From utils/websocket_manager.py
│   └── tools/                   # Tool implementations by category
│       ├── __init__.py
│       ├── connection.py       # connect_to_robot, ping_robot
│       ├── robot_config.py     # get_verified_robot_spec, get_verified_robots_list
│       ├── topics.py           # All topic tools (8 tools)
│       ├── services.py         # All service tools (6 tools)
│       ├── nodes.py            # All node tools (3 tools)
│       ├── parameters.py       # All parameter tools (7 tools)
│       ├── actions.py          # All action tools (6 tools)
│       ├── images.py           # analyze_previously_received_image
│       └── utils.py            # Helper functions
├── server.py                   # Entry point: from ros_mcp.server import main
└── pyproject.toml              # packages = ["ros_mcp", "ros_mcp.tools", "ros_mcp.utils"]
```

**Pros**: 
- Better organization (37 tools split across 8-9 focused files)
- Easier to maintain and find tools by category
- Scales better as tools are added
- Clear structure for library users

**Cons**: 
- More files to manage
- Slightly more complex imports

**Public API stays simple**: `tools.py` imports and registers all tools:
```python
# ros_mcp/tools.py
from ros_mcp.tools.connection import register_connection_tools
from ros_mcp.tools.topics import register_topic_tools
# ... etc

def register_ros_tools(mcp, rosbridge_ip, rosbridge_port):
    ws_manager = WebSocketManager(...)
    register_connection_tools(mcp, ws_manager, ...)
    register_topic_tools(mcp, ws_manager, ...)
    # ... etc
```

**Key**: Create `register_ros_tools(mcp, rosbridge_ip, rosbridge_port)` function that registers all tools.

### Phase 2: Integrate into simple-mcp-ai

1. Add submodule:
   ```bash
   git submodule add https://github.com/robotmcp/ros-mcp-server.git
   ```

2. Create `ros_integration.py`:
   ```python
   import sys, os
   sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ros-mcp-server'))
   from ros_mcp.tools import register_ros_tools
   ```

3. Update `main.py`:
   ```python
   from fastmcp import FastMCP
   from ros_integration import register_ros_tools

   mcp = FastMCP("simple-mcp-ai")
   register_ros_tools(mcp, rosbridge_ip, rosbridge_port)
   # ... OAuth middleware + FastAPI
   ```

4. Delete `tools.py` (no longer needed)

5. Update `requirements.txt` with ros-mcp dependencies

### Benefits

- ✅ Clean licensing separation (submodule stays Apache 2.0)
- ✅ Easy updates: `git submodule update --remote`
- ✅ Single MCP instance with all tools
- ✅ ros-mcp-server works standalone
