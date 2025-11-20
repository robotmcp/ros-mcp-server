"""Shared helpers for the turtlesim action servers."""

from __future__ import annotations

import math
import threading
import time
from typing import Optional

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from turtlesim.msg import Pose


class TurtlePoseTracker:
    """Caches /turtle1/pose updates so action servers can compute progress."""

    def __init__(self, node: Node, pose_topic: str = "/turtle1/pose") -> None:
        self._node = node
        self._pose_topic = pose_topic
        self._pose_lock = threading.Lock()
        self._pose: Optional[Pose] = None
        self._subscription = node.create_subscription(
            Pose, pose_topic, self._pose_callback, 10
        )

    def _pose_callback(self, pose: Pose) -> None:
        with self._pose_lock:
            self._pose = pose

    @property
    def pose(self) -> Optional[Pose]:
        with self._pose_lock:
            return self._pose

    def wait_for_pose(self, timeout: float = 5.0) -> Optional[Pose]:
        """Block until a pose is received or timeout expires."""
        end_time = time.monotonic() + timeout
        while rclpy.ok() and time.monotonic() < end_time:
            current_pose = self.pose
            if current_pose is not None:
                return current_pose
            time.sleep(0.05)
        return self.pose


def normalize_angle(theta: float) -> float:
    """Wrap an angle to [-pi, pi]."""
    return math.atan2(math.sin(theta), math.cos(theta))


def pose_distance(a: Pose, b: Pose) -> float:
    """Euclidean distance between two turtlesim poses."""
    return math.hypot(a.x - b.x, a.y - b.y)


def publish_stop(node: Node, publisher) -> None:
    """Send a zero twist to make sure the turtle stops moving."""
    twist = Twist()
    publisher.publish(twist)
    # Publish twice to counteract queueing latency
    node.get_logger().debug("Sent zero twist to stop turtle")
    publisher.publish(twist)


def create_twist(linear: float, angular: float) -> Twist:
    twist = Twist()
    twist.linear.x = float(linear)
    twist.angular.z = float(angular)
    return twist
