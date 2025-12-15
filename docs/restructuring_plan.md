# Repository Restructuring & Tool Migration Plan

## Goal

Refactor **ros-mcp-server** to be importable as a library, enabling integration into **simple-mcp-ai** (proprietary) using a git submodule approach.

- **ros-mcp-server**: Apache 2.0 licensed, ROS MCP tools
- **simple-mcp-ai**: Proprietary, OAuth + Cloudflare tunnel infrastructure

## Overview

### Current State
- **Total tools in server.py**: 39
- **Already moved**: 2 (connect_to_robot, ping_robot)
- **Remaining to move**: 37 tools
- **Structure**: All tools in monolithic `server.py` (3082 lines)

### Target Structure (Recommended: Split by Feature)

```
ros-mcp-server/
├── ros_mcp/                    # Package
│   ├── __init__.py
│   ├── tools.py                # Main registration function (public API)
│   ├── server.py               # MCP instance + main()
│   ├── websocket.py            # From utils/websocket_manager.py
│   └── tools/                   # Tool implementations by category
│       ├── __init__.py
│       ├── connection.py       # connect_to_robot, ping_robot (2 tools)
│       ├── robot_config.py     # get_verified_robot_spec, get_verified_robots_list (2 tools)
│       ├── topics.py           # All topic tools (8 tools)
│       ├── services.py         # All service tools (6 tools)
│       ├── nodes.py            # All node tools (3 tools)
│       ├── parameters.py       # All parameter tools (7 tools)
│       ├── actions.py          # All action tools (6 tools)
│       ├── images.py           # analyze_previously_received_image (1 tool)
│       └── utils.py            # Helper functions
├── server.py                   # Entry point: from ros_mcp.server import main
└── pyproject.toml              # packages = ["ros_mcp", "ros_mcp.tools", "ros_mcp.utils"]
```

**Benefits of Split Structure:**
- ✅ Better organization (37 tools split across 8-9 focused files)
- ✅ Easier to maintain and find tools by category
- ✅ Scales better as tools are added
- ✅ Clear structure for library users
- ✅ Public API stays simple: single `register_ros_tools()` function

## Phase 1: Refactor ros-mcp-server (Tool Migration)

### Step 1.1: Create Tools Directory Structure

1. Create `ros_mcp/tools/` directory
2. Create `__init__.py` in `ros_mcp/tools/`
3. Create module files:
   - `connection.py`
   - `robot_config.py`
   - `topics.py`
   - `services.py`
   - `nodes.py`
   - `parameters.py`
   - `actions.py`
   - `images.py`
   - `utils.py`

### Step 1.2: Move Helper Functions

Move to `ros_mcp/tools/utils.py`:

- `convert_expects_image_hint()` - Convert string hint to boolean
- `_encode_image_to_imagecontent()` - Encode PIL Image to ImageContent

**Required imports for utils.py:**
```python
import io
from fastmcp.utilities.types import Image
from PIL import Image as PILImage
```

### Step 1.3: Move Tools by Category

For each category, follow this pattern:

1. **Extract implementation**: Create `tool_name_impl()` function in appropriate module
2. **Create registration function**: Each module exports `register_<category>_tools(mcp, ws_manager, ...)`
3. **Update main registration**: Import and call in `ros_mcp/tools.py`
4. **Remove from server.py**: Delete `@mcp.tool` decorated function

#### Category 1: Connection Tools (Already Done)
- ✅ `connect_to_robot` - Move to `tools/connection.py`
- ✅ `ping_robot` - Move to `tools/connection.py`

#### Category 2: Robot Configuration Tools (2 tools)
**File**: `tools/robot_config.py`

- `get_verified_robot_spec` - uses `ros_mcp.utils.config_utils`
- `get_verified_robots_list` - uses `ros_mcp.utils.config_utils`

**Dependencies**: `ros_mcp.utils.config_utils`

#### Category 3: ROS Version Detection (1 tool)
**File**: `tools/robot_config.py` (or create `detection.py`)

- `detect_ros_version` - uses ws_manager

**Dependencies**: `WebSocketManager`

#### Category 4: Topic Tools (8 tools)
**File**: `tools/topics.py`

- `get_topics` - uses ws_manager
- `get_topic_type` - uses ws_manager
- `get_message_details` - uses ws_manager
- `get_topic_publishers` - uses ws_manager
- `get_topic_subscribers` - uses ws_manager
- `inspect_all_topics` - uses ws_manager, calls other topic tools
- `subscribe_once` - uses ws_manager, parse_input, convert_expects_image_hint, time
- `publish_once` - uses ws_manager

**Dependencies**: 
- `WebSocketManager`
- `ros_mcp.websocket.parse_input`
- `ros_mcp.tools.utils.convert_expects_image_hint`
- `time`, `uuid`

#### Category 5: Subscription/Publishing Tools (2 tools)
**File**: `tools/topics.py` (extend existing)

- `subscribe_for_duration` - uses ws_manager, parse_input, convert_expects_image_hint, time
- `publish_for_durations` - uses ws_manager, time

**Dependencies**: Same as Category 4

#### Category 6: Service Tools (6 tools)
**File**: `tools/services.py`

- `get_services` - uses ws_manager
- `get_service_type` - uses ws_manager
- `get_service_details` - uses ws_manager
- `get_service_providers` - uses ws_manager
- `inspect_all_services` - uses ws_manager, calls other service tools
- `call_service` - uses ws_manager

**Dependencies**: `WebSocketManager`

#### Category 7: Node Tools (3 tools)
**File**: `tools/nodes.py`

- `get_nodes` - uses ws_manager
- `get_node_details` - uses ws_manager
- `inspect_all_nodes` - uses ws_manager, calls other node tools

**Dependencies**: `WebSocketManager`

#### Category 8: Parameter Tools (7 tools)
**File**: `tools/parameters.py`

- `get_parameter` - uses ws_manager
- `set_parameter` - uses ws_manager
- `has_parameter` - uses ws_manager
- `delete_parameter` - uses ws_manager
- `get_parameters` - uses ws_manager
- `inspect_all_parameters` - uses ws_manager, calls other parameter tools
- `get_parameter_details` - uses ws_manager

**Dependencies**: `WebSocketManager`

#### Category 9: Action Tools (6 tools)
**File**: `tools/actions.py`

- `get_actions` - uses ws_manager
- `get_action_type` - uses ws_manager
- `get_action_details` - uses ws_manager
- `get_action_status` - uses ws_manager
- `inspect_all_actions` - uses ws_manager, calls other action tools
- `send_action_goal` - uses ws_manager, asyncio (async function)
- `cancel_action_goal` - uses ws_manager

**Dependencies**: 
- `WebSocketManager`
- `asyncio` (for send_action_goal)

#### Category 10: Image Analysis Tools (1 tool)
**File**: `tools/images.py`

- `analyze_previously_received_image` - uses PIL.Image, _encode_image_to_imagecontent

**Dependencies**:
- `PIL.Image`
- `ros_mcp.tools.utils._encode_image_to_imagecontent`

### Step 1.4: Update Main Registration Function

**File**: `ros_mcp/tools.py`

```python
"""ROS MCP Tools - Main registration function."""

from fastmcp import FastMCP
from ros_mcp.websocket import WebSocketManager

from ros_mcp.tools.connection import register_connection_tools
from ros_mcp.tools.robot_config import register_robot_config_tools
from ros_mcp.tools.topics import register_topic_tools
from ros_mcp.tools.services import register_service_tools
from ros_mcp.tools.nodes import register_node_tools
from ros_mcp.tools.parameters import register_parameter_tools
from ros_mcp.tools.actions import register_action_tools
from ros_mcp.tools.images import register_image_tools


def register_ros_tools(
    mcp: FastMCP,
    rosbridge_ip: str = "127.0.0.1",
    rosbridge_port: int = 9090,
) -> None:
    """Register all ROS MCP tools with the provided FastMCP instance.
    
    This function creates a WebSocketManager internally and registers all available tools.
    
    Args:
        mcp: FastMCP instance to register tools with
        rosbridge_ip: IP address of the rosbridge server (default: "127.0.0.1")
        rosbridge_port: Port of the rosbridge server (default: 9090)
    """
    # Create WebSocket manager for this instance
    ws_manager = WebSocketManager(rosbridge_ip, rosbridge_port, default_timeout=5.0)
    
    default_ip = rosbridge_ip
    default_port = rosbridge_port
    
    # Register all tool categories
    register_connection_tools(mcp, ws_manager, default_ip, default_port)
    register_robot_config_tools(mcp, ws_manager)
    register_topic_tools(mcp, ws_manager)
    register_service_tools(mcp, ws_manager)
    register_node_tools(mcp, ws_manager)
    register_parameter_tools(mcp, ws_manager)
    register_action_tools(mcp, ws_manager)
    register_image_tools(mcp, ws_manager)
```

### Step 1.5: Module Registration Pattern

Each module file should follow this pattern:

```python
"""Topic tools for ROS MCP."""

from fastmcp import FastMCP
from ros_mcp.websocket import WebSocketManager

# Import implementations
from ros_mcp.tools.topics import (
    get_topics_impl,
    get_topic_type_impl,
    # ... etc
)

def register_topic_tools(
    mcp: FastMCP,
    ws_manager: WebSocketManager,
) -> None:
    """Register all topic-related tools."""
    
    @mcp.tool(description="Fetch available topics from the ROS bridge.")
    def get_topics() -> dict:
        """Get list of all available ROS topics."""
        return get_topics_impl(ws_manager)
    
    @mcp.tool(description="Get the message type for a specific topic.")
    def get_topic_type(topic: str) -> dict:
        """Get message type for a topic."""
        return get_topic_type_impl(ws_manager, topic)
    
    # ... register all topic tools
```

### Step 1.6: Special Cases

1. **Async tools**: `send_action_goal` - keep as async in implementation and registration
   ```python
   @mcp.tool(description="...")
   async def send_action_goal(...) -> dict:
       return await send_action_goal_impl(ws_manager, ...)
   ```

2. **Tools with default values**: Preserve default parameter values, especially those referencing `ws_manager.default_timeout`

3. **Inspect tools**: These call other tools - ensure all dependent tools are moved first
   - `inspect_all_topics` - calls other topic tools
   - `inspect_all_services` - calls other service tools
   - `inspect_all_nodes` - calls other node tools
   - `inspect_all_parameters` - calls other parameter tools
   - `inspect_all_actions` - calls other action tools

4. **Image tools**: Use helper functions from `tools/utils.py`

### Step 1.7: Cleanup server.py

After all tools are moved:

1. Remove all `@mcp.tool` decorated functions (37 tools)
2. Remove helper functions (`convert_expects_image_hint`, `_encode_image_to_imagecontent`)
3. Remove unused imports
4. Keep only:
   - Imports for main() function
   - MCP/ws_manager initialization (if needed for backward compatibility)
   - `main()` function that uses `ros_mcp.server.main`

### Step 1.8: Update Imports

Update `server.py` entry point:
```python
from ros_mcp.server import main

if __name__ == "__main__":
    main()
```

## Phase 2: Integrate into simple_mcp_server

### Step 2.1: Add Submodule

```bash
cd simple_mcp_server
git submodule add https://github.com/robotmcp/ros-mcp-server.git
```

### Step 2.2: Create Integration Module

**File**: `simple_mcp_server/ros_integration.py`

```python
"""Integration module for ros-mcp-server submodule."""

import sys
import os

# Add ros-mcp-server to path
submodule_path = os.path.join(os.path.dirname(__file__), 'ros-mcp-server')
sys.path.insert(0, submodule_path)

from ros_mcp.tools import register_ros_tools
```

### Step 2.3: Update Main Application

**File**: `simple_mcp_server/main.py`

```python
from fastmcp import FastMCP
from ros_integration import register_ros_tools

# Create MCP instance
mcp = FastMCP("simple-mcp-server")

# Register ROS tools
register_ros_tools(mcp, rosbridge_ip="127.0.0.1", rosbridge_port=9090)

# ... OAuth middleware + FastAPI setup
```

### Step 2.4: Update Dependencies

**File**: `simple_mcp_server/requirements.txt`

Add ros-mcp dependencies:
```
fastmcp>=2.11.3
pillow>=11.3.0
websocket-client>=1.8.0
# ... other ros-mcp dependencies
```

### Step 2.5: Remove Old Tools

Delete `simple_mcp_server/tools.py` (no longer needed)

## Verification Checklist

### After Phase 1 (Tool Migration)

- [ ] All 39 tools registered in `register_ros_tools()`
- [ ] `server.py` has no `@mcp.tool` decorators
- [ ] All imports are correct
- [ ] Function signatures match original
- [ ] Helper functions moved to `tools/utils.py`
- [ ] Each category has its own module file
- [ ] All tools tested and working
- [ ] `ros-mcp-server` works standalone

### After Phase 2 (Integration)

- [ ] Submodule added successfully
- [ ] `ros_integration.py` created
- [ ] `main.py` updated to use `register_ros_tools()`
- [ ] Dependencies updated
- [ ] Old `tools.py` removed
- [ ] Integration tested end-to-end

## Benefits

- ✅ Clean licensing separation (submodule stays Apache 2.0)
- ✅ Easy updates: `git submodule update --remote`
- ✅ Single MCP instance with all tools
- ✅ ros-mcp-server works standalone
- ✅ Well-organized, maintainable code structure
- ✅ Clear separation of concerns
- ✅ Easy to extend with new tools

## Migration Order Summary

1. **Setup**: Create tools directory structure
2. **Helpers**: Move utility functions to `tools/utils.py`
3. **Connection**: Already done (connect_to_robot, ping_robot)
4. **Robot Config**: get_verified_robot_spec, get_verified_robots_list, detect_ros_version
5. **Topics**: All topic tools (8 tools)
6. **Services**: All service tools (6 tools)
7. **Nodes**: All node tools (3 tools)
8. **Parameters**: All parameter tools (7 tools)
9. **Actions**: All action tools (6 tools)
10. **Images**: analyze_previously_received_image
11. **Cleanup**: Remove from server.py, update imports
12. **Integration**: Add submodule, create integration, update main
