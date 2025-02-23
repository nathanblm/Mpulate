cmake_minimum_required(VERSION 3.5)
project(hiwonder_servo_driver)

# Find ament build system and any dependencies
find_package(ament_cmake REQUIRED)
find_package(rclpy REQUIRED)
find_package(diagnostic_msgs REQUIRED)
find_package(std_msgs REQUIRED)

# If you have a setup.py file, you can use ament_python_install_package to install your package.
# For a simple package that just installs executables, you can use install(PROGRAMS ...) directly.

# Install your Python scripts as executables.
install(PROGRAMS
  src/hiwonder_servo_driver/hiwonder_servo_const.py
  src/hiwonder_servo_driver/hiwonder_servo_io.py
  src/hiwonder_servo_driver/hiwonder_servo_serialproxy.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
