"""Action server that drives the turtle to an absolute pose."""

from __future__ import annotations

import math
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.node import Node

from turtlesim_custom_actions.action import GoToPose
from .action_utils import (
    TurtlePoseTracker,
    normalize_angle,
    pose_distance,
    publish_stop,
    create_twist,
)


class GoToPoseActionServer(Node):
    """Simple proportional controller for turtlesim pose goals."""

    def __init__(self) -> None:
        super().__init__("goto_pose_server")
        self.pose_tracker = TurtlePoseTracker(self)
        self.cmd_pub = self.create_publisher(Twist, "/turtle1/cmd_vel", 10)
        self._server = ActionServer(
            self,
            GoToPose,
            "/turtle1/goto_pose",
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
        )

    def goal_callback(self, goal_request: GoToPose.Goal) -> GoalResponse:
        if math.isnan(goal_request.x) or math.isnan(goal_request.y):
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle) -> CancelResponse:
        self.get_logger().info("GoToPose goal canceled by client")
        return CancelResponse.ACCEPT

    def execute_callback(self, goal_handle):
        goal = goal_handle.request
        position_tolerance = goal.position_tolerance or 0.05
        angle_tolerance = goal.angle_tolerance or 0.05
        linear_speed = max(0.1, min(2.0, abs(goal.linear_speed) or 1.5))
        angular_speed = max(0.2, min(4.0, abs(goal.angular_speed) or 2.5))

        feedback = GoToPose.Feedback()
        start_pose = self.pose_tracker.wait_for_pose(timeout=5.0)
        if start_pose is None:
            goal_handle.abort()
            return self._result(False, "No turtlesim pose available", 0.0, 0.0, 0.0, 0.0, 0.0)

        last_feedback_time = time.monotonic()
        self.get_logger().info(
            f"Executing goto_pose goal to x={goal.x:.2f}, y={goal.y:.2f}, theta={goal.theta:.2f}"
        )

        while rclpy.ok():
            current_pose = self.pose_tracker.pose
            if current_pose is None:
                time.sleep(0.05)
                continue

            dx = goal.x - current_pose.x
            dy = goal.y - current_pose.y
            distance = math.hypot(dx, dy)
            heading_to_goal = math.atan2(dy, dx)
            heading_error = normalize_angle(heading_to_goal - current_pose.theta)
            final_heading_error = normalize_angle(goal.theta - current_pose.theta)

            if distance <= position_tolerance and abs(final_heading_error) <= angle_tolerance:
                break

            if goal_handle.is_cancel_requested:
                publish_stop(self, self.cmd_pub)
                goal_handle.canceled()
                return self._result(
                    False,
                    "GoToPose goal canceled",
                    current_pose.x,
                    current_pose.y,
                    current_pose.theta,
                    distance,
                    final_heading_error,
                )

            if distance > position_tolerance:
                linear = max(min(distance, linear_speed), -linear_speed)
                angular = max(min(heading_error * angular_speed, angular_speed), -angular_speed)
            else:
                linear = 0.0
                angular = max(
                    min(final_heading_error * angular_speed, angular_speed), -angular_speed
                )

            self.cmd_pub.publish(create_twist(linear, angular))

            feedback.remaining_distance = max(0.0, distance - position_tolerance)
            feedback.remaining_angle = abs(final_heading_error)
            feedback.current_x = current_pose.x
            feedback.current_y = current_pose.y
            feedback.current_theta = current_pose.theta

            if time.monotonic() - last_feedback_time >= 0.2:
                goal_handle.publish_feedback(feedback)
                last_feedback_time = time.monotonic()

            time.sleep(0.05)

        publish_stop(self, self.cmd_pub)
        final_pose = self.pose_tracker.pose or start_pose
        goal_handle.succeed()
        final_dx = goal.x - final_pose.x
        final_dy = goal.y - final_pose.y
        return self._result(
            True,
            "Reached requested pose",
            final_pose.x,
            final_pose.y,
            final_pose.theta,
            math.hypot(final_dx, final_dy),
            normalize_angle(goal.theta - final_pose.theta),
        )

    def _result(
        self,
        success: bool,
        message: str,
        x: float,
        y: float,
        theta: float,
        distance_error: float,
        angle_error: float,
    ):
        result = GoToPose.Result()
        result.success = success
        result.message = message
        result.final_x = float(x)
        result.final_y = float(y)
        result.final_theta = float(theta)
        result.error_distance = float(distance_error)
        result.error_theta = float(angle_error)
        return result


def main(args=None):
    rclpy.init(args=args)
    node = GoToPoseActionServer()
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
