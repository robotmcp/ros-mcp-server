---
name: Move All Tools to tools.py
overview: "Move all 37 remaining tools from server.py to ros_mcp/tools.py following the established pattern: create implementation functions and register them in register_ros_tools()."
todos: []
---

# Move All Tools from server.py to ros_mcp/tools.py

## Current State

- **Total tools in server.py**: 39
- **Already moved**: 2 (connect_to_robot, ping_robot)
- **Remaining to move**: 37 tools

## Pattern to Follow

For each tool:

1. Create `tool_name_impl()` function in [`ros_mcp/tools.py`](ros_mcp/tools.py) with pure implementation
2. Register in `register_ros_tools()` using `@mcp.tool` decorator
3. Remove `@mcp.tool` decorated function from [`server.py`](server.py)
4. Update imports in `tools.py` as needed

## Tool Categories and Dependencies

### Helper Functions to Move/Import

- `convert_expects_image_hint()` - move to tools.py as utility function
- `_encode_image_to_imagecontent()` - move to tools.py as utility function
- `parse_input` - already available from `ros_mcp.websocket`

### Required Imports for tools.py

- `asyncio` - for async tools (send_action_goal)
- `io`, `PIL.Image`, `fastmcp.utilities.types.Image` - for image tools
- `time`, `uuid` - for subscription/publishing tools
- `ros_mcp.utils.config_utils` - for robot spec tools
- `ros_mcp.websocket` - for WebSocketManager and parse_input

## Tool Migration Order (by category)

### 1. Robot Configuration Tools (2 tools)

- `get_verified_robot_spec` - uses config_utils
- `get_verified_robots_list` - uses config_utils

### 2. ROS Version Detection (1 tool)

- `detect_ros_version` - uses ws_manager

### 3. Topic Tools (8 tools)

- `get_topics` - uses ws_manager
- `get_topic_type` - uses ws_manager
- `get_message_details` - uses ws_manager
- `get_topic_publishers` - uses ws_manager
- `get_topic_subscribers` - uses ws_manager
- `inspect_all_topics` - uses ws_manager, calls other topic tools
- `subscribe_once` - uses ws_manager, parse_input, convert_expects_image_hint, time
- `publish_once` - uses ws_manager

### 4. Subscription/Publishing Tools (2 tools)

- `subscribe_for_duration` - uses ws_manager, parse_input, convert_expects_image_hint, time
- `publish_for_durations` - uses ws_manager, time

### 5. Service Tools (6 tools)

- `get_services` - uses ws_manager
- `get_service_type` - uses ws_manager
- `get_service_details` - uses ws_manager
- `get_service_providers` - uses ws_manager
- `inspect_all_services` - uses ws_manager, calls other service tools
- `call_service` - uses ws_manager

### 6. Node Tools (2 tools)

- `get_nodes` - uses ws_manager
- `get_node_details` - uses ws_manager
- `inspect_all_nodes` - uses ws_manager, calls other node tools

### 7. Parameter Tools (7 tools)

- `get_parameter` - uses ws_manager
- `set_parameter` - uses ws_manager
- `has_parameter` - uses ws_manager
- `delete_parameter` - uses ws_manager
- `get_parameters` - uses ws_manager
- `inspect_all_parameters` - uses ws_manager, calls other parameter tools
- `get_parameter_details` - uses ws_manager

### 8. Action Tools (6 tools)

- `get_actions` - uses ws_manager
- `get_action_type` - uses ws_manager
- `get_action_details` - uses ws_manager
- `get_action_status` - uses ws_manager
- `inspect_all_actions` - uses ws_manager, calls other action tools
- `send_action_goal` - uses ws_manager, asyncio (async function)
- `cancel_action_goal` - uses ws_manager

### 9. Image Analysis Tools (1 tool)

- `analyze_previously_received_image` - uses PIL.Image, _encode_image_to_imagecontent

## Implementation Steps

### Phase 1: Setup Helper Functions

1. Move `convert_expects_image_hint()` to `tools.py` as a module-level utility
2. Move `_encode_image_to_imagecontent()` to `tools.py` as a module-level utility
3. Add all required imports to `tools.py`:

   - `asyncio`, `io`, `time`, `uuid`
   - `PIL.Image`, `fastmcp.utilities.types.Image`
   - `ros_mcp.utils.config_utils`
   - `ros_mcp.websocket.parse_input`

### Phase 2: Move Tools by Category

For each tool category above:

1. Extract tool function from `server.py`
2. Create `tool_name_impl()` in `tools.py` with:

   - `ws_manager: WebSocketManager` as first parameter (if needed)
   - All original parameters
   - Original implementation logic

3. Register in `register_ros_tools()`:
   ```python
   @mcp.tool(description="...")
   def tool_name(...) -> dict:
       return tool_name_impl(ws_manager, ...)
   ```

4. Remove tool from `server.py`

### Phase 3: Special Cases

- **Async tools**: `send_action_goal` - keep as async in implementation and registration
- **Tools with default values**: Preserve default parameter values, especially those referencing `ws_manager.default_timeout`
- **Inspect tools**: These call other tools - ensure all dependent tools are moved first

### Phase 4: Cleanup

1. Remove unused imports from `server.py`
2. Remove helper functions from `server.py` if no longer used
3. Verify all tools work by checking imports and function signatures

## Files to Modify

1. **[ros_mcp/tools.py](ros_mcp/tools.py)**

   - Add helper functions
   - Add all implementation functions
   - Update `register_ros_tools()` to register all tools

2. **[server.py](server.py)**

   - Remove all `@mcp.tool` decorated functions (37 tools)
   - Remove helper functions if moved
   - Keep only: imports, mcp/ws_manager initialization, main() function

## Verification

After migration:

- All 39 tools should be in `register_ros_tools()` in `tools.py`
- `server.py` should have no `@mcp.tool` decorators
- All imports should be correct
- Function signatures should match original