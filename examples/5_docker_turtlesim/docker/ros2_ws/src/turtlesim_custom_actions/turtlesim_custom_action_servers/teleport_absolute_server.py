"""Action server exposing turtlesim's teleport_absolute as an action."""

from __future__ import annotations

import math
import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.node import Node
from std_srvs.srv import Empty
from turtlesim.srv import TeleportAbsolute as TeleportAbsoluteSrv

from turtlesim_custom_actions.action import TeleportAbsolute
from .action_utils import TurtlePoseTracker


class TeleportAbsoluteActionServer(Node):
    def __init__(self) -> None:
        super().__init__("teleport_absolute_server")
        self.pose_tracker = TurtlePoseTracker(self)
        self._teleport_cli = self.create_client(TeleportAbsoluteSrv, "/turtle1/teleport_absolute")
        self._clear_cli = self.create_client(Empty, "/clear")
        self._server = ActionServer(
            self,
            TeleportAbsolute,
            "/turtle1/teleport_absolute",
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
        )

    def goal_callback(self, goal_request: TeleportAbsolute.Goal) -> GoalResponse:
        if any(map(math.isnan, (goal_request.x, goal_request.y, goal_request.theta))):
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle) -> CancelResponse:
        # Teleport happens instantly; nothing to cancel.
        return CancelResponse.REJECT

    def execute_callback(self, goal_handle):
        goal = goal_handle.request
        self._wait_for_service(self._teleport_cli, "TeleportAbsolute")

        request = TeleportAbsoluteSrv.Request()
        request.x = goal.x
        request.y = goal.y
        request.theta = goal.theta

        goal_handle.publish_feedback(self._feedback("teleporting"))
        future = self._teleport_cli.call_async(request)
        self._wait_for_future(future)

        if goal.clear_background:
            self._wait_for_service(self._clear_cli, "clear")
            goal_handle.publish_feedback(self._feedback("clearing"))
            clear_future = self._clear_cli.call_async(Empty.Request())
            self._wait_for_future(clear_future)

        final_pose = self.pose_tracker.wait_for_pose(timeout=2.0)

        result = TeleportAbsolute.Result()
        result.success = True
        result.message = "Teleport completed"
        if final_pose:
            result.final_x = final_pose.x
            result.final_y = final_pose.y
            result.final_theta = final_pose.theta

        goal_handle.succeed()
        return result

    def _wait_for_service(self, client, name: str) -> None:
        while not client.wait_for_service(timeout_sec=0.5):
            self.get_logger().warn(f"Waiting for {name} service...")
            time.sleep(0.1)

    def _wait_for_future(self, future) -> None:
        while rclpy.ok() and not future.done():
            rclpy.spin_once(self, timeout_sec=0.1)

    def _feedback(self, phase: str) -> TeleportAbsolute.Feedback:
        feedback = TeleportAbsolute.Feedback()
        feedback.phase = phase
        return feedback


def main(args=None):
    rclpy.init(args=args)
    node = TeleportAbsoluteActionServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
