"""Convenience entry point that spins up all turtlesim action servers."""

from __future__ import annotations

import contextlib

import rclpy
from rclpy.executors import MultiThreadedExecutor

from .drive_distance_server import DriveDistanceActionServer
from .goto_pose_server import GoToPoseActionServer
from .set_pen_server import SetPenActionServer
from .teleport_absolute_server import TeleportAbsoluteActionServer


def main(args=None):
    rclpy.init(args=args)

    nodes = [
        DriveDistanceActionServer(),
        GoToPoseActionServer(),
        SetPenActionServer(),
        TeleportAbsoluteActionServer(),
    ]

    executor = MultiThreadedExecutor()
    for node in nodes:
        executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        for node in nodes:
            executor.remove_node(node)
            with contextlib.suppress(Exception):
                node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
