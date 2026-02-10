import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import qos_profile_sensor_data, QoSProfile, ReliabilityPolicy, HistoryPolicy

from scipy.spatial.transform import Rotation as R

from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import State
from mavros_msgs.srv import CommandBool, SetMode

from drone_interfaces.action import DroneTakeoff, DroneTrajectory

import math
import time
import threading

class DroneMCPBridge(Node):
    def __init__(self):
        super().__init__('drone_mcp_bridge')
        self.callback_group = ReentrantCallbackGroup()

        setpoint_qos = QoSProfile(reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST, depth=10)
        self.local_pos_pub = self.create_publisher(PoseStamped, '/mavros/setpoint_position/local', setpoint_qos)
        self.state_sub = self.create_subscription(State, '/mavros/state', self.state_cb, 10)
        self.local_pos_sub = self.create_subscription(PoseStamped, '/mavros/local_position/pose', self.local_cb, qos_profile_sensor_data)

        self.arm_cli = self.create_client(CommandBool, '/mavros/cmd/arming', callback_group=self.callback_group)
        self.mode_cli = self.create_client(SetMode, '/mavros/set_mode', callback_group=self.callback_group)

        self._action_takeoff = ActionServer(
            self, DroneTakeoff, 'drone_control/takeoff', 
            self.execute_takeoff, callback_group=self.callback_group)

        self._action_trajectory = ActionServer(
            self, DroneTrajectory, 'drone_control/trajectory',
            self.execute_trajectory, callback_group=self.callback_group)

        self.current_state = State()
        self.current_pose = PoseStamped()
        
        self.target_pose = PoseStamped()
        self.active_pattern = None 
        self.pattern_params = {}

        self.is_primed = False

        self.timer = self.create_timer(0.05, self.timer_callback, callback_group=self.callback_group)
        self.get_logger().info('--- Stabilized Drone Bridge (Smoothed 50Hz) Online ---')

    def state_cb(self, msg): 
        self.current_state = msg

    def local_cb(self, msg):
        self.current_pose = msg
        if not self.is_primed:
            self.target_pose.pose.position.x = msg.pose.position.x
            self.target_pose.pose.position.y = msg.pose.position.y
            self.target_pose.pose.position.z = 0.0
            self.is_primed = True
            self.get_logger().info(f'Ground coordinates locked: {msg.pose.position.x:.2f}, {msg.pose.position.y:.2f}')

    def timer_callback(self):
        if not self.is_primed:
            return

        self.target_pose.header.stamp = self.get_clock().now().to_msg()
        self.target_pose.header.frame_id = "map"
        self.local_pos_pub.publish(self.target_pose)

    async def prepare_for_flight(self):
        if not self.current_state.connected:
            self.get_logger().error("FCU not connected!")
            return False
            
        if not self.is_primed:
            self.get_logger().warn("Waiting for local position lock...")
            return False

        if self.current_state.mode != "OFFBOARD":
            req = SetMode.Request(custom_mode="OFFBOARD")
            resp = await self.mode_cli.call_async(req)
            if not resp.mode_sent:
                self.get_logger().error("Failed to set OFFBOARD mode")
                return False
            time.sleep(0.5) 

        if not self.current_state.armed:
            req = CommandBool.Request(value=True)
            resp = await self.arm_cli.call_async(req)
            if not resp.success:
                self.get_logger().error("Failed to ARM")
                return False
                
        return True

    async def execute_takeoff(self, goal_handle):
        self.get_logger().info(f'Executing Takeoff to {goal_handle.request.target_altitude}m')
        
        if not await self.prepare_for_flight():
            goal_handle.abort()
            return DroneTakeoff.Result(success=False, message="Failed to arm/offboard")

        self.active_pattern = None
        self.target_pose.pose.position.x = self.current_pose.pose.position.x
        self.target_pose.pose.position.y = self.current_pose.pose.position.y
        self.target_pose.pose.position.z = goal_handle.request.target_altitude

        feedback_msg = DroneTakeoff.Feedback()
        
        while rclpy.ok():
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                return DroneTakeoff.Result(success=False, message="Canceled")

            current_z = self.current_pose.pose.position.z
            error = abs(goal_handle.request.target_altitude - current_z)
            
            feedback_msg.current_altitude = current_z
            goal_handle.publish_feedback(feedback_msg)

            if error < 0.2:
                break
                
            time.sleep(0.5)

        goal_handle.succeed()
        return DroneTakeoff.Result(success=True, message="Takeoff complete")



    async def execute_trajectory(self, goal_handle):
        req = goal_handle.request
        self.get_logger().info(f'Executing Trajectory with {len(req.points)} points. Frame={req.reference_frame}, FlyThrough={req.fly_through}')

        if not await self.prepare_for_flight():
            goal_handle.abort()
            return DroneTrajectory.Result(success=False, message="Failed to arm/offboard")

        self.active_pattern = None 
        
        # reference_frame: 0 = RELATIVE_TO_START, 1 = LOCAL_NED
        points = []
        if req.reference_frame == 0:
            start_x = self.current_pose.pose.position.x
            start_y = self.current_pose.pose.position.y
            start_z = self.current_pose.pose.position.z 
            for p in req.points:
                points.append((start_x + p.x, start_y + p.y, start_z + p.z))
        else:
            for p in req.points:
                points.append((p.x, p.y, p.z))

        loops = req.repeat if req.repeat > 0 else 1
        current_global_idx = 0
        
        feedback_msg = DroneTrajectory.Feedback()

        cycle_rate = 50.0
        dt = 1.0 / cycle_rate
        speed = req.speed if req.speed > 0.0 else 1.0

        setpoint_x = self.current_pose.pose.position.x
        setpoint_y = self.current_pose.pose.position.y
        setpoint_z = self.current_pose.pose.position.z

        for loop_idx in range(loops):
            for i, (tx, ty, tz) in enumerate(points):
                target_x, target_y, target_z = float(tx), float(ty), float(tz)
                setpoint_reached = False

                while rclpy.ok():
                    if goal_handle.is_cancel_requested:
                        goal_handle.canceled()
                        return DroneTrajectory.Result(success=False, message="Canceled")

                    dx = target_x - setpoint_x
                    dy = target_y - setpoint_y
                    dz = target_z - setpoint_z
                    dist_to_target = math.sqrt(dx*dx + dy*dy + dz*dz)

                    if dist_to_target < (speed * dt):
                        setpoint_x, setpoint_y, setpoint_z = target_x, target_y, target_z
                        setpoint_reached = True
                    else:
                        step = speed * dt
                        setpoint_x += (dx / dist_to_target) * step
                        setpoint_y += (dy / dist_to_target) * step
                        setpoint_z += (dz / dist_to_target) * step
                        
                        if abs(dx) > 0.1 or abs(dy) > 0.1:
                            yaw = math.atan2(dy, dx)
                            q = R.from_euler('z', yaw).as_quat()
                            self.target_pose.pose.orientation.x = q[0]
                            self.target_pose.pose.orientation.y = q[1]
                            self.target_pose.pose.orientation.z = q[2]
                            self.target_pose.pose.orientation.w = q[3]

                    self.target_pose.pose.position.x = setpoint_x
                    self.target_pose.pose.position.y = setpoint_y
                    self.target_pose.pose.position.z = setpoint_z
                    
                    cx = self.current_pose.pose.position.x
                    cy = self.current_pose.pose.position.y
                    cz = self.current_pose.pose.position.z

                    drone_dist_to_wp = math.sqrt((target_x-cx)**2 + (target_y-cy)**2 + (target_z-cz)**2)
                    
                    feedback_msg.current_point_index = current_global_idx
                    feedback_msg.distance_remaining = drone_dist_to_wp
                    goal_handle.publish_feedback(feedback_msg)

                    tolerance = req.tolerance
                    if tolerance <= 0.0:
                        tolerance = 0.5 if req.fly_through else 0.2

                    if req.fly_through:
                        if setpoint_reached:
                            break
                    else:
                        if setpoint_reached and drone_dist_to_wp < tolerance:
                            break 
                    
                    time.sleep(dt)
                
                if not req.fly_through:
                    time.sleep(1.0)
                
                current_global_idx += 1

        goal_handle.succeed()
        return DroneTrajectory.Result(success=True, message="Trajectory complete")

def main():
    rclpy.init()
    node = DroneMCPBridge()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()