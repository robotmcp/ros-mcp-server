"""Debug process tools for ROS1 C++/Python node investigation."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from typing import Any

from fastmcp import FastMCP
from mcp.types import ToolAnnotations


def _run(command: list[str], timeout: float = 15.0) -> dict[str, Any]:
    """Run a shell command and return structured output."""
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "command": command,
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "returncode": 127,
            "stdout": "",
            "stderr": f"Command not found: {command[0]}",
            "command": command,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "ok": False,
            "returncode": 124,
            "stdout": e.stdout or "",
            "stderr": f"Command timed out after {timeout}s",
            "command": command,
        }


def _pid_exists(pid: int) -> bool:
    """Check if a process exists."""
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _parse_ps_candidates(ps_stdout: str, node_name: str) -> list[dict[str, Any]]:
    """Find candidate processes for a ROS node name from ps output."""
    short = node_name.split("/")[-1] if "/" in node_name else node_name
    short = short.strip()
    full = node_name.strip()

    candidates: list[dict[str, Any]] = []

    for line in ps_stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        first_space = stripped.find(" ")
        if first_space < 0:
            continue

        pid_str = stripped[:first_space].strip()
        args = stripped[first_space + 1 :].strip()
        if not pid_str.isdigit() or not args:
            continue

        pid = int(pid_str)
        score = 0
        reasons: list[str] = []

        if f"__name:={full}" in args or f"__name:={short}" in args:
            score += 100
            reasons.append("matched __name remap")

        if full and full in args:
            score += 40
            reasons.append("matched full node name in cmdline")

        if short and re.search(rf"\b{re.escape(short)}\b", args):
            score += 20
            reasons.append("matched short node token")

        if score > 0:
            try:
                argv = shlex.split(args)
                exe = argv[0] if argv else ""
            except Exception:
                exe = args.split()[0]

            candidates.append(
                {
                    "pid": pid,
                    "exe": exe,
                    "cmdline": args,
                    "match_score": score,
                    "match_reasons": reasons,
                }
            )

    candidates.sort(key=lambda c: (-c["match_score"], c["pid"]))
    return candidates


def _parse_gdb_thread_bt(output: str) -> list[dict[str, Any]]:
    """Parse `thread apply all bt` output into thread/frame blocks."""
    threads: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    header_re = re.compile(r"^Thread\s+\d+\s+\(.*\):$")
    frame_re = re.compile(r"^#\d+\s")

    for raw_line in output.splitlines():
        line = raw_line.rstrip("\n")
        if header_re.match(line.strip()):
            if current:
                threads.append(current)
            current = {"header": line.strip(), "frames": []}
            continue

        if current is None:
            continue

        stripped = line.strip()
        if frame_re.match(stripped):
            current["frames"].append(stripped)

    if current:
        threads.append(current)

    return threads


def register_debug_process_tools(mcp: FastMCP) -> None:
    """Register C++/core debugging tools."""

    @mcp.tool(
        description=(
            "Resolve likely Linux process IDs for a ROS node name by inspecting command lines.\n"
            "Example:\nresolve_node_pid('/move_base')"
        ),
        annotations=ToolAnnotations(
            title="Resolve Node PID",
            readOnlyHint=True,
        ),
    )
    def resolve_node_pid(node_name: str) -> dict:
        """Resolve candidate process IDs for a ROS node name."""
        if not node_name or not node_name.strip():
            return {"error": "node_name cannot be empty"}

        node_name = node_name.strip()

        # If the user passed a PID directly, return quickly
        if node_name.isdigit():
            pid = int(node_name)
            if _pid_exists(pid):
                cmd = _run(["ps", "-p", str(pid), "-o", "args=", "-o", "comm="])
                lines = [ln for ln in cmd.get("stdout", "").splitlines() if ln.strip()]
                cmdline = lines[0].strip() if lines else ""
                exe = lines[1].strip() if len(lines) > 1 else ""
                return {
                    "query": node_name,
                    "best": {"pid": pid, "exe": exe, "cmdline": cmdline, "match_score": 999},
                    "candidates": [
                        {"pid": pid, "exe": exe, "cmdline": cmdline, "match_score": 999}
                    ],
                }
            return {"error": f"PID {pid} does not exist"}

        ps = _run(["ps", "-eo", "pid,args", "--no-headers"])
        if not ps["ok"]:
            return {
                "error": "Failed to inspect processes",
                "details": ps.get("stderr", ""),
            }

        candidates = _parse_ps_candidates(ps["stdout"], node_name)
        if not candidates:
            return {
                "query": node_name,
                "best": None,
                "candidates": [],
                "note": "No likely process matches found. If launched via roslaunch, try a more specific node name or pass PID directly.",
            }

        return {
            "query": node_name,
            "best": candidates[0],
            "candidates": candidates,
        }

    @mcp.tool(
        description=(
            "Attach gdb to a running PID and collect all thread backtraces.\n"
            "Example:\ngdb_thread_bt(pid=12345, depth=40)"
        ),
        annotations=ToolAnnotations(
            title="GDB Thread Backtrace",
            readOnlyHint=True,
        ),
    )
    def gdb_thread_bt(pid: int, depth: int = 40) -> dict:
        """Collect all-thread backtrace for a running process via gdb."""
        try:
            pid = int(pid)
        except Exception:
            return {"error": "pid must be an integer"}

        if pid <= 0:
            return {"error": "pid must be > 0"}
        if not _pid_exists(pid):
            return {"error": f"PID {pid} not found"}

        depth = max(1, min(int(depth), 200))

        command = [
            "gdb",
            "-q",
            "-n",
            "-batch",
            "-ex",
            "set pagination off",
            "-ex",
            "set print thread-events off",
            "-ex",
            f"thread apply all bt {depth}",
            "-p",
            str(pid),
        ]

        result = _run(command, timeout=30.0)
        combined = "\n".join([result.get("stdout", ""), result.get("stderr", "")]).strip()

        if not result["ok"] and "ptrace" in combined.lower():
            return {
                "pid": pid,
                "success": False,
                "error": "gdb attach failed (ptrace restrictions).",
                "raw": combined,
            }

        threads = _parse_gdb_thread_bt(combined)
        return {
            "pid": pid,
            "success": len(threads) > 0,
            "thread_count": len(threads),
            "threads": threads,
            "raw": combined if len(threads) == 0 else "",
        }

    @mcp.tool(
        description=(
            "List recent core dumps from systemd-coredump.\n"
            "Example:\ncore_list_recent(limit=10)"
        ),
        annotations=ToolAnnotations(
            title="Core List Recent",
            readOnlyHint=True,
        ),
    )
    def core_list_recent(limit: int = 10) -> dict:
        """List recent core dumps (if coredumpctl is available)."""
        limit = max(1, min(int(limit), 100))
        result = _run(["coredumpctl", "--no-pager", "list", "--reverse", "--lines", str(limit)])

        if not result["ok"]:
            return {
                "success": False,
                "error": "Failed to query coredumpctl",
                "details": result.get("stderr", ""),
            }

        lines = [ln for ln in result.get("stdout", "").splitlines() if ln.strip()]
        entries = []
        for line in lines:
            if line.strip().startswith("TIME") or line.strip().startswith("-"):
                continue
            entries.append({"line": line.rstrip()})

        return {
            "success": True,
            "count": len(entries),
            "entries": entries,
        }

    @mcp.tool(
        description=(
            "Analyze a core dump with gdb and return signal + backtrace summary.\n"
            "Example:\ncore_analyze('/tmp/core.12345', '/path/to/executable')"
        ),
        annotations=ToolAnnotations(
            title="Core Analyze",
            readOnlyHint=True,
        ),
    )
    def core_analyze(core_path: str, exe_path: str = "", depth: int = 60) -> dict:
        """Analyze a core dump file with gdb in batch mode."""
        if not core_path or not core_path.strip():
            return {"error": "core_path cannot be empty"}

        core_path = core_path.strip()
        if not os.path.exists(core_path):
            return {"error": f"Core file not found: {core_path}"}

        depth = max(1, min(int(depth), 300))

        command = [
            "gdb",
            "-q",
            "-n",
            "-batch",
            "-ex",
            "set pagination off",
            "-ex",
            "info program",
            "-ex",
            f"thread apply all bt {depth}",
        ]

        if exe_path and exe_path.strip():
            command.extend([exe_path.strip(), core_path])
        else:
            command.extend(["-c", core_path])

        result = _run(command, timeout=45.0)
        combined = "\n".join([result.get("stdout", ""), result.get("stderr", "")]).strip()

        signal_match = re.search(r"Program terminated with signal\s+([^,\n]+)", combined)
        signal = signal_match.group(1).strip() if signal_match else "unknown"

        threads = _parse_gdb_thread_bt(combined)
        suspected = threads[0]["frames"][0] if threads and threads[0]["frames"] else ""

        return {
            "success": result["ok"] or len(threads) > 0,
            "core_path": core_path,
            "exe_path": exe_path.strip() if exe_path else "",
            "signal": signal,
            "thread_count": len(threads),
            "suspected_top_frame": suspected,
            "threads": threads,
            "raw": combined if len(threads) == 0 else "",
        }
