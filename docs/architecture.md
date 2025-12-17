# ROS MCP Server Architecture

This document describes the architecture of the ROS MCP Server, including its components, organization, and design patterns.

## Overview

The ROS MCP Server is a Model Context Protocol (MCP) server that provides tools, resources, and prompts for interacting with ROS (Robot Operating System) robots via the rosbridge WebSocket interface. The server is built using FastMCP and follows a modular, category-based architecture.

## Architecture Principles

1. **Modular Design**: Tools, resources, and prompts are organized by category into separate modules
2. **Separation of Concerns**: Clear boundaries between tools, resources, prompts, and utilities
3. **Reusability**: Shared utilities and WebSocket manager for consistent ROS communication
4. **Extensibility**: Easy to add new tools, resources, or prompts by following established patterns
5. **Library-First**: Designed to be importable as a library for integration into other projects

## Directory Structure

```
ros-mcp-server/
├── ros_mcp/                    # Main package
│   ├── __init__.py            # Package initialization
│   ├── main.py                # MCP server instance and entry point
│   │
│   ├── tools/                 # Tool implementations (31 tools)
│   │   ├── __init__.py        # Main registration function (public API)
│   │   ├── actions.py         # Action tools (7 tools)
│   │   ├── connection.py      # Connection tools (2 tools)
│   │   ├── images.py          # Image analysis tools (1 tool + helpers)
│   │   ├── nodes.py           # Node tools (3 tools)
│   │   ├── parameters.py      # Parameter tools (7 tools)
│   │   ├── robot_config.py    # Robot configuration tools (3 tools)
│   │   ├── services.py        # Service tools (6 tools)
│   │   └── topics.py          # Topic tools (10 tools)
│   │
│   ├── resources/             # Resource implementations
│   │   ├── __init__.py        # Resource registration function
│   │   ├── robot_specs.py     # Robot specification resources
│   │   └── ros_metadata.py    # ROS metadata resources (5 resources)
│   │
│   ├── prompts/               # Prompt templates
│   │   ├── __init__.py        # Prompt registration function
│   │   ├── test_actions_tools.py
│   │   ├── test_connection_tools.py
│   │   ├── test_nodes_tools.py
│   │   ├── test_parameters_tools.py
│   │   ├── test_server_tools.py
│   │   ├── test_services_tools.py
│   │   └── test_topics_tools.py
│   │
│   └── utils/                 # Utility modules
│       ├── __init__.py
│       ├── config_utils.py    # Robot configuration utilities
│       ├── network_utils.py   # Network connectivity utilities
│       └── websocket.py       # WebSocket manager for ROS communication
│
├── server.py                   # Entry point script
├── robot_specifications/       # Robot specification YAML files
└── docs/                       # Documentation
```

## Core Components

### 1. Main Entry Point (`ros_mcp/main.py`)

The main entry point initializes the MCP server and registers all components:

```python
# Initialize MCP server
mcp = FastMCP("ros-mcp-server")

# Initialize WebSocket manager
ws_manager = WebSocketManager(ROSBRIDGE_IP, ROSBRIDGE_PORT, default_timeout=5.0)

# Register all components
register_all_tools(mcp, ws_manager, rosbridge_ip=ROSBRIDGE_IP, rosbridge_port=ROSBRIDGE_PORT)
register_all_resources(mcp, ws_manager)
register_all_prompts(mcp)
```

### 2. Tools (`ros_mcp/tools/`)

Tools are the primary interface for interacting with ROS systems. They are organized by category and follow a consistent pattern.

#### Tool Categories: Total 31 tools

| Category | File | Count | Description |
|----------|------|-------|-------------|
| **Connection** | `connection.py` | 2 | Robot connection and connectivity testing |
| **Robot Config** | `robot_config.py` | 3 | Robot specification and ROS version detection |
| **Topics** | `topics.py` | 8 | Topic discovery, subscription, and publishing |
| **Services** | `services.py` | 4 | Service discovery and calling |
| **Nodes** | `nodes.py` | 2 | Node discovery and inspection |
| **Parameters** | `parameters.py` | 6 | Parameter management (ROS 2 only) |
| **Actions** | `actions.py` | 5 | Action discovery and execution (ROS 2 only) |
| **Images** | `images.py` | 1 | Image analysis and processing |


#### Tool Template

All tools follow a consistent pattern with decorator, description, and comprehensive docstring:

```python
def register_category_tools(mcp: FastMCP, ws_manager: WebSocketManager) -> None:
    """Register all category-related tools."""

    @mcp.tool(
        description=(
            "Brief description of what the tool does.\n"
            "Example:\n"
            "tool_name(param1='value1', param2=123)"
        )
    )
    def tool_name(param1: str, param2: int = 0) -> dict:
        """
        Comprehensive description of the tool's functionality.

        Args:
            param1 (str): Description of parameter 1 (e.g., 'example value')
            param2 (int): Description of parameter 2 (e.g., 123). Default is 0.

        Returns:
            dict: Contains result data with specific fields,
                or an error message if operation fails.
        """
        # Implementation logic here
        # Use ws_manager for ROS communication
        with ws_manager:
            # Tool implementation
            pass
        
        return {"result": "data"}
```

**Key Components:**

1. **Decorator** (`@mcp.tool`):
   - Contains `description` parameter with brief explanation
   - Includes usage examples when helpful
   - Description is visible to LLMs for tool selection

2. **Function Docstring**:
   - Comprehensive description of functionality
   - **Args section**: Documents all parameters with types, descriptions, and examples
   - **Returns section**: Documents return value structure and possible error cases
   - Docstring is for developer reference and IDE tooltips

3. **Implementation**:
   - Inline implementation 
   - Uses `ws_manager` context manager for ROS communication when needed
   - Returns structured dictionaries with consistent error handling

#### Public API

The main registration function in `tools/__init__.py`:

```python
def register_all_tools(
    mcp: FastMCP,
    ws_manager: WebSocketManager,
    rosbridge_ip: str = "127.0.0.1",
    rosbridge_port: int = 9090,
) -> None:
    """Register all ROS MCP tools with the provided FastMCP instance."""
    register_action_tools(mcp, ws_manager)
    register_connection_tools(mcp, ws_manager, rosbridge_ip, rosbridge_port)
    # ... other categories
```

### 3. Resources (`ros_mcp/resources/`)

Resources provide comprehensive system information in JSON format. They are accessed via URIs and return structured data.

#### Resource Types

**ROS Metadata Resources:**
- `ros-mcp://ros-metadata/all` - Complete system overview
- `ros-mcp://ros-metadata/topics/all` - All topics with details
- `ros-mcp://ros-metadata/services/all` - All services with details
- `ros-mcp://ros-metadata/nodes/all` - All nodes with details
- `ros-mcp://ros-metadata/actions/all` - All actions with details (ROS 2 only)

**Robot Specification Resources:**
- `ros-mcp://robot-specs/get_verified_robots_list` - List of available robot specifications

#### Public API

The main registration function is found in `resources/__init__.py`:

```python
def register_all_resources(
    mcp: FastMCP,
    ws_manager: WebSocketManager,
) -> None:
    """Register all resources with the MCP server instance."""
    register_robot_spec_resources(mcp)
    register_ros_metadata_resources(mcp, ws_manager)
```




### 4. Prompts (`ros_mcp/prompts/`)

Prompts are interactive guides that help users test and understand the ROS MCP Server tools.

#### Prompt Categories

- `test-server-tools` - High-level overview
- `test-connection-tools` - Connection testing
- `test-topics-tools` - Topic tools testing
- `test-services-tools` - Service tools testing
- `test-nodes-tools` - Node tools testing
- `test-parameters-tools` - Parameter tools testing (ROS 2)
- `test-actions-tools` - Action tools testing (ROS 2)


### 5. Utilities (`ros_mcp/utils/`)

Utilities provide shared functionality used across tools and resources.

#### Utility Modules

**`websocket.py` - WebSocket Manager**
- Manages WebSocket connections to rosbridge
- Provides request/response interface for ROS communication
- Handles connection lifecycle and error handling
- Thread-safe context manager for connection management

**`network_utils.py` - Network Utilities**
- `ping_ip_and_port()` - Test network connectivity
- Platform-specific ping implementation
- Port availability checking

**`config_utils.py` - Configuration Utilities**
- `load_robot_config()` - Load robot specification YAML files
- `get_verified_robot_spec_util()` - Parse and validate robot configs
- `get_verified_robots_list_util()` - List available robot specifications

## Extension Points

### Adding a New Tool

1. Create implementation function in appropriate category file
2. Create tool wrapper with `@mcp.tool` decorator
3. Register in category's `register_*_tools()` function
4. Tool is automatically available after server restart

### Adding a New Resource

1. Create resource function in `resources/ros_metadata.py` or `resources/robot_specs.py`
2. Use `@mcp.resource` decorator with URI
3. Add to `register_all_resources()` in `resources/__init__.py`
4. Resource is automatically available after server restart

### Adding a New Prompt

1. Create prompt function in `prompts/test_*.py`
2. Use `@mcp.prompt` decorator with name
3. Add to `register_all_prompts()` in `prompts/__init__.py`
4. Prompt is automatically available after server restart

## Integration

The ROS MCP Server is designed to be importable as a library:

```python
from ros_mcp.tools import register_all_tools
from ros_mcp.resources import register_all_resources
from ros_mcp.prompts import register_all_prompts
from ros_mcp.utils.websocket import WebSocketManager

# In your MCP server
mcp = FastMCP("your-server")
ws_manager = WebSocketManager("127.0.0.1", 9090)

register_all_tools(mcp, ws_manager, rosbridge_ip="127.0.0.1", rosbridge_port=9090)
register_all_resources(mcp, ws_manager)
register_all_prompts(mcp)
```

## Dependencies

### Core Dependencies
- **FastMCP**: MCP server framework
- **websocket-client**: WebSocket communication
- **opencv-python**: Image processing
- **numpy**: Numerical operations
- **PyYAML**: Robot configuration parsing

### ROS Dependencies
- **rosbridge_server**: ROS WebSocket bridge (external, must be running)

## Testing

See `docs/testing.md` for detailed testing instructions.

## Related Documentation

- **Testing Guide**: `docs/testing.md` - How to test the server
- **Restructuring Plan**: `docs/restructuring_plan.md` - Migration history
- **Launch System**: `docs/launch_system.md` - ROS launch guide
- **Installation**: `docs/installation.md` - Setup instructions

