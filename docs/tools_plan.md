# Tool Migration Quick Reference

> **Note**: This is a quick reference. For the complete restructuring plan including integration steps, see [restructuring_plan.md](restructuring_plan.md).

## Current Status

- **Total tools**: 39
- **Moved**: 2 (connect_to_robot, ping_robot)
- **Remaining**: 37 tools

## Migration Pattern

For each tool:

1. Create `tool_name_impl()` in appropriate module file
2. Register in `register_<category>_tools()` function
3. Remove from `server.py`

## Tool Categories & Files

| Category | File | Count | Tools |
|----------|------|-------|-------|
| Connection | `tools/connection.py` | 2 | connect_to_robot, ping_robot ✅ |
| Robot Config | `tools/robot_config.py` | 3 | get_verified_robot_spec, get_verified_robots_list, detect_ros_version |
| Topics | `tools/topics.py` | 10 | get_topics, get_topic_type, get_message_details, get_topic_publishers, get_topic_subscribers, inspect_all_topics, subscribe_once, publish_once, subscribe_for_duration, publish_for_durations |
| Services | `tools/services.py` | 6 | get_services, get_service_type, get_service_details, get_service_providers, inspect_all_services, call_service |
| Nodes | `tools/nodes.py` | 3 | get_nodes, get_node_details, inspect_all_nodes |
| Parameters | `tools/parameters.py` | 7 | get_parameter, set_parameter, has_parameter, delete_parameter, get_parameters, inspect_all_parameters, get_parameter_details |
| Actions | `tools/actions.py` | 6 | get_actions, get_action_type, get_action_details, get_action_status, inspect_all_actions, send_action_goal, cancel_action_goal |
| Images | `tools/images.py` | 1 | analyze_previously_received_image |
| Utils | `tools/utils.py` | - | convert_expects_image_hint, _encode_image_to_imagecontent |

## Quick Migration Checklist

- [ ] Create `ros_mcp/tools/` directory structure
- [ ] Move helper functions to `tools/utils.py`
- [ ] Move connection tools (already done)
- [ ] Move robot config tools
- [ ] Move topic tools
- [ ] Move service tools
- [ ] Move node tools
- [ ] Move parameter tools
- [ ] Move action tools
- [ ] Move image tools
- [ ] Update `ros_mcp/tools.py` registration function
- [ ] Clean up `server.py`
- [ ] Test all tools

See [restructuring_plan.md](restructuring_plan.md) for detailed steps and code examples.
