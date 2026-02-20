#!/usr/bin/env python3
"""Practical end-to-end debug tool run inside ROS1 Noetic environment."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEBUG_PROCESS_PATH = REPO_ROOT / "ros_mcp" / "tools" / "debug_process.py"
DUMMY_NODE_PATH = REPO_ROOT / "scripts" / "ros_dummy_node.py"


def ensure_shims() -> None:
    if "fastmcp" not in sys.modules:
        fastmcp_mod = types.ModuleType("fastmcp")

        class FastMCP:  # pragma: no cover
            pass

        fastmcp_mod.FastMCP = FastMCP
        sys.modules["fastmcp"] = fastmcp_mod

    if "mcp.types" not in sys.modules:
        mcp_mod = types.ModuleType("mcp")
        types_mod = types.ModuleType("mcp.types")

        class ToolAnnotations:  # pragma: no cover
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        types_mod.ToolAnnotations = ToolAnnotations
        sys.modules["mcp"] = mcp_mod
        sys.modules["mcp.types"] = types_mod


def load_debug_module():
    ensure_shims()
    spec = importlib.util.spec_from_file_location("debug_process_noetic", str(DEBUG_PROCESS_PATH))
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load debug_process module")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["debug_process_noetic"] = mod
    spec.loader.exec_module(mod)
    return mod


class DummyMCP:
    def __init__(self):
        self.tools = {}

    def tool(self, **kwargs):  # noqa: ARG002
        def deco(fn):
            self.tools[fn.__name__] = fn
            return fn

        return deco


def run(cmd: list[str], timeout: float = 10.0) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)


def wait_for_rosnode(name: str, timeout_sec: float = 20.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        cp = run(["rosnode", "list"], timeout=5.0)
        if cp.returncode == 0 and name in cp.stdout.splitlines():
            return True
        time.sleep(0.5)
    return False


def main() -> int:
    roscore = subprocess.Popen(["roscore"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    dummy = None
    rosbridge = None

    results = {}

    try:
        if not wait_for_rosnode("/rosout", timeout_sec=20):
            print("roscore failed to become ready", file=sys.stderr)
            return 2

        dummy = subprocess.Popen([sys.executable, str(DUMMY_NODE_PATH)])
        rosbridge = subprocess.Popen(["rosrun", "rosbridge_server", "rosbridge_websocket"])

        if not wait_for_rosnode("/dummy_debug_node", timeout_sec=20):
            print("dummy node failed to come up", file=sys.stderr)
            return 3

        mod = load_debug_module()
        mcp = DummyMCP()
        mod.register_debug_process_tools(mcp)

        resolved = mcp.tools["resolve_node_pid"]("/dummy_debug_node")
        pid = int(resolved["best"]["pid"])

        results["rr_status"] = mcp.tools["rr_status"]()
        results["resolve_node_pid"] = resolved
        results["gdb_thread_bt"] = mcp.tools["gdb_thread_bt"](pid=pid, depth=20)
        results["gdb_frame_locals_auto"] = mcp.tools["gdb_frame_locals"](pid=pid, thread_id=0, frame_id=0)
        results["py_stack_snapshot"] = mcp.tools["py_stack_snapshot"](pid=pid)
        results["repro_bundle_collect"] = mcp.tools["repro_bundle_collect"](
            node_name="/dummy_debug_node",
            out_dir="/work/debug_bundles_noetic",
            include_ros_graph=True,
            include_topic_sample=True,
            sample_topic="/debug_header",
            sample_msg_count=3,
            sample_timeout_sec=8,
        )

        out = REPO_ROOT / "practical_noetic_results.json"
        out.write_text(json.dumps(results, indent=2, ensure_ascii=False))
        print(str(out))

        if not results["repro_bundle_collect"].get("success"):
            return 4
        return 0
    finally:
        for proc in [rosbridge, dummy, roscore]:
            if proc is not None and proc.poll() is None:
                proc.terminate()
        time.sleep(0.5)
        for proc in [rosbridge, dummy, roscore]:
            if proc is not None and proc.poll() is None:
                proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
