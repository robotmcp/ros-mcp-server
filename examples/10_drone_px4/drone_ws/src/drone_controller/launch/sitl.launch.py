from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess

def generate_launch_description():
    return LaunchDescription([
        # 1. Start Simulated Drone (PX4 SITL) - User usually runs this manually, but we can try?
        # Actually standard practice is user runs 'make px4_sitl' in another term. 
        # But we can launch MAVROS.
        
        # MAVROS
        Node(
            package='mavros',
            executable='mavros_node',
            output='screen',
            parameters=[
                {'fcu_url': 'udp://:14540@127.0.0.1:14557'},
                {'system_id': 1},
                {'component_id': 1},
                {'target_system_id': 1},
                {'target_component_id': 1},
            ]
        ),
        
        # Bridge Node
        Node(
            package='drone_controller',
            executable='bridge',
            output='screen',
            parameters=[{'use_sim_time': True}]
        )
    ])
