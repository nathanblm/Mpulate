import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    # Locate package directories
    gazebo_ros_share = get_package_share_directory('gazebo_ros')
    armpi_fpv_share = get_package_share_directory('armpi_fpv')
    
    # Full path to the URDF file
    urdf_file = os.path.join(armpi_fpv_share, 'urdf', 'armpi_fpv.urdf')
    
    return LaunchDescription([
        # Include the empty world launch file (ROS 2 version)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(gazebo_ros_share, 'launch', 'empty_world.launch.py')
            )
        ),
        
        # Static transform publisher using tf2_ros
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='tf_footprint_base',
            output='screen',
            arguments=['0', '0', '0', '0', '0', '0', 'base_link', 'base_footprint', '40']
        ),
        
        # Spawn the URDF model into Gazebo using spawn_entity.py
        Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            name='spawn_model',
            output='screen',
            arguments=[
                '-file', urdf_file,
                '-urdf',
                '-model', 'armpi_fpv'
            ]
        ),
        
        # Publish a fake calibration message
        ExecuteProcess(
            cmd=['ros2', 'topic', 'pub', '/calibrated', 'std_msgs/msg/Bool', 'true'],
            output='screen'
        )
    ])
