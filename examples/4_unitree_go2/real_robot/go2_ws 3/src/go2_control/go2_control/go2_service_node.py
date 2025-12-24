"""
Go2 ROS 2 Service Node
======================
Exposes all Go2 robot capabilities as individual ROS 2 services.

Custom service types from go2_interfaces:
- Trigger  : Simple actions (no input)
- SetBool  : Enable/disable features
- Move     : Movement with velocity + distance
- SetFloat : Float parameter setting
- SetInt   : Integer parameter setting

SERVICES PROVIDED:
==================

POSTURE SERVICES (Trigger):
    /go2/damp          - Emergency stop, enter damping state (highest priority)
    /go2/balance       - Enter balance stand mode
    /go2/stop          - Stop current action, restore defaults
    /go2/stand_up      - Stand up (high stance, 0.33m)
    /go2/stand_down    - Lie down (low stance)
    /go2/recovery      - Recovery stand (use after falls)
    /go2/sit           - Sit down (special action)
    /go2/rise_sit      - Stand up from sitting

MOVEMENT SERVICE (Move):
    /go2/move          - Move robot with velocity and distance control
                         Input: vx (m/s), vy (m/s), vyaw (rad/s), distance (m or rad)
                         Note: Automatically enters walking mode if needed

BODY CONFIGURATION SERVICES:
    /go2/euler         - Set body posture (roll, pitch, yaw in radians)
    /go2/body_height   - Set body height relative to default (SetFloat, range: -0.18 to 0.03m)
    /go2/foot_raise_height - Set foot raise height relative to default (SetFloat, range: -0.06 to 0.03m)
    /go2/speed_level   - Set speed range (SetInt: -1=slow, 0=normal, 1=fast)
    /go2/switch_gait   - Switch gait (SetInt: 0=idle, 1=trot, 2=trot running, 3=forward climb, 4=reverse climb)

TOGGLE SERVICES (SetBool):
    /go2/switch_joystick  - Enable/disable native remote control response
    /go2/continuous_gait  - Enable/disable continuous gait mode
    /go2/handstand        - Enable/disable handstand
    /go2/walk_upright     - Enable/disable upright walking
    /go2/free_avoid       - Enable/disable obstacle avoidance
    /go2/free_bound       - Enable/disable bounding gait
    /go2/cross_step       - Enable/disable cross-step walking
    /go2/free_jump        - Enable/disable jumping

GESTURE / TRICK SERVICES (Trigger):
    /go2/hello         - Say hello (wave)
    /go2/stretch       - Stretch
    /go2/wallow        - Roll over
    /go2/pose_on       - Strike a pose
    /go2/pose_off      - Exit pose
    /go2/scrape        - New Year greeting
    /go2/front_flip    - Front flip
    /go2/front_jump    - Jump forward
    /go2/front_pounce  - Pounce forward
    /go2/left_flip     - Left flip
    /go2/back_flip     - Back flip
    /go2/dance1        - Dance routine 1
    /go2/dance2        - Dance routine 2

EXAMPLE SERVICE CALLS (for LLM reference):
==========================================

# Stand up
ros2 service call /go2/stand_up go2_interfaces/srv/Trigger

# Move forward 2 meters at 0.3 m/s
ros2 service call /go2/move go2_interfaces/srv/Move "{vx: 0.3, vy: 0.0, vyaw: 0.0, distance: 2.0}"

# Turn left 90 degrees (1.57 radians) at 0.5 rad/s
ros2 service call /go2/move go2_interfaces/srv/Move "{vx: 0.0, vy: 0.0, vyaw: 0.5, distance: 1.57}"

# Say hello
ros2 service call /go2/hello go2_interfaces/srv/Trigger

# Do a dance
ros2 service call /go2/dance1 go2_interfaces/srv/Trigger

# Set body height lower by 0.1m
ros2 service call /go2/body_height go2_interfaces/srv/SetFloat "{value: -0.1}"

# Set speed to fast
ros2 service call /go2/speed_level go2_interfaces/srv/SetInt "{value: 1}"
"""

import math
from multiprocessing import Process, Queue

import rclpy
from go2_interfaces.srv import Move, SetBool, SetFloat, SetInt, Trigger
from rclpy.node import Node

from go2_control.go2_backend import backend_loop

# ============================================================
# CONFIGURATION CONSTANTS
# ============================================================

MOVE_INTERVAL = 0.5  # seconds between Move() calls

# Velocity limits from SDK documentation
MAX_VX = 2.5       # m/s (can go up to 3.8 forward)
MAX_VY = 1.0       # m/s
MAX_VYAW = 4.0     # rad/s


def calculate_iterations(distance: float, velocity: float, interval: float = MOVE_INTERVAL) -> int:
    """
    Calculate the number of move iterations needed to cover a distance.
    
    Formula:
        distance_per_call = velocity × interval
        iterations = ceil(distance / distance_per_call)
    
    Args:
        distance: Target distance in meters (or radians for rotation)
        velocity: Movement velocity in m/s (or rad/s for rotation)
        interval: Time between Move() calls (default 0.5s)
    
    Returns:
        Number of iterations (minimum 1)
    """
    if abs(velocity) < 0.001:
        return 1
    
    distance_per_call = abs(velocity) * interval
    iterations = math.ceil(abs(distance) / distance_per_call)
    return max(1, iterations)


class Go2ServiceNode(Node):
    """
    ROS 2 Node providing services for Go2 robot control.
    """
    
    def __init__(self, cmd_queue: Queue):
        super().__init__("go2_services")
        self.queue = cmd_queue
        
        # ============================================================
        # POSTURE SERVICES (Trigger type)
        # ============================================================
        
        self.create_service(Trigger, "/go2/damp", self.cb_damp)
        self.create_service(Trigger, "/go2/balance", self.cb_balance)
        self.create_service(Trigger, "/go2/stop", self.cb_stop)
        self.create_service(Trigger, "/go2/stand_up", self.cb_stand_up)
        self.create_service(Trigger, "/go2/stand_down", self.cb_stand_down)
        self.create_service(Trigger, "/go2/recovery", self.cb_recovery)
        self.create_service(Trigger, "/go2/sit", self.cb_sit)
        self.create_service(Trigger, "/go2/rise_sit", self.cb_rise_sit)
        
        # ============================================================
        # MOVEMENT SERVICE (Move type)
        # ============================================================
        
        self.create_service(Move, "/go2/move", self.cb_move)
        
        # ============================================================
        # BODY CONFIGURATION SERVICES
        # ============================================================
        
        self.create_service(SetFloat, "/go2/body_height", self.cb_body_height)
        self.create_service(SetFloat, "/go2/foot_raise_height", self.cb_foot_raise_height)
        self.create_service(SetInt, "/go2/speed_level", self.cb_speed_level)
        self.create_service(SetInt, "/go2/switch_gait", self.cb_switch_gait)
        
        # ============================================================
        # TOGGLE SERVICES (SetBool type)
        # ============================================================
        
        self.create_service(SetBool, "/go2/switch_joystick", self.cb_switch_joystick)
        self.create_service(SetBool, "/go2/continuous_gait", self.cb_continuous_gait)
        self.create_service(SetBool, "/go2/handstand", self.cb_handstand)
        self.create_service(SetBool, "/go2/walk_upright", self.cb_walk_upright)
        self.create_service(SetBool, "/go2/free_avoid", self.cb_free_avoid)
        self.create_service(SetBool, "/go2/free_bound", self.cb_free_bound)
        self.create_service(SetBool, "/go2/cross_step", self.cb_cross_step)
        self.create_service(SetBool, "/go2/free_jump", self.cb_free_jump)
        
        # ============================================================
        # GESTURE / TRICK SERVICES (Trigger type)
        # ============================================================
        
        self.create_service(Trigger, "/go2/hello", self.cb_hello)
        self.create_service(Trigger, "/go2/stretch", self.cb_stretch)
        self.create_service(Trigger, "/go2/wallow", self.cb_wallow)
        self.create_service(Trigger, "/go2/pose_on", self.cb_pose_on)
        self.create_service(Trigger, "/go2/pose_off", self.cb_pose_off)
        self.create_service(Trigger, "/go2/scrape", self.cb_scrape)
        self.create_service(Trigger, "/go2/front_flip", self.cb_front_flip)
        self.create_service(Trigger, "/go2/front_jump", self.cb_front_jump)
        self.create_service(Trigger, "/go2/front_pounce", self.cb_front_pounce)
        self.create_service(Trigger, "/go2/left_flip", self.cb_left_flip)
        self.create_service(Trigger, "/go2/back_flip", self.cb_back_flip)
        self.create_service(Trigger, "/go2/dance1", self.cb_dance1)
        self.create_service(Trigger, "/go2/dance2", self.cb_dance2)
        
        # ============================================================
        # LOG AVAILABLE SERVICES
        # ============================================================
        
        self.get_logger().info("=" * 65)
        self.get_logger().info("Go2 ROS 2 Services Ready!")
        self.get_logger().info("=" * 65)
        self.get_logger().info("")
        self.get_logger().info("POSTURE (Trigger):")
        self.get_logger().info("  /go2/damp, /go2/balance, /go2/stop, /go2/stand_up")
        self.get_logger().info("  /go2/stand_down, /go2/recovery, /go2/sit, /go2/rise_sit")
        self.get_logger().info("")
        self.get_logger().info("MOVEMENT (Move):")
        self.get_logger().info("  /go2/move - Args: vx, vy, vyaw, distance")
        self.get_logger().info("")
        self.get_logger().info("BODY CONFIG:")
        self.get_logger().info("  /go2/body_height (SetFloat), /go2/foot_raise_height (SetFloat)")
        self.get_logger().info("  /go2/speed_level (SetInt), /go2/switch_gait (SetInt)")
        self.get_logger().info("")
        self.get_logger().info("TOGGLES (SetBool):")
        self.get_logger().info("  /go2/switch_joystick, /go2/continuous_gait, /go2/handstand")
        self.get_logger().info("  /go2/walk_upright, /go2/free_avoid, /go2/free_bound")
        self.get_logger().info("  /go2/cross_step, /go2/free_jump")
        self.get_logger().info("")
        self.get_logger().info("GESTURES/TRICKS (Trigger):")
        self.get_logger().info("  /go2/hello, /go2/stretch, /go2/wallow, /go2/pose_on, /go2/pose_off")
        self.get_logger().info("  /go2/scrape, /go2/front_flip, /go2/front_jump, /go2/front_pounce")
        self.get_logger().info("  /go2/left_flip, /go2/back_flip, /go2/dance1, /go2/dance2")
        self.get_logger().info("=" * 65)
    
    # ================================================================
    # POSTURE SERVICE CALLBACKS
    # ================================================================
    
    def cb_damp(self, request, response):
        """Emergency stop - enter damping state."""
        self.queue.put({"type": "damp"})
        response.success = True
        response.message = "Damp command sent (emergency stop)"
        self.get_logger().info("Service: /go2/damp")
        return response
    
    def cb_balance(self, request, response):
        """Enter balance stand mode."""
        self.queue.put({"type": "balance"})
        response.success = True
        response.message = "Balance stand command sent"
        self.get_logger().info("Service: /go2/balance")
        return response
    
    def cb_stop(self, request, response):
        """Stop current action and restore defaults."""
        self.queue.put({"type": "stop"})
        response.success = True
        response.message = "Stop command sent"
        self.get_logger().info("Service: /go2/stop")
        return response
    
    def cb_stand_up(self, request, response):
        """Stand up to high stance."""
        self.queue.put({"type": "stand_up"})
        response.success = True
        response.message = "Stand up command sent"
        self.get_logger().info("Service: /go2/stand_up")
        return response
    
    def cb_stand_down(self, request, response):
        """Lie down to low stance."""
        self.queue.put({"type": "stand_down"})
        response.success = True
        response.message = "Stand down command sent"
        self.get_logger().info("Service: /go2/stand_down")
        return response
    
    def cb_recovery(self, request, response):
        """Recovery stand from fallen state."""
        self.queue.put({"type": "recovery"})
        response.success = True
        response.message = "Recovery stand command sent"
        self.get_logger().info("Service: /go2/recovery")
        return response
    
    def cb_sit(self, request, response):
        """Sit down."""
        self.queue.put({"type": "sit"})
        response.success = True
        response.message = "Sit command sent"
        self.get_logger().info("Service: /go2/sit")
        return response
    
    def cb_rise_sit(self, request, response):
        """Stand up from sitting."""
        self.queue.put({"type": "rise_sit"})
        response.success = True
        response.message = "Rise from sit command sent"
        self.get_logger().info("Service: /go2/rise_sit")
        return response
    
    # ================================================================
    # MOVEMENT SERVICE CALLBACK
    # ================================================================
    
    def cb_move(self, request, response):
        """
        Execute a movement with specified velocities and distance.
        Automatically enters walking mode if needed.
        """
        vx = request.vx
        vy = request.vy
        vyaw = request.vyaw
        distance = request.distance
        
        # Validate inputs
        if distance <= 0:
            response.success = False
            response.message = "Distance must be positive"
            response.estimated_time = 0.0
            response.iterations = 0
            return response
        
        # Clamp velocities to safe limits
        vx = max(-MAX_VX, min(MAX_VX, vx))
        vy = max(-MAX_VY, min(MAX_VY, vy))
        vyaw = max(-MAX_VYAW, min(MAX_VYAW, vyaw))
        
        # Calculate iterations based on dominant motion
        abs_vx = abs(vx)
        abs_vy = abs(vy)
        abs_vyaw = abs(vyaw)
        
        if abs_vx >= abs_vy and abs_vx >= abs_vyaw and abs_vx > 0.001:
            iterations = calculate_iterations(distance, abs_vx)
            motion_type = "forward" if vx > 0 else "backward"
        elif abs_vy >= abs_vx and abs_vy >= abs_vyaw and abs_vy > 0.001:
            iterations = calculate_iterations(distance, abs_vy)
            motion_type = "left" if vy > 0 else "right"
        elif abs_vyaw > 0.001:
            iterations = calculate_iterations(distance, abs_vyaw)
            degrees = math.degrees(distance)
            motion_type = f"rotate {'left' if vyaw > 0 else 'right'} {degrees:.1f}°"
        else:
            response.success = False
            response.message = "At least one velocity component must be non-zero"
            response.estimated_time = 0.0
            response.iterations = 0
            return response
        
        estimated_time = iterations * MOVE_INTERVAL
        
        self.queue.put({
            "type": "move",
            "vx": vx,
            "vy": vy,
            "wz": vyaw,
            "iterations": iterations
        })
        
        response.success = True
        response.message = (
            f"Moving {motion_type}: vx={vx:.2f}m/s, vy={vy:.2f}m/s, "
            f"vyaw={vyaw:.2f}rad/s, distance={distance:.2f}, "
            f"iterations={iterations}, time≈{estimated_time:.1f}s"
        )
        response.estimated_time = estimated_time
        response.iterations = iterations
        
        self.get_logger().info(f"Service: /go2/move - {response.message}")
        return response
    
    # ================================================================
    # BODY CONFIGURATION CALLBACKS
    # ================================================================
    
    def cb_body_height(self, request, response):
        """Set body height relative to default (range: -0.18 to 0.03m)."""
        height = max(-0.18, min(0.03, request.value))
        self.queue.put({"type": "body_height", "height": height})
        response.success = True
        response.message = f"Body height set to {height:.3f}m (relative to default 0.33m)"
        self.get_logger().info(f"Service: /go2/body_height value={height}")
        return response
    
    def cb_foot_raise_height(self, request, response):
        """Set foot raise height relative to default (range: -0.06 to 0.03m)."""
        height = max(-0.06, min(0.03, request.value))
        self.queue.put({"type": "foot_raise_height", "height": height})
        response.success = True
        response.message = f"Foot raise height set to {height:.3f}m (relative to default 0.09m)"
        self.get_logger().info(f"Service: /go2/foot_raise_height value={height}")
        return response
    
    def cb_speed_level(self, request, response):
        """Set speed level (-1=slow, 0=normal, 1=fast)."""
        level = max(-1, min(1, request.value))
        self.queue.put({"type": "speed_level", "level": level})
        level_names = {-1: "slow", 0: "normal", 1: "fast"}
        response.success = True
        response.message = f"Speed level set to {level} ({level_names.get(level, 'unknown')})"
        self.get_logger().info(f"Service: /go2/speed_level value={level}")
        return response
    
    def cb_switch_gait(self, request, response):
        """Switch gait (0=idle, 1=trot, 2=trot running, 3=forward climb, 4=reverse climb)."""
        gait = max(0, min(4, request.value))
        self.queue.put({"type": "switch_gait", "gait": gait})
        gait_names = {0: "idle", 1: "trot", 2: "trot running", 3: "forward climb", 4: "reverse climb"}
        response.success = True
        response.message = f"Gait switched to {gait} ({gait_names.get(gait, 'unknown')})"
        self.get_logger().info(f"Service: /go2/switch_gait value={gait}")
        return response
    
    # ================================================================
    # TOGGLE SERVICE CALLBACKS
    # ================================================================
    
    def cb_switch_joystick(self, request, response):
        """Enable/disable native remote control response."""
        self.queue.put({"type": "switch_joystick", "enable": request.enable})
        response.success = True
        response.message = f"Joystick response {'enabled' if request.enable else 'disabled'}"
        self.get_logger().info(f"Service: /go2/switch_joystick enable={request.enable}")
        return response
    
    def cb_continuous_gait(self, request, response):
        """Enable/disable continuous gait mode."""
        self.queue.put({"type": "continuous_gait", "enable": request.enable})
        response.success = True
        response.message = f"Continuous gait {'enabled' if request.enable else 'disabled'}"
        self.get_logger().info(f"Service: /go2/continuous_gait enable={request.enable}")
        return response
    
    def cb_handstand(self, request, response):
        """Enable/disable handstand mode."""
        self.queue.put({"type": "handstand", "enable": request.enable})
        response.success = True
        response.message = f"Handstand {'enabled' if request.enable else 'disabled'}"
        self.get_logger().info(f"Service: /go2/handstand enable={request.enable}")
        return response
    
    def cb_walk_upright(self, request, response):
        """Enable/disable upright walking mode."""
        self.queue.put({"type": "walk_upright", "enable": request.enable})
        response.success = True
        response.message = f"Walk upright {'enabled' if request.enable else 'disabled'}"
        self.get_logger().info(f"Service: /go2/walk_upright enable={request.enable}")
        return response
    
    def cb_free_avoid(self, request, response):
        """Enable/disable obstacle avoidance."""
        self.queue.put({"type": "free_avoid", "enable": request.enable})
        response.success = True
        response.message = f"Obstacle avoidance {'enabled' if request.enable else 'disabled'}"
        self.get_logger().info(f"Service: /go2/free_avoid enable={request.enable}")
        return response
    
    def cb_free_bound(self, request, response):
        """Enable/disable bounding gait."""
        self.queue.put({"type": "free_bound", "enable": request.enable})
        response.success = True
        response.message = f"Bounding gait {'enabled' if request.enable else 'disabled'}"
        self.get_logger().info(f"Service: /go2/free_bound enable={request.enable}")
        return response
    
    def cb_cross_step(self, request, response):
        """Enable/disable cross-step walking."""
        self.queue.put({"type": "cross_step", "enable": request.enable})
        response.success = True
        response.message = f"Cross-step {'enabled' if request.enable else 'disabled'}"
        self.get_logger().info(f"Service: /go2/cross_step enable={request.enable}")
        return response
    
    def cb_free_jump(self, request, response):
        """Enable/disable jumping capability."""
        self.queue.put({"type": "free_jump", "enable": request.enable})
        response.success = True
        response.message = f"Jumping {'enabled' if request.enable else 'disabled'}"
        self.get_logger().info(f"Service: /go2/free_jump enable={request.enable}")
        return response
    
    # ================================================================
    # GESTURE / TRICK SERVICE CALLBACKS
    # ================================================================
    
    def cb_hello(self, request, response):
        """Say hello (wave gesture)."""
        self.queue.put({"type": "hello"})
        response.success = True
        response.message = "Hello gesture command sent"
        self.get_logger().info("Service: /go2/hello")
        return response
    
    def cb_stretch(self, request, response):
        """Perform stretch."""
        self.queue.put({"type": "stretch"})
        response.success = True
        response.message = "Stretch command sent"
        self.get_logger().info("Service: /go2/stretch")
        return response
    
    def cb_wallow(self, request, response):
        """Roll over."""
        self.queue.put({"type": "wallow"})
        response.success = True
        response.message = "Wallow (roll) command sent"
        self.get_logger().info("Service: /go2/wallow")
        return response
    
    def cb_pose_on(self, request, response):
        """Strike a pose."""
        self.queue.put({"type": "pose", "enable": True})
        response.success = True
        response.message = "Pose on command sent"
        self.get_logger().info("Service: /go2/pose_on")
        return response
    
    def cb_pose_off(self, request, response):
        """Exit pose."""
        self.queue.put({"type": "pose", "enable": False})
        response.success = True
        response.message = "Pose off command sent"
        self.get_logger().info("Service: /go2/pose_off")
        return response
    
    def cb_scrape(self, request, response):
        """New Year greeting gesture."""
        self.queue.put({"type": "scrape"})
        response.success = True
        response.message = "Scrape (New Year greeting) command sent"
        self.get_logger().info("Service: /go2/scrape")
        return response
    
    def cb_front_flip(self, request, response):
        """Perform front flip."""
        self.queue.put({"type": "front_flip"})
        response.success = True
        response.message = "Front flip command sent"
        self.get_logger().info("Service: /go2/front_flip")
        return response
    
    def cb_front_jump(self, request, response):
        """Jump forward."""
        self.queue.put({"type": "front_jump"})
        response.success = True
        response.message = "Front jump command sent"
        self.get_logger().info("Service: /go2/front_jump")
        return response
    
    def cb_front_pounce(self, request, response):
        """Pounce forward."""
        self.queue.put({"type": "front_pounce"})
        response.success = True
        response.message = "Front pounce command sent"
        self.get_logger().info("Service: /go2/front_pounce")
        return response
    
    def cb_left_flip(self, request, response):
        """Perform left flip."""
        self.queue.put({"type": "left_flip"})
        response.success = True
        response.message = "Left flip command sent"
        self.get_logger().info("Service: /go2/left_flip")
        return response
    
    def cb_back_flip(self, request, response):
        """Perform back flip."""
        self.queue.put({"type": "back_flip"})
        response.success = True
        response.message = "Back flip command sent"
        self.get_logger().info("Service: /go2/back_flip")
        return response
    
    def cb_dance1(self, request, response):
        """Perform dance routine 1."""
        self.queue.put({"type": "dance1"})
        response.success = True
        response.message = "Dance 1 command sent"
        self.get_logger().info("Service: /go2/dance1")
        return response
    
    def cb_dance2(self, request, response):
        """Perform dance routine 2."""
        self.queue.put({"type": "dance2"})
        response.success = True
        response.message = "Dance 2 command sent"
        self.get_logger().info("Service: /go2/dance2")
        return response


def main(args=None):
    """
    Main entry point.
    Starts the backend process and ROS 2 service node.
    """
    cmd_queue = Queue()
    
    backend = Process(target=backend_loop, args=(cmd_queue,), daemon=True)
    backend.start()
    
    rclpy.init(args=args)
    node = Go2ServiceNode(cmd_queue)
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down...")
    finally:
        cmd_queue.put(None)
        node.destroy_node()
        rclpy.shutdown()
        backend.join(timeout=2.0)
        if backend.is_alive():
            backend.terminate()


if __name__ == "__main__":
    main()
