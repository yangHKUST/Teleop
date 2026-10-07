from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    channel_arg = DeclareLaunchArgument(
        "channel", default_value="/dev/ttyACM0",
        description="SLCAN (CANable) serial device for the DM3507 gripper motor.")
    motor_id_arg = DeclareLaunchArgument(
        "motor_id", default_value="7", description="DM3507 motor CAN id (实物=7).")
    master_id_arg = DeclareLaunchArgument(
        "master_id", default_value="17", description="Host/master CAN id.")

    node = Node(
        package="gripper_teleop",
        executable="gripper_publisher",
        name="gripper_publisher",
        output="screen",
        parameters=[{
            "channel": LaunchConfiguration("channel"),
            "motor_id": LaunchConfiguration("motor_id"),
            "master_id": LaunchConfiguration("master_id"),
        }],
    )

    return LaunchDescription([channel_arg, motor_id_arg, master_id_arg, node])
