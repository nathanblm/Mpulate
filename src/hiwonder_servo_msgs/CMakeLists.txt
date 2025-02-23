cmake_minimum_required(VERSION 3.5)
project(hiwonder_servo_msgs)

# Find ament and the default generators for ROS interfaces
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(action_msgs REQUIRED)  # If needed by your action definitions

# List your message files (make sure these files are in the msg/ folder)
set(msg_files
  "msg/JointState.msg"
  "msg/ServoState.msg"
  "msg/ServoStateList.msg"
  "msg/CommandDuration.msg"
  "msg/CommandDurationList.msg"
  "msg/RawIdPosDur.msg"
  "msg/MultiRawIdPosDur.msg"
)

# List your action files (make sure these files are in the action/ folder)
set(action_files
  "action/ActionGroupRunner.action"
)

# Generate ROS interfaces using rosidl_default_generators.
# Note: You can add additional dependencies in the DEPENDENCIES option.
rosidl_generate_interfaces(${PROJECT_NAME}
  ${msg_files}
  ${action_files}
  DEPENDENCIES std_msgs action_msgs
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
