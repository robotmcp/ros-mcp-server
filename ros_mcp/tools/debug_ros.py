"""ROS1 diagnostic tools for timing and bridge-lag investigation."""

from __future__ import annotations

import json
import statistics
import time
from typing import Any

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ros_mcp.utils.websocket import WebSocketManager, parse_input


def _call_service(
    ws_manager: WebSocketManager,
    service: str,
    service_type: str,
    args: dict[str, Any],
    request_id: str,
) -> dict[str, Any]:
    request = {
        "op": "call_service",
        "service": service,
        "type": service_type,
        "args": args,
        "id": request_id,
    }
    with ws_manager:
        response = ws_manager.request(request)
    return response if isinstance(response, dict) else {}


def _parse_boolish(value: Any) -> bool | None:
    """Parse ROS parameter value into bool when possible."""
    if isinstance(value, bool):
        return value
    if value is None:
        return None

    text = str(value).strip().strip('"').strip("'")
    if text == "":
        return None

    lower = text.lower()
    if lower in {"true", "1", "yes", "on"}:
        return True
    if lower in {"false", "0", "no", "off"}:
        return False

    try:
        parsed = json.loads(text)
        if isinstance(parsed, bool):
            return parsed
    except Exception:
        pass

    return None


def _extract_stamp_seconds(msg: dict[str, Any]) -> float | None:
    """Extract ROS timestamp from common message layouts."""
    # Header stamp layout (most topics)
    header = msg.get("header")
    if isinstance(header, dict):
        stamp = header.get("stamp")
        value = _stamp_dict_to_seconds(stamp)
        if value is not None:
            return value

    # Clock layout (/clock)
    clock = msg.get("clock")
    value = _stamp_dict_to_seconds(clock)
    if value is not None:
        return value

    # Direct stamp layout
    value = _stamp_dict_to_seconds(msg.get("stamp"))
    if value is not None:
        return value

    return None


def _stamp_dict_to_seconds(stamp: Any) -> float | None:
    """Convert ROS time dict to float seconds."""
    if not isinstance(stamp, dict):
        return None

    if "secs" in stamp or "nsecs" in stamp:
        secs = float(stamp.get("secs", 0))
        nsecs = float(stamp.get("nsecs", 0))
        return secs + (nsecs * 1e-9)

    if "sec" in stamp or "nanosec" in stamp:
        secs = float(stamp.get("sec", 0))
        nsecs = float(stamp.get("nanosec", 0))
        return secs + (nsecs * 1e-9)

    return None


def _percentile(sorted_values: list[float], p: float) -> float:
    """Compute percentile with linear interpolation."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]

    rank = (len(sorted_values) - 1) * p
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    frac = rank - low
    return sorted_values[low] * (1 - frac) + sorted_values[high] * frac


def _lag_diagnosis(age_drift: float, p95_age: float, hz: float) -> str:
    """Simple heuristic diagnosis for lag symptoms."""
    if hz <= 0:
        return "no_messages"
    if age_drift > 1.0 and p95_age > 1.0:
        return "increasing_queue_delay_likely"
    if p95_age > 0.5:
        return "high_latency_detected"
    if hz < 1.0:
        return "low_message_rate"
    return "no_strong_lag_signal"


def register_debug_ros_tools(mcp: FastMCP, ws_manager: WebSocketManager) -> None:
    """Register ROS timing/lag diagnostic tools."""

    @mcp.tool(
        description=(
            "Inspect ROS time configuration and /clock health.\n"
            "Example:\ntf_time_snapshot()"
        ),
        annotations=ToolAnnotations(
            title="TF Time Snapshot",
            readOnlyHint=True,
        ),
    )
    def tf_time_snapshot(clock_wait_sec: float = 2.0) -> dict:
        """Inspect /use_sim_time, /clock availability, and timing risks."""
        clock_wait_sec = max(0.1, min(float(clock_wait_sec), 15.0))

        # /use_sim_time
        use_sim_resp = _call_service(
            ws_manager,
            "/rosapi/get_param",
            "rosapi/GetParam",
            {"name": "/use_sim_time"},
            "tf_time_use_sim_time",
        )

        raw_use_sim = use_sim_resp.get("values", {}).get("value") if isinstance(use_sim_resp, dict) else None
        use_sim_time = _parse_boolish(raw_use_sim)

        # Topic inventory
        topics_resp = _call_service(
            ws_manager,
            "/rosapi/topics",
            "rosapi/Topics",
            {},
            "tf_time_topics",
        )
        topics = topics_resp.get("values", {}).get("topics", []) if isinstance(topics_resp, dict) else []
        types = topics_resp.get("values", {}).get("types", []) if isinstance(topics_resp, dict) else []

        clock_present = "/clock" in topics
        clock_type = ""
        if clock_present:
            try:
                idx = topics.index("/clock")
                clock_type = types[idx] if idx < len(types) else ""
            except Exception:
                clock_type = ""

        # Probe one /clock sample (if present)
        clock_sample = None
        clock_received = False
        if clock_present:
            subscribe_msg = {
                "op": "subscribe",
                "topic": "/clock",
                "type": clock_type or "rosgraph_msgs/Clock",
                "queue_length": 1,
                "throttle_rate": 0,
            }
            with ws_manager:
                send_err = ws_manager.send(subscribe_msg)
                if not send_err:
                    deadline = time.time() + clock_wait_sec
                    while time.time() < deadline:
                        raw = ws_manager.receive(timeout=0.2)
                        if raw is None:
                            continue
                        parsed, _ = parse_input(raw, expects_image=False)
                        if not parsed:
                            continue
                        if parsed.get("op") == "publish" and parsed.get("topic") == "/clock":
                            msg = parsed.get("msg", {})
                            stamp = _extract_stamp_seconds(msg)
                            clock_sample = {
                                "msg": msg,
                                "stamp_seconds": stamp,
                            }
                            clock_received = True
                            break
                ws_manager.send({"op": "unsubscribe", "topic": "/clock"})

        checks: list[str] = []
        risk_level = "low"

        if use_sim_time is True and not clock_present:
            risk_level = "high"
            checks.append("/use_sim_time=true but /clock topic is missing")
        elif use_sim_time is True and clock_present and not clock_received:
            risk_level = "high"
            checks.append("/use_sim_time=true and /clock exists, but no recent clock messages received")
        elif use_sim_time is False and clock_present:
            risk_level = "medium"
            checks.append("/clock exists while /use_sim_time=false (possible mixed time sources)")
        elif use_sim_time is None:
            risk_level = "medium"
            checks.append("Could not parse /use_sim_time value")
        else:
            checks.append("Time configuration appears consistent")

        return {
            "use_sim_time": {
                "parsed": use_sim_time,
                "raw": raw_use_sim,
            },
            "clock": {
                "topic_present": clock_present,
                "topic_type": clock_type,
                "message_received": clock_received,
                "sample": clock_sample,
            },
            "risk_level": risk_level,
            "checks": checks,
        }

    @mcp.tool(
        description=(
            "Measure topic rate and message age (from header.stamp) over a short window.\n"
            "Example:\ntopic_age_probe('/camera/image_raw', msg_type='sensor_msgs/Image', window_sec=10)"
        ),
        annotations=ToolAnnotations(
            title="Topic Age Probe",
            readOnlyHint=True,
        ),
    )
    def topic_age_probe(
        topic: str,
        msg_type: str = "",
        window_sec: float = 10.0,
        max_samples: int = 200,
    ) -> dict:
        """Sample a topic and compute latency/rate stats."""
        if not topic or not topic.strip():
            return {"error": "topic is required"}

        topic = topic.strip()
        window_sec = max(0.5, min(float(window_sec), 120.0))
        max_samples = max(1, min(int(max_samples), 2000))

        # Auto-detect topic type if not provided
        detected_type = msg_type.strip()
        if not detected_type:
            type_resp = _call_service(
                ws_manager,
                "/rosapi/topic_type",
                "rosapi/TopicType",
                {"topic": topic},
                f"topic_age_type_{topic.replace('/', '_')}",
            )
            detected_type = type_resp.get("values", {}).get("type", "") if isinstance(type_resp, dict) else ""
            if not detected_type:
                return {
                    "error": f"Could not determine type for topic {topic}. Pass msg_type explicitly.",
                }

        subscribe_msg = {
            "op": "subscribe",
            "topic": topic,
            "type": detected_type,
            "queue_length": 1,
            "throttle_rate": 0,
        }

        receive_times: list[float] = []
        ages: list[float] = []
        with_header_stamp = 0
        status_errors: list[str] = []

        with ws_manager:
            send_err = ws_manager.send(subscribe_msg)
            if send_err:
                return {"error": f"Failed to subscribe: {send_err}"}

            deadline = time.time() + window_sec
            while time.time() < deadline and len(receive_times) < max_samples:
                raw = ws_manager.receive(timeout=0.2)
                if raw is None:
                    continue

                parsed, _ = parse_input(raw, expects_image=False)
                if not parsed:
                    continue

                if parsed.get("op") == "status" and parsed.get("level") == "error":
                    status_errors.append(parsed.get("msg", "Unknown rosbridge status error"))
                    continue

                if parsed.get("op") != "publish" or parsed.get("topic") != topic:
                    continue

                now = time.time()
                receive_times.append(now)

                msg = parsed.get("msg", {})
                stamp = _extract_stamp_seconds(msg) if isinstance(msg, dict) else None
                if stamp is not None:
                    with_header_stamp += 1
                    ages.append(now - stamp)

            ws_manager.send({"op": "unsubscribe", "topic": topic})

        sample_count = len(receive_times)
        elapsed = receive_times[-1] - receive_times[0] if sample_count >= 2 else 0.0
        hz = (sample_count - 1) / elapsed if elapsed > 0 else (1.0 / window_sec if sample_count == 1 else 0.0)

        age_sorted = sorted(ages)
        age_stats = {
            "count": len(ages),
            "with_stamp_ratio": (len(ages) / sample_count) if sample_count else 0.0,
            "min": age_sorted[0] if age_sorted else 0.0,
            "p50": _percentile(age_sorted, 0.50) if age_sorted else 0.0,
            "p95": _percentile(age_sorted, 0.95) if age_sorted else 0.0,
            "max": age_sorted[-1] if age_sorted else 0.0,
            "mean": statistics.fmean(ages) if ages else 0.0,
            "drift": (ages[-1] - ages[0]) if len(ages) >= 2 else 0.0,
        }

        return {
            "topic": topic,
            "msg_type": detected_type,
            "window_sec": window_sec,
            "sample_count": sample_count,
            "receive_hz": hz,
            "header_stamp_messages": with_header_stamp,
            "age_seconds": age_stats,
            "status_errors": status_errors,
        }

    @mcp.tool(
        description=(
            "Diagnose rosbridge lag symptoms on one topic using age/rate drift heuristics.\n"
            "Example:\nrosbridge_lag_probe('/camera/image_raw', msg_type='sensor_msgs/Image', seconds=20)"
        ),
        annotations=ToolAnnotations(
            title="Rosbridge Lag Probe",
            readOnlyHint=True,
        ),
    )
    def rosbridge_lag_probe(
        topic: str,
        msg_type: str = "",
        seconds: float = 20.0,
        max_samples: int = 400,
    ) -> dict:
        """Diagnose bridge delay symptoms from topic age drift."""
        probe = topic_age_probe(topic=topic, msg_type=msg_type, window_sec=seconds, max_samples=max_samples)
        if "error" in probe:
            return probe

        age = probe.get("age_seconds", {})
        drift = float(age.get("drift", 0.0) or 0.0)
        p95 = float(age.get("p95", 0.0) or 0.0)
        hz = float(probe.get("receive_hz", 0.0) or 0.0)

        diagnosis = _lag_diagnosis(drift, p95, hz)
        return {
            "topic": probe.get("topic"),
            "msg_type": probe.get("msg_type"),
            "sample_count": probe.get("sample_count"),
            "receive_hz": hz,
            "age_seconds": age,
            "diagnosis": diagnosis,
            "notes": [
                "A strongly increasing age drift usually indicates buffering/queue delay.",
                "Compare against direct rospy/rostopic consumers to isolate rosbridge overhead.",
            ],
            "status_errors": probe.get("status_errors", []),
        }
