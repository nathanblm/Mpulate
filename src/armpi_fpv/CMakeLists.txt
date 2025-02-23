cmake_minimum_required(VERSION 3.5)
project(armpi_fpv)

# Find ament_cmake
find_package(ament_cmake REQUIRED)

# If you have dependencies like rclcpp, you would find them here:
# find_package(rclcpp REQUIRED)

# Since this is a robot description package, you may simply install the URDF and mesh directories.
install(DIRECTORY
  urdf
  meshes
  DESTINATION share/${PROJECT_NAME}
)

# If you have launch files, you might want to install them too.
install(DIRECTORY
  launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()

