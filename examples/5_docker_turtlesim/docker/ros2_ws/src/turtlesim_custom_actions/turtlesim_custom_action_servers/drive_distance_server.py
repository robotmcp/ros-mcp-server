"""Action server that drives the turtle forward/backward by a relative distance."""

from __future__ import annotations

import asyncio
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.node import Node

from turtlesim_custom_actions.action import DriveDistance
from .action_utils import TurtlePoseTracker, pose_distance, publish_stop, create_twist


class DriveDistanceActionServer(Node):
    """Implements the DriveDistance action."""

    def __init__(self) -> None:
        super().__init__("drive_distance_server")
        self.pose_tracker = TurtlePoseTracker(self)
        self.cmd_pub = self.create_publisher(Twist, "/turtle1/cmd_vel", 10)
        self._server = ActionServer(
            self,
            DriveDistance,
            "/turtle1/drive_distance",
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
        )

    def goal_callback(self, goal_request: DriveDistance.Goal) -> GoalResponse:
        if abs(goal_request.distance) < 1e-3:
            self.get_logger().warning("Rejected goal with negligible distance request")
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle) -> CancelResponse:
        self.get_logger().info("Received request to cancel DriveDistance goal")
        return CancelResponse.ACCEPT

    async def execute_callback(self, goal_handle):
        goal = goal_handle.request
        target_distance = abs(goal.distance)
        direction = 1.0 if goal.distance >= 0 else -1.0
        commanded_speed = abs(goal.speed) if abs(goal.speed) > 1e-3 else 1.0
        commanded_speed = max(0.1, min(2.0, commanded_speed)) * direction

        feedback = DriveDistance.Feedback()
        start_pose = self.pose_tracker.wait_for_pose(timeout=5.0)
        if start_pose is None:
            goal_handle.abort()
            return self._result(False, "No turtlesim pose available", 0.0, 0.0, 0.0)

        self.get_logger().info(f"Driving turtle for {goal.distance:.2f} meters")
        loop_hz = 20.0
        loop_period = 1.0 / loop_hz
        last_feedback_time = time.monotonic()

        while rclpy.ok():
            current_pose = self.pose_tracker.pose
            if current_pose is None:
                await asyncio.sleep(0.05)
                continue

            traveled = pose_distance(start_pose, current_pose)
            remaining = max(0.0, target_distance - traveled)

            feedback.remaining_distance = remaining
            feedback.traveled_distance = traveled
            feedback.current_x = current_pose.x
            feedback.current_y = current_pose.y
            feedback.current_theta = current_pose.theta

            if time.monotonic() - last_feedback_time >= 0.25:
                goal_handle.publish_feedback(feedback)
                last_feedback_time = time.monotonic()

            if traveled >= target_distance:
                break

            if goal_handle.is_cancel_requested:
                publish_stop(self, self.cmd_pub)
                goal_handle.canceled()
                return self._result(
                    False,
                    "DriveDistance goal canceled",
                    current_pose.x,
                    current_pose.y,
                    current_pose.theta,
                )

            self.cmd_pub.publish(create_twist(commanded_speed, 0.0))
            await asyncio.sleep(loop_period)

        publish_stop(self, self.cmd_pub)
        final_pose = self.pose_tracker.pose or start_pose
        goal_handle.succeed()
        return self._result(
            True,
            "DriveDistance completed",
            final_pose.x,
            final_pose.y,
            final_pose.theta,
        )

    def _result(self, success: bool, message: str, x: float, y: float, theta: float):
        result = DriveDistance.Result()
        result.success = success
        result.message = message
        result.final_x = float(x)
        result.final_y = float(y)
        result.final_theta = float(theta)
        return result


def main(args=None):
    rclpy.init(args=args)
    node = DriveDistanceActionServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        publish_stop(node, node.cmd_pub)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
