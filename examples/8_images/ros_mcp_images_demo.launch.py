from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import AnyLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os


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

    # cam2image (synthetic image since burger_mode=true)
    cam2image = Node(
        package="image_tools",
        executable="cam2image",
        name="cam2image",
        parameters=[{"burger_mode": True}],
    )

    # showimage (display the image)
    showimage = Node(
        package="image_tools",
        executable="showimage",
        name="showimage",
    )

    # image_transport republisher (raw → compressed)
    republish = Node(
        package="image_transport",
        executable="republish",
        name="republish",
        arguments=["raw"],
        remappings=[
            ("in", "/image"),
            ("out", "/image/compressed"),
        ],
    )

    return LaunchDescription(
        [
            port_arg,
            rosbridge_launch,
            cam2image,
            showimage,
            republish,
        ]
    )
