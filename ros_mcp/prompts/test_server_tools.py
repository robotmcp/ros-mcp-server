"""Test server tools prompts for ROS1 MCP Server."""


def register_test_server_tools_prompts(mcp):
    """Register test server tools prompts with the MCP server."""

    @mcp.prompt(name="test-server-tools")
    def test_server_tools() -> str:
        """Guide users on how to test and explore ROS1 MCP server tools."""
        return """# Testing ROS1 MCP Server - Quick Start Guide

## Prerequisites

Before testing, ensure you have:
1. **Turtlesim running**: `rosrun turtlesim turtlesim_node`
2. **Rosbridge running**: `rosrun rosbridge_server rosbridge_websocket`

## Quick Test Workflow

### 1. Connect and Discover

```python
connect_to_robot(ip='127.0.0.1', port=9090)
detect_ros_version()

get_topics()
get_services()
get_nodes()
get_parameters()
```

### 2. Test Main Tools by Category

**Topics**
```python
subscribe_once(topic='/turtle1/pose', msg_type='turtlesim/Pose')
publish_once(topic='/turtle1/cmd_vel', msg_type='geometry_msgs/Twist',
             msg={'linear': {'x': 2.0, 'y': 0.0, 'z': 0.0}})
```

**Services**
```python
call_service(service_name='/turtle1/teleport_absolute',
             service_type='turtlesim/TeleportAbsolute',
             request={'x': 5.5, 'y': 5.5, 'theta': 0.0})
```

**Nodes**
```python
get_node_details('/turtlesim')
```

**Parameters**
```python
get_parameter('/turtlesim/background_r')
set_parameter('/turtlesim/background_r', '255')
```

**Debug (C++/process)**
```python
resolve_node_pid('/turtlesim')
gdb_thread_bt(pid=12345)
gdb_frame_locals(pid=12345, thread_id=0, frame_id=0)  # auto thread pick
py_stack_snapshot(pid=12345)
core_list_recent(limit=5)
repro_bundle_collect(node_name='/turtlesim')
classify_cpp_crash(signal_name='SIGSEGV', top_frame='#0 ...')
```

**Timing / rosbridge diagnostics**
```python
tf_time_snapshot()
topic_age_probe('/turtle1/pose', msg_type='turtlesim/Pose', window_sec=8)
rosbridge_lag_probe('/turtle1/pose', msg_type='turtlesim/Pose', seconds=12)
```

## Useful Resources

- `ros-mcp://ros-metadata/all`
- `ros-mcp://ros-metadata/topics/all`
- `ros-mcp://ros-metadata/services/all`
- `ros-mcp://ros-metadata/nodes/all`
- `ros-mcp://ros-metadata/parameters/all`

## Troubleshooting

If tools fail, verify:
- `roscore` is running
- `rosbridge_server` and `rosapi` are installed and active
- topic/service names match your ROS graph
"""
