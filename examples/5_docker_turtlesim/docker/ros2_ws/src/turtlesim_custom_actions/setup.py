from setuptools import setup

package_name = "turtlesim_custom_actions"
python_packages = ["turtlesim_custom_action_servers"]

setup(
    name=package_name,
    version="0.1.0",
    packages=python_packages,
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=[
        "setuptools",
    ],
    zip_safe=True,
    maintainer="Jonathan Salfity",
    maintainer_email="j.salfity@utexas.edu",
    description="Custom action servers wired into turtlesim for ROS MCP demos.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "drive_distance_server = turtlesim_custom_action_servers.drive_distance_server:main",
            "goto_pose_server = turtlesim_custom_action_servers.goto_pose_server:main",
            "set_pen_server = turtlesim_custom_action_servers.set_pen_server:main",
            "teleport_absolute_server = turtlesim_custom_action_servers.teleport_absolute_server:main",
            "turtlesim_action_bringup = turtlesim_custom_action_servers.launch_all_servers:main",
        ],
    },
)
