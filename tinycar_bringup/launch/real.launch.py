from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os
import xacro

def generate_launch_description():

    pkg_share = get_package_share_directory('tinycar_description')
    urdf_file = os.path.join(pkg_share, 'urdf', 'tinycar.urdf.xacro')

    robot_description = {
        'robot_description': xacro.process_file(urdf_file).toxml()
    }

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[robot_description],
        output='screen'
    )

    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        parameters=[os.path.join(
            get_package_share_directory('tinycar_bringup'),
            'config',
            'ekf.yaml')],
        output='screen'
    )

    return LaunchDescription([
        robot_state_publisher,
        ekf_node,
    ])