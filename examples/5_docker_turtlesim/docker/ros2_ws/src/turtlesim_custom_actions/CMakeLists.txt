cmake_minimum_required(VERSION 3.8)
project(turtlesim_custom_actions)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)
find_package(turtlesim REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "action/DriveDistance.action"
  "action/GoToPose.action"
  "action/SetPen.action"
  "action/TeleportAbsolute.action"
  DEPENDENCIES geometry_msgs
)

ament_python_install_package(turtlesim_custom_action_servers)

rosidl_get_typesupport_target(cpp_typesupport_target "${PROJECT_NAME}" "rosidl_typesupport_cpp")
rosidl_get_typesupport_target(py_typesupport_target "${PROJECT_NAME}" "rosidl_typesupport_python")

install(
  PROGRAMS
    scripts/drive_distance_server.py
    scripts/goto_pose_server.py
    scripts/set_pen_server.py
    scripts/teleport_absolute_server.py
    scripts/turtlesim_action_bringup.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_export_dependencies(rosidl_default_runtime)

ament_package()
