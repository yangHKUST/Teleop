// Copyright 2026 Enactic, Inc.
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

#include <cstddef>
#include <cstdint>
#include <vector>

#include "openarm/damiao_motor/dm_motor_constants.hpp"

namespace openarm {

// Canonical V1.0 hardware description shared by every writer that talks to the
// bus: the ros2_control hardware interface, the enable/disable switch tool, and
// any future driver. Keeping the motor types, CAN IDs, and MIT gains in exactly
// one place means a change to the physical arm only has to be made here.
//
// The default gains are also the fallbacks used by openarm_hardware when no
// per-joint gain is supplied through its ros2_control hardware parameters, so
// they must stay in sync with the control_gains.yaml shipped by
// openarm_description.
struct OpenArmV10Config {
    static constexpr std::size_t ARM_DOF = 7;

    // Arm motors, ordered joint 1..7 (shoulder -> wrist).
    inline static const std::vector<damiao_motor::MotorType> ARM_MOTOR_TYPES = {
        damiao_motor::MotorType::DM8009,  // Joint 1
        damiao_motor::MotorType::DM8009,  // Joint 2
        damiao_motor::MotorType::DM4340,  // Joint 3
        damiao_motor::MotorType::DM4340,  // Joint 4
        damiao_motor::MotorType::DM4310,  // Joint 5
        damiao_motor::MotorType::DM4310,  // Joint 6
        damiao_motor::MotorType::DM4310,  // Joint 7
    };

    inline static const std::vector<uint32_t> ARM_SEND_CAN_IDS = {
        0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07};
    inline static const std::vector<uint32_t> ARM_RECV_CAN_IDS = {
        0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17};

    // Default MIT gains per arm joint.
    inline static const std::vector<double> ARM_KP = {
        70.0, 70.0, 70.0, 60.0, 10.0, 10.0, 10.0};
    inline static const std::vector<double> ARM_KD = {
        2.75, 2.5, 2.0, 2.0, 0.7, 0.6, 0.5};

    // Gripper: one DM4310 per arm.
    static constexpr damiao_motor::MotorType GRIPPER_MOTOR_TYPE =
        damiao_motor::MotorType::DM4310;
    static constexpr uint32_t GRIPPER_SEND_CAN_ID = 0x08;
    static constexpr uint32_t GRIPPER_RECV_CAN_ID = 0x18;
    static constexpr double GRIPPER_KP = 5.0;
    static constexpr double GRIPPER_KD = 0.1;
};

}  // namespace openarm
