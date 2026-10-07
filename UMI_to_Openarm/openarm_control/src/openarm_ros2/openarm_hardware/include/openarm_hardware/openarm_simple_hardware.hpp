// Copyright 2025 Enactic, Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#pragma once

#include <array>
#include <chrono>
#include <memory>
#include <string>
#include <vector>

#include <openarm/can/socket/openarm.hpp>
#include <openarm/config/openarm_v10_config.hpp>
#include <openarm/damiao_motor/dm_motor_constants.hpp>

#include <pinocchio/algorithm/rnea.hpp>
#include <pinocchio/multibody/data.hpp>
#include <pinocchio/multibody/model.hpp>
#include <pinocchio/parsers/urdf.hpp>

#include "hardware_interface/handle.hpp"
#include "hardware_interface/hardware_info.hpp"
#include "hardware_interface/system_interface.hpp"
#include "hardware_interface/types/hardware_interface_return_values.hpp"
#include "openarm_hardware/visibility_control.h"
#include "rclcpp/macros.hpp"
#include "rclcpp_lifecycle/state.hpp"

namespace openarm_hardware {

/**
 * @brief Simplified OpenArm V10 Hardware Interface
 *
 * This is a simplified version that uses the OpenArm CAN API directly,
 * following the pattern from full_arm.cpp example. Much simpler than
 * the original implementation.
 */
class OpenArmHW : public hardware_interface::SystemInterface {
 public:
  OpenArmHW();

  TEMPLATES__ROS2_CONTROL__VISIBILITY_PUBLIC
  hardware_interface::CallbackReturn on_init(
      const hardware_interface::HardwareInfo& info) override;

  TEMPLATES__ROS2_CONTROL__VISIBILITY_PUBLIC
  hardware_interface::CallbackReturn on_configure(
      const rclcpp_lifecycle::State& previous_state) override;

  TEMPLATES__ROS2_CONTROL__VISIBILITY_PUBLIC
  std::vector<hardware_interface::StateInterface> export_state_interfaces()
      override;

  TEMPLATES__ROS2_CONTROL__VISIBILITY_PUBLIC
  std::vector<hardware_interface::CommandInterface> export_command_interfaces()
      override;

  TEMPLATES__ROS2_CONTROL__VISIBILITY_PUBLIC
  hardware_interface::CallbackReturn on_activate(
      const rclcpp_lifecycle::State& previous_state) override;

  TEMPLATES__ROS2_CONTROL__VISIBILITY_PUBLIC
  hardware_interface::CallbackReturn on_deactivate(
      const rclcpp_lifecycle::State& previous_state) override;

  TEMPLATES__ROS2_CONTROL__VISIBILITY_PUBLIC
  hardware_interface::return_type read(const rclcpp::Time& time,
                                       const rclcpp::Duration& period) override;

  TEMPLATES__ROS2_CONTROL__VISIBILITY_PUBLIC
  hardware_interface::return_type write(
      const rclcpp::Time& time, const rclcpp::Duration& period) override;

 private:
  // V10 default configuration
  static constexpr size_t ARM_DOF = openarm::OpenArmV10Config::ARM_DOF;
  static constexpr bool ENABLE_GRIPPER = true;

  // Gripper mechanism geometry (joint<->motor mapping). These describe the
  // linkage, not the motor configuration, so they live here rather than in
  // OpenArmV10Config.
  const double GRIPPER_JOINT_0_POSITION = 0.044;
  const double GRIPPER_JOINT_1_POSITION = 0.0;
  const double GRIPPER_MOTOR_0_RADIANS = 0.0;
  const double GRIPPER_MOTOR_1_RADIANS = -1.0472;

  // Control gains: initialized from the shared V10 config, then optionally
  // overridden per-joint / for the hand via ros2_control hardware parameters.
  std::vector<double> kp_ = openarm::OpenArmV10Config::ARM_KP;
  std::vector<double> kd_ = openarm::OpenArmV10Config::ARM_KD;
  double gripper_kp_ = openarm::OpenArmV10Config::GRIPPER_KP;
  double gripper_kd_ = openarm::OpenArmV10Config::GRIPPER_KD;

  // Configuration
  std::string can_interface_;
  std::string arm_prefix_;
  std::string ee_type_;
  bool hand_;
  bool can_fd_;

  // Safety: when false (the default), activation holds the current position
  // instead of forcing a return-to-zero sweep. Set true to restore the old
  // behavior.
  bool return_to_zero_{false};

  // Teaching mode: when true, gravity compensation is full (scale=1.0) and the
  // position spring toggles on a velocity deadband — kp=0 while a human drags
  // the arm (free movement), normal kp_[i] once it is released (holds where it
  // stopped). Requires gravity_ready_.
  bool teaching_mode_{false};
  // Drag-hold state: hold target re-latched to the live position during a drag,
  // plus the speed thresholds that switch between free-drag and hold.
  std::vector<double> teaching_hold_pos_;
  bool teaching_holding_{true};
  double teaching_drag_vel_{0.15};  // rad/s, peak |dq| above this -> dragging
  double teaching_hold_vel_{0.05};  // rad/s, peak |dq| below this -> holding
  // Manual trims for residual sag in teaching mode: gravity feedforward scale
  // (>1 over-compensates a model that reads light) and a hold-spring multiplier
  // (>1 stiffens the release hold without touching normal control gains).
  double teaching_gravity_scale_{1.0};
  double teaching_hold_kp_scale_{1.0};

  // Health monitor: an axis with no CAN response for longer than this is
  // reported as stale.
  std::chrono::milliseconds stale_timeout_{100};
  std::chrono::steady_clock::time_point last_health_check_{};

  // OpenArm instance
  std::unique_ptr<openarm::can::socket::OpenArm> openarm_;

  // Generated joint names for this arm instance
  std::vector<std::string> joint_names_;

  // ROS2 control state and command vectors. The hardware only accepts position
  // commands (MIT control uses zero velocity/torque feedforward), so only a
  // position command vector is kept; velocity/effort are read-only state.
  std::vector<double> pos_commands_;
  std::vector<double> pos_states_;
  std::vector<double> vel_states_;
  std::vector<double> tau_states_;

  // Gravity-compensation feedforward. G(q) is pinocchio's
  // computeGeneralizedGravity on the v1.0 URDF, using motor positions directly
  // as URDF joint positions (no motor->URDF offset). tau_ff = scale * G(q),
  // clamped per joint. gravity_ready_ stays false if the model fails to load,
  // so the control loop degrades to the previous zero-feedforward behavior.
  pinocchio::Model grav_model_;
  pinocchio::Data grav_data_;
  std::array<int, ARM_DOF> grav_idx_q_{};
  std::array<int, ARM_DOF> grav_idx_v_{};
  bool gravity_ready_{false};
  double gravity_scale_{0.0};
  // Per-joint gravity feedforward offset (Nm). Manual trim for joints where the
  // model under- (or over-) compensates; added to tau_ff before clamping.
  std::vector<double> grav_tau_offset_;
  // Per-joint gravity feedforward direction (+1 normal, -1 flips). Fixes a
  // joint whose motor direction is inverted relative to the URDF (e.g. a
  // mirrored wrist), which makes G(q) come out sign-flipped.
  std::vector<double> grav_tau_dir_;
  std::string urdf_path_;
  bool grav_tau_logged_{false};

  static constexpr std::array<double, ARM_DOF> ZERO_POSITION = {
      0.0,  // joint1
      0.0,  // joint2
      0.0,  // joint3
      0.0,  // joint4
      0.0,  // joint5
      0.0,  // joint6
      0.0,  // joint7
  };

  // Per-joint gravity-torque clamp (Nm): DM8009 x2, DM4340 x2, DM4310 x3.
  static constexpr std::array<double, ARM_DOF> GRAVITY_TMAX = {
      54.0, 54.0, 28.0, 28.0, 10.0, 10.0, 10.0};

  // Helper methods
  void return_to_zero();
  void monitor_health();
  bool parse_config(const hardware_interface::HardwareInfo& info);
  void generate_joint_names(const hardware_interface::HardwareInfo& info);
  void load_gravity_model(const std::string& urdf_path);

  // Gripper mapping functions
  double joint_to_motor_radians(double joint_value);
  double motor_radians_to_joint(double motor_radians);
};

}  // namespace openarm_hardware
