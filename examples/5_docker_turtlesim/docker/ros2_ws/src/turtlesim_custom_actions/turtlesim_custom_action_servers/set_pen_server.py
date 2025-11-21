"""Action server wrapping turtlesim's SetPen service."""

from __future__ import annotations

import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.node import Node
from std_srvs.srv import Empty
from turtlesim.srv import SetPen as SetPenSrv

from turtlesim_custom_actions.action import SetPen


class SetPenActionServer(Node):
    def __init__(self) -> None:
        super().__init__("set_pen_server")
        self._set_pen_cli = self.create_client(SetPenSrv, "/turtle1/set_pen")
        self._clear_cli = self.create_client(Empty, "/clear")
        self._server = ActionServer(
            self,
            SetPen,
            "/turtle1/set_pen",
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
        )

    def goal_callback(self, goal_request: SetPen.Goal) -> GoalResponse:
        if goal_request.width == 0 and goal_request.pen_on:
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle) -> CancelResponse:
        # Execution is quick, so cancellation is effectively immediate.
        return CancelResponse.ACCEPT

    def execute_callback(self, goal_handle):
        goal = goal_handle.request
        self._wait_for_service(self._set_pen_cli, "SetPen")

        request = SetPenSrv.Request()
        request.r = goal.r
        request.g = goal.g
        request.b = goal.b
        request.width = goal.width
        request.off = not goal.pen_on

        future = self._set_pen_cli.call_async(request)
        self._wait_for_future(future)

        feedback = SetPen.Feedback()
        feedback.state = (
            f"pen={'on' if goal.pen_on else 'off'} rgb=({goal.r},{goal.g},{goal.b}) width={goal.width}"
        )
        goal_handle.publish_feedback(feedback)

        # Optional nicety: if pen is being turned back on, clear the board first.
        if goal.pen_on and self._clear_cli.service_is_ready():
            clear_future = self._clear_cli.call_async(Empty.Request())
            self._wait_for_future(clear_future)

        result = SetPen.Result()
        result.success = True
        result.message = "Updated turtlesim pen settings"

        goal_handle.succeed()
        return result

    def _wait_for_service(self, client, name: str) -> None:
        while not client.wait_for_service(timeout_sec=0.5):
            self.get_logger().warn(f"Waiting for {name} service...")
            time.sleep(0.1)

    def _wait_for_future(self, future) -> None:
        while rclpy.ok() and not future.done():
            rclpy.spin_once(self, timeout_sec=0.1)


def main(args=None):
    rclpy.init(args=args)
    node = SetPenActionServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
