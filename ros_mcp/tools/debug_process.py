"""Debug process tools for ROS1 C++/Python node investigation."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
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


def _parse_frame_text(frame_text: str) -> dict[str, Any]:
    """Extract common frame fields (function, file, line) from gdb frame text."""
    parsed: dict[str, Any] = {}

    # Example: #0  0x.... in foo::bar(...) at /path/file.cpp:123
    func_match = re.search(r"\sin\s+(.+?)(?:\sat\s|\sfrom\s|$)", frame_text)
    if func_match:
        parsed["function"] = func_match.group(1).strip()

    file_line_match = re.search(r"\sat\s+(.+?):(\d+)\s*$", frame_text)
    if file_line_match:
        parsed["file"] = file_line_match.group(1).strip()
        parsed["line"] = int(file_line_match.group(2))

    addr_match = re.search(r"^#\d+\s+(0x[0-9a-fA-F]+)", frame_text)
    if addr_match:
        parsed["address"] = addr_match.group(1)

    if "??" in frame_text:
        parsed["symbolized"] = False
    else:
        parsed["symbolized"] = True

    return parsed


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
            frame_text = stripped
            frame_payload: dict[str, Any] = {
                "index": int(frame_match.group(1)),
                "text": frame_text,
            }
            frame_payload.update(_parse_frame_text(frame_text))
            current["frames"].append(frame_payload)
            continue

        # Continuation line for previous frame
        if current["frames"] and stripped:
            current["frames"][-1]["text"] += f" {stripped}"
            # Re-parse after continuation update
            reparsed = _parse_frame_text(current["frames"][-1]["text"])
            current["frames"][-1].update(reparsed)

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


def _classify_cpp_crash(signal_name: str, top_frame: str, raw_text: str = "") -> dict[str, Any]:
    """Heuristic crash classifier for C/C++ failures."""
    signal_name = (signal_name or "").upper().strip()
    top = (top_frame or "").lower()
    raw = (raw_text or "").lower()

    labels: list[str] = []
    recommendations: list[str] = []

    if signal_name == "SIGSEGV":
        labels.append("invalid_memory_access")
        recommendations.append("Inspect pointer lifetimes and ownership near the top frame.")
        recommendations.append("Rebuild with AddressSanitizer for stronger diagnostics.")

    if signal_name == "SIGABRT":
        labels.append("abort_or_assert")
        recommendations.append("Search for failed assertions and uncaught exceptions in logs.")

    if signal_name == "SIGFPE":
        labels.append("arithmetic_error")
        recommendations.append("Check divide-by-zero and invalid numeric operations.")

    if "??" in top_frame or "??" in raw_text:
        labels.append("missing_symbols")
        recommendations.append("Install debug symbols or rebuild target with debug info.")

    if "optimized out" in raw:
        labels.append("optimized_build")
        recommendations.append("Use Debug or RelWithDebInfo to improve stack/local visibility.")

    if "std::bad_alloc" in raw or "operator new" in top:
        labels.append("possible_memory_exhaustion")
        recommendations.append("Check memory growth and limits; capture RSS over time.")

    if "__assert_fail" in raw or "assert" in top:
        labels.append("assertion_failure")

    if "pthread_mutex" in top or "futex" in top:
        labels.append("possible_thread_contention_or_deadlock")

    if not labels:
        labels.append("unclassified")
        recommendations.append("Capture locals for top frames and rerun under sanitizer/rr.")

    rr = _get_rr_status()
    if rr.get("available"):
        recommendations.append("rr is available: use `rr record` + `rr replay -d gdb` for deterministic replay.")
    else:
        recommendations.append("rr not detected: consider installing rr for replay debugging if environment supports it.")

    return {
        "labels": labels,
        "primary_label": labels[0],
        "recommendations": recommendations,
    }


def _parse_pyspy_dump(output: str) -> list[dict[str, Any]]:
    """Parse py-spy dump output into thread + stack entries."""
    threads: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for raw_line in output.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if not stripped:
            continue

        # Common pattern: Thread 12345 (active): "MainThread"
        if stripped.startswith("Thread "):
            if current:
                threads.append(current)
            current = {
                "header": stripped,
                "frames": [],
            }
            continue

        if current is not None:
            current["frames"].append(stripped)

    if current:
        threads.append(current)

    return threads


def _collect_gdb_threads(pid: int, depth: int = 40, timeout: float = 35.0) -> dict[str, Any]:
    """Collect thread backtraces via gdb and parse them."""
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

    result = _run(command, timeout=timeout)
    combined = "\n".join([result.get("stdout", ""), result.get("stderr", "")]).strip()

    if not result["ok"] and "ptrace" in combined.lower():
        return {
            "ok": False,
            "error": "gdb attach failed (ptrace restrictions).",
            "combined": combined,
            "threads": [],
            "current_thread_id": None,
        }

    threads = _parse_gdb_thread_bt(combined)
    current_thread_id = _extract_current_thread_id(combined)

    return {
        "ok": result["ok"] or len(threads) > 0,
        "combined": combined,
        "threads": threads,
        "current_thread_id": current_thread_id,
    }


def _is_probably_idle_frame(frame: dict[str, Any]) -> bool:
    """Heuristic: whether a frame likely represents idle/wait state."""
    text = str(frame.get("text", "")).lower()
    fn = str(frame.get("function", "")).lower()
    source = f"{fn} {text}"

    idle_markers = [
        "futex",
        "pthread_cond_wait",
        "pthread_mutex_lock",
        "poll",
        "epoll_wait",
        "nanosleep",
        "clock_nanosleep",
        "__lll_lock_wait",
    ]
    return any(marker in source for marker in idle_markers)


def _select_target_thread(
    threads: list[dict[str, Any]], current_thread_id: int | None
) -> tuple[int | None, str]:
    """Choose a thread for deeper inspection."""
    if not threads:
        return None, "no_threads"

    if current_thread_id is not None:
        for thread in threads:
            if thread.get("thread_id") == current_thread_id:
                return current_thread_id, "gdb_current_thread"

    for thread in threads:
        frames = thread.get("frames", [])
        if not frames:
            continue
        top = frames[0]
        if not _is_probably_idle_frame(top):
            return int(thread.get("thread_id")), "first_non_idle_top_frame"

    return int(threads[0].get("thread_id")), "fallback_first_thread"


def _capture_frame_locals(pid: int, thread_id: int, frame_id: int) -> dict[str, Any]:
    """Capture args/locals from one stack frame via gdb."""
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
            "thread_id": thread_id,
            "frame_id": frame_id,
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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON helper."""
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def _write_text(path: Path, content: str) -> None:
    """Write plain text helper."""
    path.write_text(content)


def _get_rr_status() -> dict[str, Any]:
    """Check rr availability and return quick usage hints."""
    rr_bin = shutil.which("rr")
    status: dict[str, Any] = {
        "available": bool(rr_bin),
        "path": rr_bin or "",
        "hints": [],
    }

    if rr_bin:
        status["hints"] = [
            "Record run: rr record <your_node_command>",
            "Replay debug: rr replay -d gdb",
            "Use reverse-continue / reverse-step in replay for hard-to-reproduce bugs.",
        ]
    else:
        status["hints"] = [
            "Install rr for deterministic replay debugging (if kernel/CPU compatible).",
            "Fallback: use gdb + core dumps + AddressSanitizer.",
        ]

    perf_path = Path("/proc/sys/kernel/perf_event_paranoid")
    if perf_path.exists():
        try:
            value = perf_path.read_text().strip()
            status["perf_event_paranoid"] = value
        except Exception:
            pass

    return status


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

        collected = _collect_gdb_threads(pid=pid, depth=depth, timeout=35.0)
        if not collected.get("ok") and collected.get("error"):
            return {
                "pid": pid,
                "success": False,
                "error": collected.get("error"),
                "raw": collected.get("combined", ""),
            }

        combined = collected.get("combined", "")
        threads = collected.get("threads", [])
        current_thread_id = collected.get("current_thread_id")

        suggested_thread_id, suggested_reason = _select_target_thread(threads, current_thread_id)

        suspected_top_frame = ""
        if suggested_thread_id is not None:
            for thread in threads:
                if thread.get("thread_id") == suggested_thread_id and thread.get("frames"):
                    suspected_top_frame = thread["frames"][0]["text"]
                    break

        return {
            "pid": pid,
            "success": len(threads) > 0,
            "thread_count": len(threads),
            "current_thread_id": current_thread_id,
            "suggested_thread_id": suggested_thread_id,
            "suggested_thread_reason": suggested_reason,
            "suspected_top_frame": suspected_top_frame,
            "threads": threads,
            "raw": combined if len(threads) == 0 else "",
        }

    @mcp.tool(
        description=(
            "Attach gdb to a PID and inspect arguments/locals for a specific thread/frame.\n"
            "Set thread_id=0 to auto-select a likely interesting thread.\n"
            "Example:\ngdb_frame_locals(pid=12345, thread_id=0, frame_id=0)"
        ),
        annotations=ToolAnnotations(
            title="GDB Frame Locals",
            readOnlyHint=True,
        ),
    )
    def gdb_frame_locals(pid: int, thread_id: int = 0, frame_id: int = 0) -> dict:
        """Capture args/locals from one stack frame of a running process via gdb."""
        try:
            pid = int(pid)
            thread_id = int(thread_id)
            frame_id = int(frame_id)
        except Exception:
            return {"error": "pid, thread_id, and frame_id must be integers"}

        if pid <= 0:
            return {"error": "pid must be > 0"}
        if frame_id < 0:
            return {"error": "frame_id must be >= 0"}
        if not _pid_exists(pid):
            return {"error": f"PID {pid} not found"}

        selected_thread_id = thread_id
        selected_reason = "requested"

        if thread_id <= 0:
            collected = _collect_gdb_threads(pid=pid, depth=30, timeout=25.0)
            if not collected.get("ok") and collected.get("error"):
                return {
                    "pid": pid,
                    "success": False,
                    "error": collected.get("error"),
                    "raw": collected.get("combined", ""),
                }

            selected_thread_id, selected_reason = _select_target_thread(
                collected.get("threads", []),
                collected.get("current_thread_id"),
            )
            if selected_thread_id is None:
                return {
                    "pid": pid,
                    "success": False,
                    "error": "Could not auto-select a thread",
                    "raw": collected.get("combined", ""),
                }

        locals_result = _capture_frame_locals(
            pid=pid,
            thread_id=int(selected_thread_id),
            frame_id=frame_id,
        )

        locals_result["selected_thread_reason"] = selected_reason
        return locals_result

    @mcp.tool(
        description=(
            "Capture Python thread stacks from a running process using py-spy.\n"
            "Example:\npy_stack_snapshot(pid=12345)"
        ),
        annotations=ToolAnnotations(
            title="Python Stack Snapshot",
            readOnlyHint=True,
        ),
    )
    def py_stack_snapshot(pid: int) -> dict:
        """Capture Python thread stacks for a running process."""
        try:
            pid = int(pid)
        except Exception:
            return {"error": "pid must be an integer"}

        if pid <= 0:
            return {"error": "pid must be > 0"}
        if not _pid_exists(pid):
            return {"error": f"PID {pid} not found"}

        pyspy_bin = shutil.which("py-spy")
        if not pyspy_bin:
            return {
                "pid": pid,
                "success": False,
                "error": "py-spy is not installed",
                "hint": "Install py-spy (e.g., pipx install py-spy) and retry.",
            }

        command = [pyspy_bin, "dump", "--pid", str(pid), "--threads"]
        result = _run(command, timeout=20.0)
        combined = "\n".join([result.get("stdout", ""), result.get("stderr", "")]).strip()

        if not result["ok"]:
            return {
                "pid": pid,
                "success": False,
                "error": "py-spy failed",
                "raw": combined,
            }

        threads = _parse_pyspy_dump(result.get("stdout", ""))
        blocked_hints = [
            th["header"]
            for th in threads
            if any("wait" in fr.lower() or "sleep" in fr.lower() for fr in th.get("frames", []))
        ]

        return {
            "pid": pid,
            "success": True,
            "thread_count": len(threads),
            "threads": threads,
            "blocked_hints": blocked_hints,
        }

    @mcp.tool(
        description=(
            "Check whether rr (record/replay debugger) is available and show quick usage hints.\n"
            "Example:\nrr_status()"
        ),
        annotations=ToolAnnotations(
            title="RR Status",
            readOnlyHint=True,
        ),
    )
    def rr_status() -> dict:
        """Return rr availability and usage hints."""
        return _get_rr_status()

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

        hypothesis = _classify_cpp_crash(
            signal_name=signal.get("name", ""),
            top_frame=suspected_top_frame,
            raw_text=combined,
        )

        return {
            "success": result["ok"] or len(threads) > 0,
            "core_path": core_path,
            "exe_path": exe_path.strip() if exe_path else "",
            "signal": signal,
            "thread_count": len(threads),
            "current_thread_id": current_thread_id,
            "suspected_top_frame": suspected_top_frame,
            "crash_hypothesis": hypothesis,
            "threads": threads,
            "raw": combined if len(threads) == 0 else "",
        }

    @mcp.tool(
        description=(
            "Collect a minimal reproducibility/debug bundle for a ROS node or PID.\n"
            "Example:\nrepro_bundle_collect(node_name='/move_base')"
        ),
        annotations=ToolAnnotations(
            title="Repro Bundle Collect",
            readOnlyHint=True,
        ),
    )
    def repro_bundle_collect(
        node_name: str = "",
        pid: int = 0,
        out_dir: str = "./debug_bundles",
        depth: int = 40,
        include_ros_graph: bool = True,
        include_topic_sample: bool = False,
        sample_topic: str = "",
        sample_msg_count: int = 3,
        sample_timeout_sec: float = 8.0,
    ) -> dict:
        """Collect a minimal debug bundle (process, gdb backtrace, ROS snapshots)."""
        depth = max(1, min(int(depth), 200))
        sample_msg_count = max(1, min(int(sample_msg_count), 20))
        sample_timeout_sec = max(1.0, min(float(sample_timeout_sec), 60.0))

        resolved = None
        selected_pid = int(pid) if int(pid) > 0 else 0

        if selected_pid <= 0 and node_name.strip():
            resolved = _resolve_pid_from_rosnode(node_name.strip())
            if resolved:
                selected_pid = int(resolved["pid"])
            else:
                ps = _run(["ps", "-eo", "pid,args", "--no-headers"])
                if ps.get("ok"):
                    matches = _parse_ps_candidates(ps.get("stdout", ""), node_name.strip())
                    if matches:
                        resolved = matches[0]
                        selected_pid = int(matches[0]["pid"])

        if selected_pid <= 0:
            return {
                "success": False,
                "error": "Could not resolve target PID. Provide node_name or pid.",
            }

        if not _pid_exists(selected_pid):
            return {
                "success": False,
                "error": f"PID {selected_pid} not found",
            }

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bundle_path = Path(out_dir).expanduser().resolve() / f"repro_{stamp}_pid{selected_pid}"
        bundle_path.mkdir(parents=True, exist_ok=True)

        process_info = _get_process_identity(selected_pid)

        rosnode_info_text = ""
        if node_name.strip():
            info = _run(["rosnode", "info", node_name.strip()], timeout=8.0)
            rosnode_info_text = (info.get("stdout", "") + "\n" + info.get("stderr", "")).strip()
            (bundle_path / "rosnode_info.txt").write_text(rosnode_info_text)

        rosnode_list_path = ""
        rostopic_list_path = ""
        rosservice_list_path = ""
        rosparam_list_path = ""

        if include_ros_graph:
            rosnode_list = _run(["rosnode", "list"], timeout=8.0)
            rosnode_list_path = str(bundle_path / "rosnode_list.txt")
            _write_text(
                Path(rosnode_list_path),
                (rosnode_list.get("stdout", "") + "\n" + rosnode_list.get("stderr", "")).strip(),
            )

            rostopic_list = _run(["rostopic", "list", "-v"], timeout=10.0)
            rostopic_list_path = str(bundle_path / "rostopic_list_v.txt")
            _write_text(
                Path(rostopic_list_path),
                (rostopic_list.get("stdout", "") + "\n" + rostopic_list.get("stderr", "")).strip(),
            )

            rosservice_list = _run(["rosservice", "list"], timeout=10.0)
            rosservice_list_path = str(bundle_path / "rosservice_list.txt")
            _write_text(
                Path(rosservice_list_path),
                (rosservice_list.get("stdout", "") + "\n" + rosservice_list.get("stderr", "")).strip(),
            )

            rosparam_list = _run(["rosparam", "list"], timeout=10.0)
            rosparam_list_path = str(bundle_path / "rosparam_list.txt")
            _write_text(
                Path(rosparam_list_path),
                (rosparam_list.get("stdout", "") + "\n" + rosparam_list.get("stderr", "")).strip(),
            )

        coredump_list = _run(["coredumpctl", "--no-pager", "list", "--reverse", "--lines", "10"])
        coredump_list_path = str(bundle_path / "coredumpctl_list.txt")
        _write_text(
            Path(coredump_list_path),
            (coredump_list.get("stdout", "") + "\n" + coredump_list.get("stderr", "")).strip(),
        )

        topic_sample_file = ""
        topic_hz_file = ""
        if include_topic_sample and sample_topic.strip():
            sample_topic_clean = sample_topic.strip()
            topic_echo = _run(
                ["rostopic", "echo", "-n", str(sample_msg_count), sample_topic_clean],
                timeout=sample_timeout_sec,
            )
            topic_sample_file = str(bundle_path / "rostopic_sample.txt")
            _write_text(
                Path(topic_sample_file),
                (topic_echo.get("stdout", "") + "\n" + topic_echo.get("stderr", "")).strip(),
            )

            topic_hz = _run(["rostopic", "hz", "-w", "5", sample_topic_clean], timeout=sample_timeout_sec)
            topic_hz_file = str(bundle_path / "rostopic_hz.txt")
            _write_text(
                Path(topic_hz_file),
                (topic_hz.get("stdout", "") + "\n" + topic_hz.get("stderr", "")).strip(),
            )

        bt = _collect_gdb_threads(pid=selected_pid, depth=depth, timeout=35.0)
        suggested_thread_id, suggested_reason = _select_target_thread(
            bt.get("threads", []), bt.get("current_thread_id")
        )

        suspected_top_frame = ""
        if suggested_thread_id is not None:
            for thread in bt.get("threads", []):
                if thread.get("thread_id") == suggested_thread_id and thread.get("frames"):
                    suspected_top_frame = thread["frames"][0].get("text", "")
                    break

        bt_payload = {
            "pid": selected_pid,
            "ok": bt.get("ok", False),
            "current_thread_id": bt.get("current_thread_id"),
            "suggested_thread_id": suggested_thread_id,
            "suggested_thread_reason": suggested_reason,
            "suspected_top_frame": suspected_top_frame,
            "threads": bt.get("threads", []),
            "raw": bt.get("combined", "") if not bt.get("threads") else "",
        }
        _write_json(bundle_path / "gdb_thread_bt.json", bt_payload)

        frame_payload = {}
        if suggested_thread_id is not None:
            frame_payload = _capture_frame_locals(
                pid=selected_pid,
                thread_id=int(suggested_thread_id),
                frame_id=0,
            )
            frame_payload["selected_thread_reason"] = suggested_reason
            _write_json(bundle_path / "gdb_frame0_locals.json", frame_payload)

        hypothesis = _classify_cpp_crash(
            signal_name="",
            top_frame=suspected_top_frame,
            raw_text=bt.get("combined", ""),
        )

        rr = _get_rr_status()

        summary = {
            "created_at": datetime.now().isoformat(),
            "bundle_dir": str(bundle_path),
            "node_name": node_name,
            "pid": selected_pid,
            "process": process_info,
            "pid_resolution": resolved,
            "gdb": {
                "thread_count": len(bt.get("threads", [])),
                "suggested_thread_id": suggested_thread_id,
                "suggested_thread_reason": suggested_reason,
                "suspected_top_frame": suspected_top_frame,
                "crash_hypothesis": hypothesis,
            },
            "rr": rr,
            "files": {
                "rosnode_info": str(bundle_path / "rosnode_info.txt") if node_name.strip() else "",
                "rosnode_list": rosnode_list_path,
                "rostopic_list_v": rostopic_list_path,
                "rosservice_list": rosservice_list_path,
                "rosparam_list": rosparam_list_path,
                "coredumpctl_list": coredump_list_path,
                "gdb_thread_bt": str(bundle_path / "gdb_thread_bt.json"),
                "gdb_frame0_locals": str(bundle_path / "gdb_frame0_locals.json") if frame_payload else "",
                "topic_sample": topic_sample_file,
                "topic_hz": topic_hz_file,
            },
        }
        _write_json(bundle_path / "summary.json", summary)

        return {
            "success": True,
            "bundle_dir": str(bundle_path),
            "summary": summary,
        }

    @mcp.tool(
        description=(
            "Classify likely C/C++ crash cause from signal and top frame text.\n"
            "Example:\nclassify_cpp_crash(signal_name='SIGSEGV', top_frame='#0  ...')"
        ),
        annotations=ToolAnnotations(
            title="Classify C++ Crash",
            readOnlyHint=True,
        ),
    )
    def classify_cpp_crash(signal_name: str = "", top_frame: str = "", raw_text: str = "") -> dict:
        """Classify likely crash cause heuristically from stack context."""
        return _classify_cpp_crash(signal_name=signal_name, top_frame=top_frame, raw_text=raw_text)
