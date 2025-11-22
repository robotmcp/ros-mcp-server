from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from launch import LaunchDescription


def generate_launch_description():
    """Generate the launch description for Gazebo, Bridge, Rosbridge AND Rosapi."""

    # 1. Define the World Source
    world_file = "tugbot_depot.sdf"

    # 2. Start Ignition Gazebo Server
    gazebo_sim = ExecuteProcess(cmd=["ign", "gazebo", "-r", world_file], output="screen")

    # 3. The Bridge
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            "/model/tugbot/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist",
            "/model/tugbot/odometry@nav_msgs/msg/Odometry[ignition.msgs.Odometry",
            "/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan",
            "/model/tugbot/tf@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V",
            "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock",
        ],
        remappings=[
            ("/model/tugbot/cmd_vel", "/cmd_vel"),
            ("/model/tugbot/odometry", "/odom"),
            ("/model/tugbot/tf", "/tf"),
        ],
        output="screen",
    )

    # 4. Rosbridge Arguments
    port_arg = DeclareLaunchArgument(
        "port", default_value="9090", description="Port for rosbridge websocket server"
    )

    # 5. Rosbridge Node (The Connection)
    rosbridge_node = Node(
        package="rosbridge_server",
        executable="rosbridge_websocket",
        name="rosbridge_websocket",
        output="screen",
        parameters=[{"port": LaunchConfiguration("port")}],
    )

    # 6. ROSAPI Node (The Introspection - MISSING PART)
    # This node allows the MCP server to ask "What topics exist?"
    rosapi_node = Node(package="rosapi", executable="rosapi_node", name="rosapi", output="screen")

    # 7. FINAL RETURN
    return LaunchDescription(
        [
            port_arg,
            gazebo_sim,
            bridge,
            rosbridge_node,
            rosapi_node,
        ]
    )
