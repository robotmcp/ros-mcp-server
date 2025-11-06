import os

from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import AnyLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from launch import LaunchDescription


def generate_launch_description():
    # Declare port argument for rosbridge
    port_arg = DeclareLaunchArgument(
        "port", default_value="9090", description="Port for rosbridge websocket"
    )

    # rosbridge websocket
    rosbridge_launch = IncludeLaunchDescription(
        AnyLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("rosbridge_server"),
                "launch",
                "rosbridge_websocket_launch.xml",
            )
        ),
        launch_arguments={"port": LaunchConfiguration("port")}.items(),
    )

    # Realsense camera driver
    realsense_launch = IncludeLaunchDescription(
        AnyLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("realsense2_camera"),
                "launch",
                "rs_launch.py",
            )
        )
    )

    # showimage for realsense (color)
    showimage_real = Node(
        package="image_tools",
        executable="showimage",
        name="showimage_real",
        remappings=[("/image", "/camera/camera/color/image_raw")],
    )

    # republish compressed for realsense color stream
    republish_real = Node(
        package="image_transport",
        executable="republish",
        name="republish_real",
        arguments=["raw"],
        remappings=[
            ("in", "/camera/camera/color/image_raw"),
            ("out", "/camera/camera/color/image_raw/compressed"),
        ],
    )

    return LaunchDescription(
        [
            port_arg,
            rosbridge_launch,
            realsense_launch,
            showimage_real,
            republish_real,
        ]
    )
