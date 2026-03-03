from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, Command, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory

import os


def generate_launch_description():

    # ---------------- Launch Configurations ----------------

    esp_port   = LaunchConfiguration('esp_port')
    esp_baud   = LaunchConfiguration('esp_baud')

    lidar_port = LaunchConfiguration('lidar_port')
    lidar_baud = LaunchConfiguration('lidar_baud')

    ekf_yaml   = LaunchConfiguration('ekf_yaml')

    use_lidar  = LaunchConfiguration('use_lidar')
    use_ekf    = LaunchConfiguration('use_ekf')

    # ---------------- Paths ----------------

    tinycar_description_pkg = FindPackageShare('tinycar_description')

    sllidar_launch = os.path.join(
        get_package_share_directory('sllidar_ros2'),
        'launch',
        'sllidar_a1_launch.py'
    )

    # ---------------- Robot State Publisher ----------------

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': Command([
                'xacro ',
                PathJoinSubstitution([
                    tinycar_description_pkg,
                    'urdf',
                    'tinycar.urdf.xacro'
                ])
            ])
        }]
    )

    # ---------------- EKF ----------------

    ekf_node = Node(
        condition=IfCondition(use_ekf),
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[ekf_yaml]
    )

    # ---------------- micro-ROS Agent ----------------

    micro_ros_agent = ExecuteProcess(
        cmd=[
            'bash', '-lc',
            'ros2 run micro_ros_agent micro_ros_agent serial --dev "$ESP_PORT" -b "$ESP_BAUD"'
        ],
        additional_env={
            'ESP_PORT': esp_port,
            'ESP_BAUD': esp_baud
        },
        output='screen'
    )

    # ---------------- LiDAR ----------------

    lidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(sllidar_launch),
        condition=IfCondition(use_lidar),
        launch_arguments={
            'serial_port': lidar_port,
            'serial_baudrate': lidar_baud,
            'frame_id': 'base_laser'
        }.items()
    )

    # ---------------- Static TF: base_link -> laser ----------------

    static_laser_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='base_to_laser_tf',
        output='screen',
        arguments=[
            '0.10', '0.0', '0.05',   # xyz (adjust for your mount)
            '0', '0', '0',          # rpy
            'base_link',
            'base_laser'
        ],
        condition=IfCondition(use_lidar)
    )

    # ---------------- Launch Description ----------------

    return LaunchDescription([

        # -------- Arguments --------
        DeclareLaunchArgument('esp_port',   default_value='/dev/ttyUSB0'),
        DeclareLaunchArgument('esp_baud',   default_value='115200'),
        DeclareLaunchArgument('lidar_port', default_value='/dev/ttyUSB1'),
        DeclareLaunchArgument('lidar_baud', default_value='115200'),
        DeclareLaunchArgument(
            'ekf_yaml',
            default_value=os.path.join(
                get_package_share_directory('tinycar_bringup'),
                'config',
                'ekf.yaml'
            )
        ),
        DeclareLaunchArgument('use_lidar', default_value='true'),
        DeclareLaunchArgument('use_ekf',   default_value='true'),

        # -------- Bringup Order --------
        micro_ros_agent,

        robot_state_publisher_node,

        TimerAction(
            period=2.0,
            actions=[
                ekf_node,
                lidar_launch,
                static_laser_tf
            ]
        ),
    ])