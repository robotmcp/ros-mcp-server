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


def _get_process_identity(pid: int) -> dict[str, Any]:
    """Get process executable and command line."""
    info = _run(["ps", "-p", str(pid), "-o", "args=", "-o", "comm="])
    lines = [ln for ln in info.get("stdout", "").splitlines() if ln.strip()]
    cmdline = lines[0].strip() if lines else ""
    exe = lines[1].strip() if len(lines) > 1 else (os.path.basename(cmdline.split()[0]) if cmdline else "")
    return {
        "pid": pid,
        "exe": exe,
        "cmdline": cmdline,
    }


def _resolve_pid_from_rosnode(node_name: str) -> dict[str, Any] | None:
    """Try resolving PID directly via `rosnode info` for highest accuracy."""
    candidates = [node_name]
    if not node_name.startswith("/"):
        candidates.append(f"/{node_name}")

    seen = set()
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)

        info = _run(["rosnode", "info", candidate], timeout=8.0)
        if not info["ok"]:
            continue

        match = re.search(r"^\s*Pid:\s*(\d+)\s*$", info.get("stdout", ""), re.MULTILINE)
        if not match:
            continue

        pid = int(match.group(1))
        if not _pid_exists(pid):
            continue

        proc = _get_process_identity(pid)
        proc.update(
            {
                "match_score": 1000,
                "match_reasons": ["matched via rosnode info"],
                "node_name": candidate,
            }
        )
        return proc

    return None


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
            score += 120
            reasons.append("matched __name remap")

        if full and full in args:
            score += 45
            reasons.append("matched full node name in cmdline")

        if short and re.search(rf"\b{re.escape(short)}\b", args):
            score += 30
            reasons.append("matched short node token")

        try:
            argv = shlex.split(args)
            exe_path = argv[0] if argv else ""
        except Exception:
            exe_path = args.split()[0]

        exe_base = os.path.basename(exe_path)
        if short and exe_base == short:
            score += 45
            reasons.append("executable basename exact match")
        elif short and short and short in exe_base:
            score += 15
            reasons.append("executable basename partial match")

        if score > 0:
            candidates.append(
                {
                    "pid": pid,
                    "exe": exe_base,
                    "cmdline": args,
                    "match_score": score,
                    "match_reasons": reasons,
                }
            )

    candidates.sort(key=lambda c: (-c["match_score"], c["pid"]))
    return candidates


def _parse_gdb_thread_bt(output: str) -> list[dict[str, Any]]:
    """Parse `thread apply all bt` output into structured thread/frame blocks."""
    threads: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    header_re = re.compile(r"^Thread\s+(\d+)\s+\((.*)\):$")
    lwp_re = re.compile(r"\(LWP\s+(\d+)\)")
    frame_re = re.compile(r"^#(\d+)\s+(.*)$")

    for raw_line in output.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()

        header_match = header_re.match(stripped)
        if header_match:
            if current:
                threads.append(current)

            thread_id = int(header_match.group(1))
            header_payload = header_match.group(2)
            lwp_match = lwp_re.search(header_payload)
            lwp = int(lwp_match.group(1)) if lwp_match else None

            current = {
                "thread_id": thread_id,
                "lwp": lwp,
                "header": stripped,
                "frames": [],
            }
            continue

        if current is None:
            continue

        frame_match = frame_re.match(stripped)
        if frame_match:
            current["frames"].append(
                {
                    "index": int(frame_match.group(1)),
                    "text": stripped,
                }
            )
            continue

        # Continuation line for previous frame
        if current["frames"] and stripped:
            current["frames"][-1]["text"] += f" {stripped}"

    if current:
        threads.append(current)

    return threads


def _parse_assignment_lines(lines: list[str]) -> dict[str, str]:
    """Parse `name = value` lines from gdb output into a dict."""
    values: dict[str, str] = {}
    assign_re = re.compile(r"^\s*([A-Za-z_][\w:<>\[\].-]*)\s*=\s*(.*)$")

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("No locals") or stripped.startswith("No arguments"):
            continue

        m = assign_re.match(stripped)
        if m:
            values[m.group(1)] = m.group(2)

    return values


def _extract_signal(combined: str) -> dict[str, str]:
    """Extract signal info from gdb text."""
    match = re.search(r"Program terminated with signal\s+([A-Z0-9]+)(?:,\s*([^\n]+))?", combined)
    if not match:
        return {"name": "unknown", "description": ""}
    return {
        "name": match.group(1).strip(),
        "description": (match.group(2) or "").strip(),
    }


def _extract_current_thread_id(combined: str) -> int | None:
    """Extract current thread id from gdb output if present."""
    match = re.search(r"Current thread is\s+(\d+)", combined)
    if match:
        return int(match.group(1))
    return None


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

        # If user provided PID directly
        if node_name.isdigit():
            pid = int(node_name)
            if _pid_exists(pid):
                proc = _get_process_identity(pid)
                proc.update({"match_score": 999, "match_reasons": ["query is PID"]})
                return {
                    "query": node_name,
                    "resolution_method": "direct_pid",
                    "best": proc,
                    "candidates": [proc],
                }
            return {"error": f"PID {pid} does not exist"}

        # Best path: resolve from rosnode info
        resolved = _resolve_pid_from_rosnode(node_name)
        if resolved:
            return {
                "query": node_name,
                "resolution_method": "rosnode_info",
                "best": resolved,
                "candidates": [resolved],
            }

        # Fallback: command line matching
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
                "resolution_method": "ps_scan",
                "best": None,
                "candidates": [],
                "note": "No likely process matches found. If launched via roslaunch, try exact node name (/name) or pass PID directly.",
            }

        return {
            "query": node_name,
            "resolution_method": "ps_scan",
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
            "info threads",
            "-ex",
            f"thread apply all bt {depth}",
            "-p",
            str(pid),
        ]

        result = _run(command, timeout=35.0)
        combined = "\n".join([result.get("stdout", ""), result.get("stderr", "")]).strip()

        if not result["ok"] and "ptrace" in combined.lower():
            return {
                "pid": pid,
                "success": False,
                "error": "gdb attach failed (ptrace restrictions).",
                "raw": combined,
            }

        threads = _parse_gdb_thread_bt(combined)
        current_thread_id = _extract_current_thread_id(combined)

        suspected_top_frame = ""
        if threads:
            if current_thread_id is not None:
                for thread in threads:
                    if thread.get("thread_id") == current_thread_id and thread.get("frames"):
                        suspected_top_frame = thread["frames"][0]["text"]
                        break
            if not suspected_top_frame and threads[0].get("frames"):
                suspected_top_frame = threads[0]["frames"][0]["text"]

        return {
            "pid": pid,
            "success": len(threads) > 0,
            "thread_count": len(threads),
            "current_thread_id": current_thread_id,
            "suspected_top_frame": suspected_top_frame,
            "threads": threads,
            "raw": combined if len(threads) == 0 else "",
        }

    @mcp.tool(
        description=(
            "Attach gdb to a PID and inspect arguments/locals for a specific thread/frame.\n"
            "Example:\ngdb_frame_locals(pid=12345, thread_id=1, frame_id=0)"
        ),
        annotations=ToolAnnotations(
            title="GDB Frame Locals",
            readOnlyHint=True,
        ),
    )
    def gdb_frame_locals(pid: int, thread_id: int = 1, frame_id: int = 0) -> dict:
        """Capture args/locals from one stack frame of a running process via gdb."""
        try:
            pid = int(pid)
            thread_id = int(thread_id)
            frame_id = int(frame_id)
        except Exception:
            return {"error": "pid, thread_id, and frame_id must be integers"}

        if pid <= 0:
            return {"error": "pid must be > 0"}
        if thread_id <= 0:
            return {"error": "thread_id must be > 0"}
        if frame_id < 0:
            return {"error": "frame_id must be >= 0"}
        if not _pid_exists(pid):
            return {"error": f"PID {pid} not found"}

        command = [
            "gdb",
            "-q",
            "-n",
            "-batch",
            "-ex",
            "set pagination off",
            "-ex",
            f"thread {thread_id}",
            "-ex",
            f"frame {frame_id}",
            "-ex",
            "printf \"__ARGS_BEGIN__\\n\"",
            "-ex",
            "info args",
            "-ex",
            "printf \"__LOCALS_BEGIN__\\n\"",
            "-ex",
            "info locals",
            "-p",
            str(pid),
        ]

        result = _run(command, timeout=30.0)
        combined = "\n".join([result.get("stdout", ""), result.get("stderr", "")]).strip()

        if "ptrace" in combined.lower() and not result["ok"]:
            return {
                "pid": pid,
                "success": False,
                "error": "gdb attach failed (ptrace restrictions).",
                "raw": combined,
            }

        lines = combined.splitlines()
        args_lines: list[str] = []
        locals_lines: list[str] = []
        section = None

        for line in lines:
            stripped = line.strip()
            if stripped == "__ARGS_BEGIN__":
                section = "args"
                continue
            if stripped == "__LOCALS_BEGIN__":
                section = "locals"
                continue
            if section == "args":
                args_lines.append(line)
            elif section == "locals":
                locals_lines.append(line)

        parsed_args = _parse_assignment_lines(args_lines)
        parsed_locals = _parse_assignment_lines(locals_lines)

        return {
            "pid": pid,
            "thread_id": thread_id,
            "frame_id": frame_id,
            "success": bool(parsed_args or parsed_locals),
            "args": parsed_args,
            "locals": parsed_locals,
            "raw": combined if not (parsed_args or parsed_locals) else "",
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
            "info threads",
            "-ex",
            f"thread apply all bt {depth}",
        ]

        if exe_path and exe_path.strip():
            command.extend([exe_path.strip(), core_path])
        else:
            command.extend(["-c", core_path])

        result = _run(command, timeout=45.0)
        combined = "\n".join([result.get("stdout", ""), result.get("stderr", "")]).strip()

        signal = _extract_signal(combined)
        threads = _parse_gdb_thread_bt(combined)
        current_thread_id = _extract_current_thread_id(combined)

        suspected_top_frame = ""
        if threads:
            if current_thread_id is not None:
                for thread in threads:
                    if thread.get("thread_id") == current_thread_id and thread.get("frames"):
                        suspected_top_frame = thread["frames"][0]["text"]
                        break
            if not suspected_top_frame and threads[0].get("frames"):
                suspected_top_frame = threads[0]["frames"][0]["text"]

        return {
            "success": result["ok"] or len(threads) > 0,
            "core_path": core_path,
            "exe_path": exe_path.strip() if exe_path else "",
            "signal": signal,
            "thread_count": len(threads),
            "current_thread_id": current_thread_id,
            "suspected_top_frame": suspected_top_frame,
            "threads": threads,
            "raw": combined if len(threads) == 0 else "",
        }
