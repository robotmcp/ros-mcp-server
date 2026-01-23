# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.5.0] - 2026-01-23

### Added
- ROS 1 (Noetic) E2E testing support alongside ROS 2 (Humble)
- New Docker configurations: `Dockerfile.ros1`, `Dockerfile.ros2`, `docker-compose.ros1.yml`
- ROS version-aware fixtures for cross-version compatibility
- New pytest markers: `ros1`, `ros2` for version-specific test filtering
- Command line option `--ros-version=1|2` for pytest
- ROS version-aware rosapi service type fixtures

### Changed
- E2E tests now support both ROS 1 and ROS 2 environments
- Updated test documentation with ROS 1/ROS 2 testing instructions
- Refactored E2E tests to use ROS version-aware message and service types
- Actions and parameters tests marked as ROS 2-only (appropriate for their APIs)

## [2.4.0] - 2026-01-23

### Added
- 6 new E2E test files covering prompts, resources, integration, error handling, and images
- New fixtures: `ws_manager_tiny_timeout`, `invalid_ws_manager`, `mcp_server`
- Tests for MCP server registration (tools, resources, prompts)
- Tests for CLI argument parsing
- Multi-tool workflow integration tests
- Error handling and edge case tests
- Image detection and parsing tests

### Fixed
- Critical: Fixed `locals()` usage for undefined `action_interfaces` variable in actions.py
- High: Fixed resource leak in `subscribe_once` and `subscribe_for_duration` (added try/finally)
- High: Fixed race condition with negative timeout in `send_action_goal`
- Medium: Fixed silent exception handling - now logs exceptions instead of bare `pass`
- Medium: Fixed float type inference error for values like "1.2.3" in parameters.py
- Medium: Fixed unchecked WebSocket state before sending messages
- Medium: Fixed misleading `__enter__` docstring in WebSocketManager
- Medium: Simplified redundant condition in `_is_empty_value`
- Low: Added exception handling in publish loop
- Low: Added timeout validation in `send_action_goal`
- Low: Fixed inconsistent bounds checking in action details parsing

### Changed
- Action support now marked as implemented (was "upcoming")
- Improved context manager usage in async action goal sending
- Updated test documentation with automated testing section

## [2.3.0] - 2026-01-23

### Added
- Comprehensive unit test suite with 239 tests achieving 62% code coverage
- Tests for all major tool modules: actions, parameters, nodes, images, robot_config
- End-to-end (E2E) tests with ROS 2 turtlesim in Docker
- GitHub Actions workflow for automated unit and E2E testing
- API reference documentation (`docs/api-reference.md`)
- pytest configuration in pyproject.toml with coverage support
- pytest-asyncio support for async test functions

### Changed
- Improved code quality with ruff linting and formatting
- Lazy imports in `ros_mcp/__init__.py` for optional dependencies

## [2.2.1] - 2026-01-15

### Added
- Integration module for parent server registration (`integration.py`)
- Support for registering ros-mcp-server as a child of a parent MCP server

### Fixed
- Packaging configuration: added missing modules and corrected entry point
- Fixed mutable defaults in `publish_once` and `publish_for_durations` functions

## [2.2.0] - 2025-12-20

### Added
- Major refactoring and modularization of the ros-mcp server
- New modular architecture with separate tool modules:
  - `ros_mcp/tools/actions.py` - ROS 2 action tools
  - `ros_mcp/tools/connection.py` - Connection and ping tools
  - `ros_mcp/tools/images.py` - Image handling tools
  - `ros_mcp/tools/nodes.py` - Node inspection tools
  - `ros_mcp/tools/parameters.py` - ROS 2 parameter tools
  - `ros_mcp/tools/robot_config.py` - Robot configuration tools
  - `ros_mcp/tools/services.py` - Service tools
  - `ros_mcp/tools/topics.py` - Topic pub/sub tools
- MCP Resources for ROS metadata and robot specifications
- MCP Prompts for guided testing workflows
- Cross-platform Docker launch system for turtlesim example
- Unitree GO2 robot specification

### Changed
- Reorganized codebase from monolithic to modular structure
- Improved WebSocket management with context manager support
- Enhanced error handling and response consistency across all tools

### Fixed
- GUI display issues on macOS with XQuartz for Docker examples
- Scripts path in turtlesim Docker example

## [2.1.7] - 2025-12-01

### Added
- Installation using uvx documentation
- TurtleBot3 example

### Fixed
- GitHub Actions for PyPI and MCP publish workflows

## [2.1.0] - 2025-11-15

### Added
- Initial public release of ros-mcp-server
- Core MCP tools for ROS interaction via rosbridge:
  - Topic discovery, subscription, and publishing
  - Service discovery and calling
  - Node inspection
  - Parameter management (ROS 2)
  - Action goals (ROS 2)
  - Image message handling
- Robot specification system for verified robot models
- Connection tools with network diagnostics
- Docker-based turtlesim example
- Comprehensive documentation

### Changed
- Migrated from prototype to production-ready implementation

---

## Version History Summary

| Version | Release Date | Key Changes |
|---------|--------------|-------------|
| 2.4.0 | 2026-01-23 | Bug fixes, new E2E tests, documentation updates |
| 2.3.0 | 2026-01-23 | Comprehensive test suite, GitHub Actions CI |
| 2.2.1 | 2026-01-15 | Parent server integration, packaging fixes |
| 2.2.0 | 2025-12-20 | Major modularization, MCP resources/prompts |
| 2.1.7 | 2025-12-01 | uvx installation, TurtleBot3 example |
| 2.1.0 | 2025-11-15 | Initial public release |

[Unreleased]: https://github.com/robotmcp/ros-mcp-server/compare/v2.4.0...HEAD
[2.4.0]: https://github.com/robotmcp/ros-mcp-server/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/robotmcp/ros-mcp-server/compare/v2.2.1...v2.3.0
[2.2.1]: https://github.com/robotmcp/ros-mcp-server/compare/v2.2.0...v2.2.1
[2.2.0]: https://github.com/robotmcp/ros-mcp-server/compare/v2.1.7...v2.2.0
[2.1.7]: https://github.com/robotmcp/ros-mcp-server/compare/v2.1.0...v2.1.7
[2.1.0]: https://github.com/robotmcp/ros-mcp-server/releases/tag/v2.1.0
