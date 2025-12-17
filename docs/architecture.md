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

#### Tool Categories

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

**Total: 31 tools**



#### Public API

The main registration function in `tools/__init__.py`:

```python
def register_ros_tools(
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

#### Resource Registration Pattern

```python
def register_ros_metadata_resources(mcp, ws_manager: WebSocketManager):
    """Register ROS metadata resources with the MCP server."""
    
    @mcp.resource("ros-mcp://ros-metadata/all")
    def get_all_ros_metadata() -> str:
        """Get all ROS metadata."""
        # Query ROS system via ws_manager
        # Return JSON string
        return json.dumps(metadata, indent=2)
```

**Key Characteristics:**
- Resources return JSON strings (not dicts)
- Use `@mcp.resource` decorator with URI
- Access ROS system via WebSocket manager
- Provide comprehensive system snapshots

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

#### Prompt Registration Pattern

```python
def register_test_category_prompts(mcp):
    """Register test prompts for a category."""
    
    @mcp.prompt(name="test-category-tools")
    def test_category_tools() -> str:
        """Return prompt content as string."""
        return """# Testing Guide
        ...
        """
```

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

## Communication Flow

### Tool Execution Flow

```
User Request
    ↓
MCP Client
    ↓
FastMCP Server (main.py)
    ↓
Tool Function (tools/*.py)
    ↓
Implementation Function (*_impl)
    ↓
WebSocket Manager (utils/websocket.py)
    ↓
Rosbridge WebSocket
    ↓
ROS System
```

### Resource Access Flow

```
User Request (Resource URI)
    ↓
MCP Client
    ↓
FastMCP Server (main.py)
    ↓
Resource Function (resources/*.py)
    ↓
WebSocket Manager (utils/websocket.py)
    ↓
Rosbridge WebSocket
    ↓
ROS System
    ↓
JSON Response
```

## WebSocket Manager

The `WebSocketManager` is the core communication component that handles all ROS interactions.

### Key Features

- **Connection Management**: Establishes and maintains WebSocket connections
- **Request/Response**: Sends ROS messages and receives responses
- **Context Manager**: Thread-safe connection handling with `with` statements
- **Error Handling**: Graceful handling of connection failures
- **Timeout Management**: Configurable timeouts for operations

### Usage Pattern

```python
with ws_manager:
    response = ws_manager.request({
        "op": "call_service",
        "service": "/rosapi/topics",
        "type": "rosapi/Topics",
        "args": {},
        "id": "request_id"
    })
```

## Design Patterns

### 1. Registration Pattern

All components (tools, resources, prompts) follow a registration pattern:

```python
def register_component(mcp: FastMCP, ...) -> None:
    """Register component with MCP server."""
    # Registration logic
```

### 2. Implementation Pattern

Tools separate implementation from registration:

```python
def tool_impl(ws_manager, ...) -> dict:
    """Pure implementation logic."""
    pass

@mcp.tool(...)
def tool(...) -> dict:
    """MCP tool wrapper."""
    return tool_impl(ws_manager, ...)
```

### 3. Category Organization

Related tools are grouped into category modules:
- Each category has its own file
- Each category has a registration function
- Categories are independent and can be extended

### 4. Resource URI Pattern

Resources use URIs following this pattern:
- `ros-mcp://ros-metadata/{category}/all` - Metadata resources
- `ros-mcp://robot-specs/{resource_name}` - Robot specification resources

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
from ros_mcp.tools import register_ros_tools
from ros_mcp.resources import register_all_resources
from ros_mcp.prompts import register_all_prompts
from ros_mcp.utils.websocket import WebSocketManager

# In your MCP server
mcp = FastMCP("your-server")
ws_manager = WebSocketManager("127.0.0.1", 9090)

register_ros_tools(mcp, ws_manager)
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
- **rosapi**: ROS API services (part of rosbridge)

## Error Handling

### Tool Error Handling

Tools return structured error responses:

```python
{
    "error": "Error message",
    "details": {...}  # Optional additional context
}
```

### Resource Error Handling

Resources include errors in JSON response:

```python
{
    "error": "Error message",
    "data": {...},  # Partial data if available
    "errors": [...]  # List of errors encountered
}
```

### WebSocket Error Handling

WebSocket manager handles:
- Connection failures
- Timeout errors
- Invalid responses
- Network issues

## Testing

The architecture supports testing through:
- **Test Prompts**: Interactive guides for testing tools
- **Resource Access**: Comprehensive system information gathering
- **Tool Isolation**: Implementation functions can be tested independently

See `docs/testing.md` for detailed testing instructions.

## Future Considerations

### Potential Enhancements
- Caching layer for frequently accessed resources
- Connection pooling for multiple ROS systems
- Async/await support for better concurrency
- Plugin system for custom tool categories
- Resource versioning for API stability

### Scalability
- Current architecture supports single ROS system connection
- WebSocket manager can be extended for multiple connections
- Resource aggregation can be optimized for large systems

## Related Documentation

- **Testing Guide**: `docs/testing.md` - How to test the server
- **Restructuring Plan**: `docs/restructuring_plan.md` - Migration history
- **Launch System**: `docs/launch_system.md` - ROS integration guide
- **Installation**: `docs/installation.md` - Setup instructions

