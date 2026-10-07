import os
import time
import pygame

# Pinocchio-based controller (matches the deployed environment)
from src.gamepad_pin import RoboticArmController


class Teleop(RoboticArmController):
    """Virtual-arm teleoperation using the MuJoCo native viewer."""

    def __init__(self, urdf_path: str = None, mesh_path: str = None, root_name: str = None,
                 target_link_name: str = None, visualization_backend: str = "mujoco"):
        super().__init__(urdf_path, mesh_path, root_name,
                         target_link_name=target_link_name,
                         visualization_backend=visualization_backend)


def get_current_path():
    """Get current path"""
    return os.path.dirname(os.path.realpath(__file__))


def main():
    """Main function for virtual robotic arm teleoperation with MuJoCo viz."""
    urdf_path = os.path.join(get_current_path(), "piper/piper.urdf")
    mesh_path = os.path.join(get_current_path(), "piper/meshes/")

    # Initialize control class with MuJoCo visualization backend
    controller = Teleop(urdf_path, mesh_path, "/base_link", "link6",
                        visualization_backend="mujoco")

    t1 = time.time()

    try:
        while True:
            # Update control state
            controller.update()

            # Print status
            controller.print_state()

            t2 = time.time()
            print(f"Update time: {(t2 - t1) * 1000:.3f}ms")
            t1 = t2

            pygame.time.wait(5)  # Control loop frequency

    except KeyboardInterrupt:
        print("\nProgram exited")
        pygame.quit()


if __name__ == "__main__":
    main()
