"""Conftest for unit tests.

Stubs out modules that may not be available in the test environment
to allow importing individual tool modules without triggering
the full ros_mcp package initialization.
"""

import sys
import types

# Stub ros_mcp.utils.response if missing (may not exist on all branches)
if "ros_mcp.utils.response" not in sys.modules:
    stub = types.ModuleType("ros_mcp.utils.response")
    stub._extract_error = lambda resp: "stub"
    stub._safe_get_values = lambda resp: None
    stub._check_response = lambda resp: None
    sys.modules["ros_mcp.utils.response"] = stub
