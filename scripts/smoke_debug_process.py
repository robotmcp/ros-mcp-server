#!/usr/bin/env python3
"""Practical smoke test for ros_mcp/tools/debug_process.py.

Runs against a temporary local Python process and validates that debug tools:
- register correctly
- execute without crashing
- return structured output even when optional system deps are missing
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import types
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEBUG_PROCESS_PATH = REPO_ROOT / "ros_mcp" / "tools" / "debug_process.py"


def ensure_shims() -> None:
    """Provide tiny module shims so debug_process can be imported standalone."""
    if "fastmcp" not in sys.modules:
        fastmcp_mod = types.ModuleType("fastmcp")

        class FastMCP:  # pragma: no cover - shim only
            pass

        fastmcp_mod.FastMCP = FastMCP
        sys.modules["fastmcp"] = fastmcp_mod

    if "mcp.types" not in sys.modules:
        mcp_mod = types.ModuleType("mcp")
        types_mod = types.ModuleType("mcp.types")

        class ToolAnnotations:  # pragma: no cover - shim only
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        types_mod.ToolAnnotations = ToolAnnotations
        sys.modules["mcp"] = mcp_mod
        sys.modules["mcp.types"] = types_mod


def load_module(path: Path):
    """Load debug_process.py as a standalone module."""
    ensure_shims()
    spec = importlib.util.spec_from_file_location("debug_process_smoke", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["debug_process_smoke"] = module
    spec.loader.exec_module(module)
    return module


class DummyMCP:
    """Capture decorated tools into a dict."""

    def __init__(self):
        self.tools: dict[str, Any] = {}

    def tool(self, **kwargs):  # noqa: ARG002
        def deco(fn):
            self.tools[fn.__name__] = fn
            return fn

        return deco


def spawn_target() -> subprocess.Popen:
    """Spawn a synthetic multi-thread Python target process."""
    code = textwrap.dedent(
        """
        import threading
        import time

        def worker():
            x = 0
            while True:
                x += 1
                if x % 500000 == 0:
                    time.sleep(0.02)

        for _ in range(3):
            t = threading.Thread(target=worker, daemon=True)
            t.start()

        while True:
            time.sleep(1)
        """
    )
    return subprocess.Popen([sys.executable, "-c", code])


def main() -> int:
    module = load_module(DEBUG_PROCESS_PATH)
    mcp = DummyMCP()
    module.register_debug_process_tools(mcp)

    target = spawn_target()
    pid = target.pid

    results: dict[str, Any] = {}

    try:
        results["rr_status"] = mcp.tools["rr_status"]()
        results["resolve_node_pid"] = mcp.tools["resolve_node_pid"](str(pid))
        results["gdb_thread_bt"] = mcp.tools["gdb_thread_bt"](pid=pid, depth=10)
        results["gdb_frame_locals_auto"] = mcp.tools["gdb_frame_locals"](
            pid=pid, thread_id=0, frame_id=0
        )
        results["py_stack_snapshot"] = mcp.tools["py_stack_snapshot"](pid=pid)

        with tempfile.TemporaryDirectory(prefix="ros_mcp_smoke_bundle_") as td:
            results["repro_bundle_collect"] = mcp.tools["repro_bundle_collect"](
                pid=pid,
                out_dir=td,
                include_ros_graph=False,
                include_topic_sample=False,
            )

        print(json.dumps(results, indent=2, ensure_ascii=False))

        # Minimal pass criteria: core tools return dicts and repro bundle succeeds.
        if not isinstance(results.get("resolve_node_pid"), dict):
            return 2
        if not results.get("repro_bundle_collect", {}).get("success"):
            return 3
        return 0
    finally:
        if target.poll() is None:
            target.terminate()
            try:
                target.wait(timeout=2)
            except Exception:
                target.kill()


if __name__ == "__main__":
    raise SystemExit(main())
