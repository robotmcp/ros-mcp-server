from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # MAVROS for Real Hardware (Serial / UART)
        Node(
            package='mavros',
            executable='mavros_node',
            output='screen',
            parameters=[
                # ADJUST THESE FOR REAL DRONE
                {'fcu_url': '/dev/ttyUSB0:57600'}, 
                {'system_id': 1},
                {'component_id': 1},
            ]
        ),
        
        # Bridge Node
        Node(
            package='drone_controller',
            executable='bridge',
            output='screen',
            parameters=[{'use_sim_time': False}]
        )
    ])
