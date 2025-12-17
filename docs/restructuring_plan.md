# Repository Restructuring & Tool Migration Plan

> **Note**: This plan is based on the original approach from [merge_plan_mok.md](merge_plan_mok.md), with detailed implementation steps specific to this repository.

## Related Documents

- **[merge_plan_mok.md](merge_plan_mok.md)**: Original high-level plan from mok (refactor-to-library + submodule approach)

## Summary: Implementation vs Original Plan

**Status**: ✅ **Phase 1 Complete** - All 31 tools migrated to modular structure

**Key Differences from Original Plan:**
- ✅ Used `tools/__init__.py` instead of `tools.py` (better Python package convention)
- ✅ Used `main.py` instead of `server.py` (entry point naming)
- ⚠️ Function signature: `register_all_tools(mcp, ws_manager, ...)` takes `ws_manager` as parameter (more flexible than creating it internally)
- ✅ WebSocket manager renamed to `utils/websocket.py` (matches original plan structure)
- ✅ Helper functions in `tools/images.py` (co-located with usage, not separate `utils.py`)

**Public API**: `from ros_mcp.tools import register_all_tools` - imports from `ros_mcp/tools/__init__.py`

## Goal

Refactor **ros-mcp-server** to be importable as a library, enabling integration into **simple-mcp-ai** (proprietary) using a git submodule approach.

- **ros-mcp-server**: Apache 2.0 licensed, ROS MCP tools
- **simple-mcp-ai**: Proprietary, OAuth + Cloudflare tunnel infrastructure

## Overview

### Current State
- **Total tools**: 31
- **Status**: ✅ **All tools migrated** (31/31)
- **Structure**: Modular structure with tools organized by category in `ros_mcp/tools/`

### Tool Categories Overview

| Category | File | Count | Tools | Status |
|----------|------|-------|-------|--------|
| Connection | `tools/connection.py` | 2 | connect_to_robot, ping_robot | ✅ Done |
| Robot Config | `tools/robot_config.py` | 3 | get_verified_robot_spec, get_verified_robots_list, detect_ros_version | ✅ Done |
| Topics | `tools/topics.py` | 10 | get_topics, get_topic_type, get_message_details, get_topic_publishers, get_topic_subscribers, inspect_all_topics, subscribe_once, publish_once, subscribe_for_duration, publish_for_durations | ✅ Done|
| Services | `tools/services.py` | 6 | get_services, get_service_type, get_service_details, get_service_providers, inspect_all_services, call_service | ✅ Done |
| Nodes | `tools/nodes.py` | 3 | get_nodes, get_node_details, inspect_all_nodes | ✅ Done |
| Parameters | `tools/parameters.py` | 7 | get_parameter, set_parameter, has_parameter, delete_parameter, get_parameters, inspect_all_parameters, get_parameter_details | ✅ Done |
| Actions | `tools/actions.py` | 7 | get_actions, get_action_type, get_action_details, get_action_status, inspect_all_actions, send_action_goal, cancel_action_goal | ✅ Done |
| Images | `tools/images.py` | 1 | analyze_previously_received_image | ✅ Done |
| Utils | `tools/images.py` | - | convert_expects_image_hint, _encode_image_to_imagecontent (helper functions in images.py) | ✅ Done |

### Current Structure (Implemented)

```
ros-mcp-server/
├── ros_mcp/                    # Package
│   ├── __init__.py
│   ├── main.py                 # MCP instance + main() ✅
│   ├── tools/                  # Tool implementations by category ✅
│   │   ├── __init__.py         # Main registration function (public API) ✅
│   │   ├── connection.py       # 2 tools ✅
│   │   ├── robot_config.py     # 3 tools ✅
│   │   ├── topics.py           # 10 tools ✅
│   │   ├── services.py         # 6 tools ✅
│   │   ├── nodes.py            # 3 tools ✅
│   │   ├── parameters.py      # 7 tools ✅
│   │   ├── actions.py          # 7 tools ✅
│   │   └── images.py           # 1 tool + helper functions ✅
│   └── utils/                  # Utility modules ✅
│       ├── config_utils.py
│       ├── network_utils.py
│       └── websocket.py         # WebSocket manager (renamed from websocket_manager.py)
├── server.py                   # Entry point: from ros_mcp.main import main ✅
└── pyproject.toml
```

**Public API**: `from ros_mcp.tools import register_all_tools` (imports from `ros_mcp/tools/__init__.py`)

## Phase 1: Refactor ros-mcp-server (Tool Migration) ✅ COMPLETE

### Migration Pattern

For each tool category:
1. **Extract implementation**: Create `tool_name_impl()` function in appropriate module
2. **Create registration function**: Each module exports `register_<category>_tools(mcp, ws_manager, ...)`
3. **Update main registration**: Import and call in `ros_mcp/tools/__init__.py`
4. **Remove from server.py**: Delete `@mcp.tool` decorated function

### Tool Categories (All Complete ✅)

- **Connection** (2 tools): `connect_to_robot`, `ping_robot`
- **Robot Config** (3 tools): `get_verified_robot_spec`, `get_verified_robots_list`, `detect_ros_version`
- **Topics** (10 tools): `get_topics`, `get_topic_type`, `get_message_details`, `get_topic_publishers`, `get_topic_subscribers`, `inspect_all_topics`, `subscribe_once`, `publish_once`, `subscribe_for_duration`, `publish_for_durations`
- **Services** (6 tools): `get_services`, `get_service_type`, `get_service_details`, `get_service_providers`, `inspect_all_services`, `call_service`
- **Nodes** (3 tools): `get_nodes`, `get_node_details`, `inspect_all_nodes`
- **Parameters** (7 tools): `get_parameter`, `set_parameter`, `has_parameter`, `delete_parameter`, `get_parameters`, `inspect_all_parameters`, `get_parameter_details`
- **Actions** (7 tools): `get_actions`, `get_action_type`, `get_action_details`, `get_action_status`, `inspect_all_actions`, `send_action_goal`, `cancel_action_goal`
- **Images** (1 tool): `analyze_previously_received_image` + helper functions (`convert_expects_image_hint`, `_encode_image_to_imagecontent`)

### Main Registration Function ✅

**File**: `ros_mcp/tools/__init__.py`

The public API function `register_all_tools()` registers all 31 tools:

```python
def register_all_tools(
    mcp: FastMCP,
    ws_manager: WebSocketManager,
    rosbridge_ip: str = "127.0.0.1",
    rosbridge_port: int = 9090,
) -> None:
    """Register all ROS MCP tools with the provided FastMCP instance."""
    # Registers all tool categories...
```

**Note**: Function signature differs from original plan - takes `ws_manager` as parameter (more flexible than creating it internally).

## Phase 2: Integration into simple-mcp-ai ⏳ Pending

**Note**: This phase is for the **simple-mcp-ai** repository, not ros-mcp-server.

### Integration Steps

1. **Add git submodule**:
   ```bash
   cd simple-mcp-ai
   git submodule add https://github.com/robotmcp/ros-mcp-server.git
   ```

2. **Create `ros_integration.py`**:
   ```python
   import sys, os
   sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ros-mcp-server'))
   from ros_mcp.tools import register_all_tools
   from ros_mcp.utils.websocket import WebSocketManager
   ```

3. **Update `main.py`**:
   ```python
   from fastmcp import FastMCP
   from ros_integration import register_all_tools, WebSocketManager
   
   mcp = FastMCP("simple-mcp-ai")
   ws_manager = WebSocketManager("127.0.0.1", 9090, default_timeout=5.0)
   register_all_tools(mcp, ws_manager, rosbridge_ip="127.0.0.1", rosbridge_port=9090)
   ```

4. **Update `requirements.txt`** with ros-mcp dependencies

5. **Delete old `tools.py`** (if exists)

## Migration Checklist

### Phase 1: Tool Migration ✅ COMPLETE

- [X] Create `ros_mcp/tools/` directory structure ✅
- [X] Move helper functions (in `tools/images.py`) ✅
- [X] Move all 31 tools across 8 categories ✅
- [X] Update `ros_mcp/tools/__init__.py` registration function ✅
- [X] Update `server.py` entry point ✅

## Verification Checklist

### Phase 1 (Tool Migration) ✅

- [X] All 31 tools registered in `register_all_tools()`
- [X] Each category has its own module file
- [X] Helper functions in `tools/images.py`
- [X] `ros-mcp-server` works standalone

### Phase 2 (Integration) ⏳ Pending

- [ ] Submodule added to simple-mcp-ai
- [ ] `ros_integration.py` created
- [ ] `main.py` updated to use `register_all_tools()`
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
