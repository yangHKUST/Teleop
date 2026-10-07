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

#include "openarm_hardware/openarm_simple_hardware.hpp"

#include <algorithm>
#include <cctype>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <thread>
#include <vector>

#include "ament_index_cpp/get_package_share_directory.hpp"

#include "hardware_interface/types/hardware_interface_type_values.hpp"
#include "rclcpp/logging.hpp"
#include "rclcpp/rclcpp.hpp"

namespace openarm_hardware {

OpenArmHW::OpenArmHW() = default;

bool OpenArmHW::parse_config(const hardware_interface::HardwareInfo& info) {
  // Parse CAN interface (default: can0)
  auto it = info.hardware_parameters.find("can_interface");
  can_interface_ = (it != info.hardware_parameters.end()) ? it->second : "can0";

  // Parse arm prefix (default: empty for single arm, "left_" or "right_" for
  // bimanual)
  it = info.hardware_parameters.find("arm_prefix");
  arm_prefix_ = (it != info.hardware_parameters.end()) ? it->second : "";

  // Parse gripper enable (default: true for V10)
  it = info.hardware_parameters.find("hand");
  if (it == info.hardware_parameters.end()) {
    hand_ = true;  // Default to true for V10
  } else {
    // Handle both "true"/"True" and "false"/"False"
    std::string value = it->second;
    std::transform(value.begin(), value.end(), value.begin(), ::tolower);
    hand_ = (value == "true");
  }

  // Parse CAN-FD enable (default: true for V10)
  it = info.hardware_parameters.find("can_fd");
  if (it == info.hardware_parameters.end()) {
    can_fd_ = true;  // Default to true for V10
  } else {
    // Handle both "true"/"True" and "false"/"False"
    std::string value = it->second;
    std::transform(value.begin(), value.end(), value.begin(), ::tolower);
    can_fd_ = (value == "true");
  }

  // Parse return-to-zero (default: false — hold current position on activate).
  // The forced zero sweep is dangerous if the arm is not already at zero, so it
  // is opt-in.
  it = info.hardware_parameters.find("return_to_zero");
  if (it == info.hardware_parameters.end()) {
    return_to_zero_ = false;
  } else {
    std::string value = it->second;
    std::transform(value.begin(), value.end(), value.begin(), ::tolower);
    return_to_zero_ = (value == "true");
  }

  // Parse teaching mode (default: false). Teaching mode disables the position
  // spring (kp=0) and applies full gravity compensation so the arm can be
  // dragged by hand and holds where it is released.
  it = info.hardware_parameters.find("teaching_mode");
  if (it == info.hardware_parameters.end()) {
    teaching_mode_ = false;
  } else {
    std::string value = it->second;
    std::transform(value.begin(), value.end(), value.begin(), ::tolower);
    teaching_mode_ = (value == "true");
  }

  // Teaching-mode drag/hold velocity thresholds (rad/s). Above drag_vel the
  // spring releases (free drag); below hold_vel it re-engages (holds).
  it = info.hardware_parameters.find("teaching_drag_vel");
  teaching_drag_vel_ =
      (it != info.hardware_parameters.end()) ? std::stod(it->second) : 0.15;
  it = info.hardware_parameters.find("teaching_hold_vel");
  teaching_hold_vel_ =
      (it != info.hardware_parameters.end()) ? std::stod(it->second) : 0.05;

  // Manual trims for residual sag in teaching mode.
  it = info.hardware_parameters.find("teaching_gravity_scale");
  teaching_gravity_scale_ =
      (it != info.hardware_parameters.end()) ? std::stod(it->second) : 1.0;
  it = info.hardware_parameters.find("teaching_hold_kp_scale");
  teaching_hold_kp_scale_ =
      (it != info.hardware_parameters.end()) ? std::stod(it->second) : 1.0;

  // Parse health-monitor stale timeout (default: 100 ms)
  it = info.hardware_parameters.find("stale_timeout_ms");
  stale_timeout_ = std::chrono::milliseconds(
      (it != info.hardware_parameters.end()) ? std::stoi(it->second) : 100);

  // Parse gravity-compensation feedforward scale (default: 0 = off).
  it = info.hardware_parameters.find("gravity_scale");
  gravity_scale_ =
      (it != info.hardware_parameters.end()) ? std::stod(it->second) : 0.0;

  // Per-joint gravity feedforward offset in Nm (default: 0). Manual trim for
  // individual joints that still sag (or float) after tuning gravity_scale.
  grav_tau_offset_.assign(ARM_DOF, 0.0);
  for (size_t i = 1; i <= ARM_DOF; ++i) {
    it = info.hardware_parameters.find("gravity_tau_offset" +
                                       std::to_string(i));
    if (it != info.hardware_parameters.end()) {
      grav_tau_offset_[i - 1] = std::stod(it->second);
    }
  }

  // Per-joint gravity feedforward direction (default: +1). Set to -1 for a
  // joint whose motor direction is inverted relative to the URDF, otherwise
  // its gravity compensation pushes the wrong way.
  grav_tau_dir_.assign(ARM_DOF, 1.0);
  for (size_t i = 1; i <= ARM_DOF; ++i) {
    it = info.hardware_parameters.find("gravity_tau_dir" + std::to_string(i));
    if (it != info.hardware_parameters.end()) {
      grav_tau_dir_[i - 1] = std::stod(it->second);
    }
  }

  // Optional URDF override for the gravity model (default: resolved below).
  it = info.hardware_parameters.find("urdf_path");
  urdf_path_ = (it != info.hardware_parameters.end()) ? it->second : "";

  // Parse control gains
  for (size_t i = 1; i <= ARM_DOF; ++i) {
    it = info.hardware_parameters.find("kp" + std::to_string(i));
    if (it != info.hardware_parameters.end()) {
      kp_[i - 1] = std::stod(it->second);
    }
    it = info.hardware_parameters.find("kd" + std::to_string(i));
    if (it != info.hardware_parameters.end()) {
      kd_[i - 1] = std::stod(it->second);
    }
  }
  // Parse ee_type (default: parallel_link for v10)
  it = info.hardware_parameters.find("ee_type");
  ee_type_ =
      (it != info.hardware_parameters.end()) ? it->second : "parallel_link";
  if (hand_) {
    it = info.hardware_parameters.find("kp_hand");
    if (it != info.hardware_parameters.end()) {
      gripper_kp_ = std::stod(it->second);
    }
    it = info.hardware_parameters.find("kd_hand");
    if (it != info.hardware_parameters.end()) {
      gripper_kd_ = std::stod(it->second);
    }
  }

  RCLCPP_INFO(rclcpp::get_logger("OpenArmHW"),
              "Configuration: CAN=%s, arm_prefix=%s, hand=%s, can_fd=%s",
              can_interface_.c_str(), arm_prefix_.c_str(),
              hand_ ? "enabled" : "disabled", can_fd_ ? "enabled" : "disabled");
  return true;
}

void OpenArmHW::load_gravity_model(const std::string& urdf_path) {
  std::ifstream in(urdf_path);
  if (!in) {
    RCLCPP_ERROR(rclcpp::get_logger("OpenArmHW"),
                 "Gravity comp: cannot open URDF '%s'; disabled",
                 urdf_path.c_str());
    gravity_ready_ = false;
    return;
  }
  std::stringstream ss;
  ss << in.rdbuf();

  try {
    pinocchio::urdf::buildModelFromXML(ss.str(), grav_model_, false, true);
  } catch (const std::exception& e) {
    RCLCPP_ERROR(rclcpp::get_logger("OpenArmHW"),
                 "Gravity comp: URDF model build failed (%s); disabled",
                 e.what());
    gravity_ready_ = false;
    return;
  }
  grav_data_ = pinocchio::Data(grav_model_);

  // Map the arm's joint names (joint_names_[0..6]) to pinocchio indices.
  for (size_t i = 0; i < ARM_DOF && i < joint_names_.size(); ++i) {
    const std::string& name = joint_names_[i];
    if (!grav_model_.existJointName(name)) {
      RCLCPP_ERROR(rclcpp::get_logger("OpenArmHW"),
                   "Gravity comp: joint '%s' not in URDF; disabled",
                   name.c_str());
      gravity_ready_ = false;
      return;
    }
    pinocchio::JointIndex jid = grav_model_.getJointId(name);
    grav_idx_q_[i] = grav_model_.joints[jid].idx_q();
    grav_idx_v_[i] = grav_model_.joints[jid].idx_v();
  }

  gravity_ready_ = true;
  RCLCPP_INFO(rclcpp::get_logger("OpenArmHW"),
              "[%s] Gravity comp ready: %s (nq=%d nv=%d), scale=%.2f",
              arm_prefix_.c_str(), urdf_path.c_str(), grav_model_.nq,
              grav_model_.nv, gravity_scale_);
}

void OpenArmHW::generate_joint_names(const hardware_interface::HardwareInfo& info) {
  joint_names_.clear();
  // Joint names come straight from the URDF <joint> declarations, in
  // declaration order (arm joints 1..7, then the gripper finger joint when
  // `hand` is enabled). This keeps the interface names in lock-step with the
  // model instead of reconstructing them from a naming convention.
  joint_names_.reserve(info.joints.size());
  for (const auto& joint : info.joints) {
    joint_names_.push_back(joint.name);
  }

  RCLCPP_INFO(rclcpp::get_logger("OpenArmHW"),
              "Read %zu joint names from URDF for arm prefix '%s'",
              joint_names_.size(), arm_prefix_.c_str());
}

hardware_interface::CallbackReturn OpenArmHW::on_init(
    const hardware_interface::HardwareInfo& info) {
  if (hardware_interface::SystemInterface::on_init(info) !=
      CallbackReturn::SUCCESS) {
    return CallbackReturn::ERROR;
  }
  // Parse configuration
  if (!parse_config(info)) {
    return CallbackReturn::ERROR;
  }

  // Read joint names from the URDF (no more hardcoded naming convention)
  generate_joint_names(info);

  // Validate joint count (7 arm joints + optional gripper)
  size_t expected_joints = ARM_DOF + (hand_ ? 1 : 0);
  if (joint_names_.size() != expected_joints) {
    RCLCPP_ERROR(rclcpp::get_logger("OpenArmHW"),
                 "URDF declares %zu joints, expected %zu", joint_names_.size(),
                 expected_joints);
    return CallbackReturn::ERROR;
  }

  // Resolve + build the gravity-compensation model (optional; a failure only
  // disables the feedforward, it never blocks activation).
  if (urdf_path_.empty()) {
    try {
      urdf_path_ =
          ament_index_cpp::get_package_share_directory("openarm_description") +
          "/assets/robot/openarm_v1.0/urdf/example/v1.urdf";
    } catch (const std::exception& e) {
      RCLCPP_WARN(rclcpp::get_logger("OpenArmHW"),
                  "Cannot resolve openarm_description share dir (%s); "
                  "gravity compensation disabled",
                  e.what());
      urdf_path_.clear();
    }
  }
  if (!urdf_path_.empty()) {
    load_gravity_model(urdf_path_);
  }

  // Initialize OpenArm with configurable CAN-FD setting
  RCLCPP_INFO(rclcpp::get_logger("OpenArmHW"),
              "Initializing OpenArm on %s with CAN-FD %s...",
              can_interface_.c_str(), can_fd_ ? "enabled" : "disabled");
  openarm_ =
      std::make_unique<openarm::can::socket::OpenArm>(can_interface_, can_fd_);

  // Initialize arm motors with the shared V10 config
  openarm_->init_arm_motors(openarm::OpenArmV10Config::ARM_MOTOR_TYPES,
                            openarm::OpenArmV10Config::ARM_SEND_CAN_IDS,
                            openarm::OpenArmV10Config::ARM_RECV_CAN_IDS);

  // Initialize gripper if enabled
  if (hand_) {
    RCLCPP_INFO(rclcpp::get_logger("OpenArmHW"), "Initializing gripper...");
    openarm_->init_gripper_motor(openarm::OpenArmV10Config::GRIPPER_MOTOR_TYPE,
                                 openarm::OpenArmV10Config::GRIPPER_SEND_CAN_ID,
                                 openarm::OpenArmV10Config::GRIPPER_RECV_CAN_ID);
  }

  // Initialize state and command vectors based on generated joint count
  const size_t total_joints = joint_names_.size();
  pos_commands_.resize(total_joints, 0.0);
  pos_states_.resize(total_joints, 0.0);
  vel_states_.resize(total_joints, 0.0);
  tau_states_.resize(total_joints, 0.0);

  RCLCPP_INFO(rclcpp::get_logger("OpenArmHW"),
              "OpenArm V10 Simple HW initialized successfully");

  return CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn OpenArmHW::on_configure(
    const rclcpp_lifecycle::State& /*previous_state*/) {
  // Set callback mode to ignore during configuration
  openarm_->refresh_all();
  std::this_thread::sleep_for(std::chrono::milliseconds(100));
  openarm_->recv_all();

  return CallbackReturn::SUCCESS;
}

std::vector<hardware_interface::StateInterface>
OpenArmHW::export_state_interfaces() {
  std::vector<hardware_interface::StateInterface> state_interfaces;
  for (size_t i = 0; i < joint_names_.size(); ++i) {
    state_interfaces.emplace_back(hardware_interface::StateInterface(
        joint_names_[i], hardware_interface::HW_IF_POSITION, &pos_states_[i]));
    state_interfaces.emplace_back(hardware_interface::StateInterface(
        joint_names_[i], hardware_interface::HW_IF_VELOCITY, &vel_states_[i]));
    state_interfaces.emplace_back(hardware_interface::StateInterface(
        joint_names_[i], hardware_interface::HW_IF_EFFORT, &tau_states_[i]));
  }

  return state_interfaces;
}

std::vector<hardware_interface::CommandInterface>
OpenArmHW::export_command_interfaces() {
  std::vector<hardware_interface::CommandInterface> command_interfaces;
  // The MIT control law used in write() only consumes a position setpoint (its
  // velocity and torque terms are fixed at zero), so exporting velocity/effort
  // command interfaces would let a controller write values that are silently
  // ignored. Expose position only.
  for (size_t i = 0; i < joint_names_.size(); ++i) {
    command_interfaces.emplace_back(hardware_interface::CommandInterface(
        joint_names_[i], hardware_interface::HW_IF_POSITION,
        &pos_commands_[i]));
  }

  return command_interfaces;
}

hardware_interface::CallbackReturn OpenArmHW::on_activate(
    const rclcpp_lifecycle::State& /*previous_state*/) {
  RCLCPP_INFO(rclcpp::get_logger("OpenArmHW"), "Activating OpenArm V10...");
  openarm_->set_callback_mode_all(openarm::damiao_motor::CallbackMode::STATE);
  openarm_->enable_all();
  std::this_thread::sleep_for(std::chrono::milliseconds(100));
  openarm_->recv_all();

  // Default behavior is to HOLD the current position (safe). The old forced
  // return-to-zero sweep is opt-in via the return_to_zero parameter. Teaching
  // mode always holds (kp=0 drag), never sweeps.
  if (return_to_zero_ && !teaching_mode_) {
    return_to_zero();
  } else {
    // Latch live positions into the command buffers so write() keeps the arm
    // exactly where it is until a controller actually commands a new target
    // (or, in teaching mode, so the gravity-unavailable fallback has a sane
    // hold position rather than pulling toward zero).
    const auto& arm_motors = openarm_->get_arm().get_motors();
    for (size_t i = 0; i < ARM_DOF && i < arm_motors.size(); ++i) {
      pos_commands_[i] = arm_motors[i].get_position();
    }
    if (hand_ && joint_names_.size() > ARM_DOF) {
      const auto& gripper_motors = openarm_->get_gripper().get_motors();
      if (!gripper_motors.empty()) {
        pos_commands_[ARM_DOF] =
            motor_radians_to_joint(gripper_motors[0].get_position());
      }
    }
    if (teaching_mode_) {
      // Start holding at the latched current position; the deadband in write()
      // releases the spring only while a human actually drags the arm.
      teaching_hold_pos_.resize(ARM_DOF);
      for (size_t i = 0; i < ARM_DOF; ++i) {
        teaching_hold_pos_[i] = pos_commands_[i];
      }
      teaching_holding_ = true;
      RCLCPP_INFO(rclcpp::get_logger("OpenArmHW"),
                  "Teaching mode: drag to move, release to hold (full gravity "
                  "comp)");
    } else {
      RCLCPP_INFO(rclcpp::get_logger("OpenArmHW"),
                  "Holding current position (return_to_zero disabled)");
    }
  }

  RCLCPP_INFO(rclcpp::get_logger("OpenArmHW"), "OpenArm V10 activated");
  return CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn OpenArmHW::on_deactivate(
    const rclcpp_lifecycle::State& /*previous_state*/) {
  RCLCPP_INFO(rclcpp::get_logger("OpenArmHW"), "Deactivating OpenArm V10...");

  // Disable all motors (like full_arm.cpp exit)
  for (int i = 0; i < 3; ++i) {
    openarm_->disable_all();
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    openarm_->recv_all();
  }

  RCLCPP_INFO(rclcpp::get_logger("OpenArmHW"), "OpenArm V10 deactivated");
  return CallbackReturn::SUCCESS;
}

hardware_interface::return_type OpenArmHW::read(
    const rclcpp::Time& /*time*/, const rclcpp::Duration& /*period*/) {
  // Receive all motor states
  openarm_->refresh_all();
  openarm_->recv_all();

  // Read arm joint states
  const auto& arm_motors = openarm_->get_arm().get_motors();
  for (size_t i = 0; i < ARM_DOF && i < arm_motors.size(); ++i) {
    pos_states_[i] = arm_motors[i].get_position();
    vel_states_[i] = arm_motors[i].get_velocity();
    tau_states_[i] = arm_motors[i].get_torque();
  }

  // Read gripper state if enabled
  if (hand_ && joint_names_.size() > ARM_DOF) {
    const auto& gripper_motors = openarm_->get_gripper().get_motors();
    if (!gripper_motors.empty()) {
      // TODO the mappings are approximates
      // Convert motor position (radians) to joint value (0-0.044m)
      double motor_pos = gripper_motors[0].get_position();
      pos_states_[ARM_DOF] = motor_radians_to_joint(motor_pos);

      // Unimplemented: Velocity and torque mapping
      vel_states_[ARM_DOF] = 0;  // gripper_motors[0].get_velocity();
      tau_states_[ARM_DOF] = 0;  // gripper_motors[0].get_torque();
    }
  }

  monitor_health();

  return hardware_interface::return_type::OK;
}

void OpenArmHW::monitor_health() {
  // Runs at most every 100 ms so a faulting axis cannot flood the log.
  const auto now = std::chrono::steady_clock::now();
  if (now - last_health_check_ < std::chrono::milliseconds(100)) return;
  last_health_check_ = now;

  auto logger = rclcpp::get_logger("OpenArmHW");
  std::string faults;

  // Per-axis faults: motor-reported error codes, and axes that stopped replying.
  const auto& arm_motors = openarm_->get_arm().get_motors();
  const auto stale = std::chrono::duration_cast<std::chrono::microseconds>(
      stale_timeout_);
  for (size_t i = 0; i < ARM_DOF && i < arm_motors.size(); ++i) {
    if (arm_motors[i].has_error()) {
      faults += " " + joint_names_[i] + "=" +
                openarm::damiao_motor::motor_error_to_string(
                    arm_motors[i].get_error_code());
    }
    if (openarm_->get_arm().get_link_stats(static_cast<int>(i)).is_stale(
            stale)) {
      faults += " " + joint_names_[i] + "=stale";
    }
  }

  if (hand_ && joint_names_.size() > ARM_DOF) {
    const auto& gripper_motors = openarm_->get_gripper().get_motors();
    if (!gripper_motors.empty()) {
      if (gripper_motors[0].has_error()) {
        faults += " " + joint_names_[ARM_DOF] + "=" +
                  openarm::damiao_motor::motor_error_to_string(
                      gripper_motors[0].get_error_code());
      }
      if (openarm_->get_gripper().get_link_stats(0).is_stale(stale)) {
        faults += " " + joint_names_[ARM_DOF] + "=stale";
      }
    }
  }

  // Bus faults affect every axis at once and are not attributable to one motor.
  // The BusStatus counters latch until cleared, so report the specific fault
  // type(s) once and clear them: a recovered transient (e.g. a tx-queue burst
  // while both arms activate) is logged once instead of flooding every cycle,
  // while a genuinely ongoing fault re-arms the counters and is reported again
  // on the next check.
  if (!openarm_->is_link_running()) {
    faults += " bus=no-carrier";
  } else {
    const auto& bus = openarm_->get_bus_status();
    if (!bus.healthy()) {
      if (bus.bus_off) faults += " bus=bus-off";
      if (bus.error_passive) faults += " bus=error-passive";
      if (bus.error_warning) faults += " bus=error-warning";
      if (bus.tx_overflow) faults += " bus=tx-overflow";
      if (bus.rx_overflow) faults += " bus=rx-overflow";
      if (bus.ack_error) faults += " bus=ack-error";
      if (bus.tx_timeout) faults += " bus=tx-timeout";
      if (bus.restarted) faults += " bus=restarted";
      if (bus.write_net_down) faults += " bus=net-down";
      if (bus.write_no_buffer) faults += " bus=no-buffer";
      if (bus.write_other) faults += " bus=write-err";
      openarm_->clear_bus_status();
    }
  }

  if (!faults.empty()) {
    RCLCPP_ERROR(logger, "[%s] motor/bus faults:%s", arm_prefix_.c_str(),
                 faults.c_str());
  }
}

hardware_interface::return_type OpenArmHW::write(
    const rclcpp::Time& /*time*/, const rclcpp::Duration& /*period*/) {
  // Control arm motors with MIT control. Gravity compensation adds a torque
  // feedforward tau_ff = clamp(scale * G(q), +/-TMAX) so the PD loop does not
  // have to fight gravity (cancels the steady-state sag G(q)/kp).
  // Teaching mode uses its own gravity feedforward scale (default 1.0), so the
  // arm is neutrally buoyant but the user can nudge it above 1.0 to cancel a
  // gravity model that reads slightly light.
  const double grav_scale =
      teaching_mode_ ? teaching_gravity_scale_ : gravity_scale_;

  std::vector<double> tau_ff(ARM_DOF, 0.0);
  if (gravity_ready_ && grav_scale > 0.0) {
    Eigen::VectorXd qv = Eigen::VectorXd::Zero(grav_model_.nq);
    for (size_t i = 0; i < ARM_DOF; ++i) {
      qv[grav_idx_q_[i]] = pos_states_[i];
    }
    pinocchio::computeGeneralizedGravity(grav_model_, grav_data_, qv);
    for (size_t i = 0; i < ARM_DOF; ++i) {
      tau_ff[i] =
          std::clamp(grav_tau_dir_[i] * grav_scale *
                         grav_data_.g[grav_idx_v_[i]] +
                         grav_tau_offset_[i],
                     -GRAVITY_TMAX[i], GRAVITY_TMAX[i]);
    }
    if (!grav_tau_logged_) {
      std::ostringstream os;
      os << "gravity tau_ff (Nm):";
      for (size_t i = 0; i < ARM_DOF; ++i) {
        os << " " << std::fixed << std::setprecision(2) << tau_ff[i];
      }
      RCLCPP_INFO(rclcpp::get_logger("OpenArmHW"), "[%s] %s",
                  arm_prefix_.c_str(), os.str().c_str());
      grav_tau_logged_ = true;
    }
  }

  // Teaching-mode drag hold: free the spring while the arm is being moved and
  // re-latch the hold target to the live position, then re-engage the spring
  // the moment the arm is released (peak speed back under the hold threshold).
  if (teaching_mode_ && gravity_ready_) {
    double max_dq = 0.0;
    for (size_t i = 0; i < ARM_DOF; ++i) {
      max_dq = std::max(max_dq, std::fabs(vel_states_[i]));
    }
    if (teaching_holding_ && max_dq > teaching_drag_vel_) {
      teaching_holding_ = false;
    } else if (!teaching_holding_ && max_dq < teaching_hold_vel_) {
      teaching_holding_ = true;
    }
    if (!teaching_holding_) {
      for (size_t i = 0; i < ARM_DOF; ++i) {
        teaching_hold_pos_[i] = pos_states_[i];
      }
    }
  }

  std::vector<openarm::damiao_motor::MITParam> arm_params;
  for (size_t i = 0; i < ARM_DOF; ++i) {
    if (teaching_mode_ && gravity_ready_ && teaching_holding_) {
      // Holding: (scaled) position spring to the latched position + gravity
      // comp. The scale lets the user stiffen the hold against residual sag.
      arm_params.push_back(
          {teaching_hold_kp_scale_ * kp_[i], kd_[i], teaching_hold_pos_[i],
           0.0, tau_ff[i]});
    } else if (teaching_mode_ && gravity_ready_) {
      // Dragging: no spring (kp=0), only damping + gravity hold.
      arm_params.push_back({0.0, kd_[i], 0.0, 0.0, tau_ff[i]});
    } else {
      arm_params.push_back({kp_[i], kd_[i], pos_commands_[i], 0.0, tau_ff[i]});
    }
  }
  openarm_->get_arm().mit_control_all(arm_params);
  // Control gripper if enabled
  if (hand_ && joint_names_.size() > ARM_DOF) {
    // TODO the true mappings are unimplemented.
    double motor_command = joint_to_motor_radians(pos_commands_[ARM_DOF]);
    openarm_->get_gripper().mit_control_all(
        {{gripper_kp_, gripper_kd_, motor_command, 0.0, 0.0}});
  }
  openarm_->recv_all(100);
  return hardware_interface::return_type::OK;
}

void OpenArmHW::return_to_zero() {
  RCLCPP_INFO(rclcpp::get_logger("OpenArmHW"), "Returning to zero position...");

  openarm_->refresh_all();
  // Return arm to zero with MIT control
  std::vector<openarm::damiao_motor::MITParam> arm_params;
  for (size_t i = 0; i < ARM_DOF; ++i) {
    arm_params.push_back({kp_[i], kd_[i], 0.0, 0.0, 0.0});
  }
  openarm_->get_arm().mit_control_all(arm_params);

  // Return gripper to zero if enabled
  if (hand_) {
    openarm_->get_gripper().mit_control_all(
        {{gripper_kp_, gripper_kd_, GRIPPER_JOINT_0_POSITION, 0.0, 0.0}});
  }
  std::this_thread::sleep_for(std::chrono::microseconds(1000));
  openarm_->recv_all();
  const auto& arm_motors = openarm_->get_arm().get_motors();

  std::vector<double> start_pos(ARM_DOF, 0.0);
  for (size_t i = 0; i < ARM_DOF && i < arm_motors.size(); ++i) {
    start_pos[i] = arm_motors[i].get_position();
  }

  const int steps = 200;
  const int step_ms = 10;

  for (int step = 0; step <= steps; ++step) {
    double t = static_cast<double>(step) / steps;  // 0.0 → 1.0

    std::vector<openarm::damiao_motor::MITParam> arm_params;
    for (size_t i = 0; i < ARM_DOF; ++i) {
      double target = start_pos[i] + t * (ZERO_POSITION[i] - start_pos[i]);
      arm_params.push_back({kp_[i], kd_[i], target, 0.0, 0.0});
    }
    openarm_->get_arm().mit_control_all(arm_params);

    if (hand_) {
      openarm_->get_gripper().mit_control_all(
          {{gripper_kp_, gripper_kd_, GRIPPER_JOINT_0_POSITION, 0.0, 0.0}});
    }

    openarm_->recv_all();
    std::this_thread::sleep_for(std::chrono::milliseconds(step_ms));
  }

  RCLCPP_INFO(rclcpp::get_logger("OpenArmHW"), "Reached zero position");
}

// void OpenArmHW::return_to_zero() {
//   RCLCPP_INFO(rclcpp::get_logger("OpenArmHW"), "Returning to zero
//   position...");

//   // Return arm to zero with MIT control
//   std::vector<openarm::damiao_motor::MITParam> arm_params;
//   for (size_t i = 0; i < ARM_DOF; ++i) {
//     arm_params.push_back({kp_[i], kd_[i], 0.0, 0.0, 0.0});
//   }
//   openarm_->get_arm().mit_control_all(arm_params);

//   // Return gripper to zero if enabled
//   if (hand_) {
//     openarm_->get_gripper().mit_control_all(
//         {{GRIPPER_KP, GRIPPER_KD, GRIPPER_JOINT_0_POSITION, 0.0, 0.0}});
//   }
//   std::this_thread::sleep_for(std::chrono::microseconds(1000));
//   openarm_->recv_all();
// }

double OpenArmHW::joint_to_motor_radians(double joint_value) {
  if (ee_type_ == "pinch_gripper") {
    // revolute: joint 0-1.5708 rad -> motor 0-1.5708
    return joint_value;
  } else {
    // parallel_link (prismatic): 0-0.044m -> 0 to -1.0472 rad
    return (joint_value / GRIPPER_JOINT_0_POSITION) * GRIPPER_MOTOR_1_RADIANS;
  }
}

double OpenArmHW::motor_radians_to_joint(double motor_radians) {
  if (ee_type_ == "pinch_gripper") {
    // revolute:
    return motor_radians;
  } else {
    // parallel_link (prismatic)
    return GRIPPER_JOINT_0_POSITION * (motor_radians / GRIPPER_MOTOR_1_RADIANS);
  }
}

// // Gripper mapping helper functions
// double OpenArmHW::joint_to_motor_radians(double joint_value) {
//   // Joint 0=closed -> motor 0 rad, Joint 0.044=open -> motor -1.0472 rad
//   return (joint_value / GRIPPER_JOINT_0_POSITION) *
//          GRIPPER_MOTOR_1_RADIANS;  // Scale from 0-0.044 to 0 to -1.0472
// }

// double OpenArmHW::motor_radians_to_joint(double motor_radians) {
//   // Motor 0 rad=closed -> joint 0, Motor -1.0472 rad=open -> joint 0.044
//   return GRIPPER_JOINT_0_POSITION *
//          (motor_radians /
//           GRIPPER_MOTOR_1_RADIANS);  // Scale from 0 to -1.0472 to 0-0.044
// }

}  // namespace openarm_hardware

#include "pluginlib/class_list_macros.hpp"

PLUGINLIB_EXPORT_CLASS(openarm_hardware::OpenArmHW,
                       hardware_interface::SystemInterface)
