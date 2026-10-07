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

// Interactive motor enable/disable switch.
//
// Motors start DISABLED (free to rotate). Press SPACE to toggle:
//   - enable  -> every motor enables and holds the position it is at right now
//   - disable -> every motor disables and free-wheels
//
// q / ESC (or Ctrl-C) quits; on exit the motors are left disabled.
//
// This drives the motors directly over SocketCAN, so run it on its own — do not
// run ros2_control / MoveIt against the same interfaces at the same time, or the
// two writers will fight over the bus.
//
//     openarm-can-enable-switch [interface...]
//
// Defaults to the V1.0 bimanual layout: can0 (right arm) and can1 (left arm),
// 7 arm motors + 1 gripper each. Pass --no-fd for a Classic-CAN interface.

#include <CLI/CLI.hpp>
#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdio>
#include <fcntl.h>
#include <memory>
#include <openarm/can/socket/openarm.hpp>
#include <openarm/config/openarm_v10_config.hpp>
#include <termios.h>
#include <thread>
#include <unistd.h>
#include <vector>

using namespace openarm;
using namespace openarm::damiao_motor;

namespace {

// V1.0 arm layout lives in the shared OpenArmV10Config (see
// openarm/config/openarm_v10_config.hpp) so it cannot drift out of sync with
// openarm_hardware. Keep this alias for the local code below.
constexpr size_t ARM_DOF = OpenArmV10Config::ARM_DOF;

std::atomic<bool> g_running{true};
void handle_sigint(int) { g_running = false; }

// One arm: the OpenArm handle, its gains, and the latched hold position.
struct Arm {
    std::string interface;
    std::unique_ptr<can::socket::OpenArm> hw;
    std::vector<double> kp;  // ARM_DOF arm joints + 1 gripper
    std::vector<double> kd;
    std::vector<double> hold_pos;
};

Arm make_arm(const std::string& interface, bool enable_fd) {
    Arm arm;
    arm.interface = interface;
    arm.hw = std::make_unique<can::socket::OpenArm>(interface, enable_fd);
    arm.hw->init_arm_motors(OpenArmV10Config::ARM_MOTOR_TYPES,
                            OpenArmV10Config::ARM_SEND_CAN_IDS,
                            OpenArmV10Config::ARM_RECV_CAN_IDS);
    arm.hw->init_gripper_motor(OpenArmV10Config::GRIPPER_MOTOR_TYPE,
                               OpenArmV10Config::GRIPPER_SEND_CAN_ID,
                               OpenArmV10Config::GRIPPER_RECV_CAN_ID);
    arm.hw->set_callback_mode_all(CallbackMode::STATE);
    arm.kp = OpenArmV10Config::ARM_KP;
    arm.kp.push_back(OpenArmV10Config::GRIPPER_KP);
    arm.kd = OpenArmV10Config::ARM_KD;
    arm.kd.push_back(OpenArmV10Config::GRIPPER_KD);
    arm.hold_pos.assign(ARM_DOF + 1, 0.0);
    return arm;
}

// Read the current motor positions into hold_pos (raw motor radians, so no
// joint<->motor mapping is needed to hold where the arm actually is).
void latch_positions(Arm& arm) {
    arm.hw->refresh_all();
    arm.hw->recv_all(500);
    const auto& motors = arm.hw->get_arm().get_motors();
    for (size_t i = 0; i < ARM_DOF && i < motors.size(); ++i) {
        arm.hold_pos[i] = motors[i].get_position();
    }
    const auto& gripper = arm.hw->get_gripper().get_motors();
    if (!gripper.empty()) {
        arm.hold_pos[ARM_DOF] = gripper[0].get_position();
    }
}

// Hold every motor at its latched position via MIT control.
void hold(const Arm& arm) {
    std::vector<MITParam> params;
    params.reserve(ARM_DOF);
    for (size_t i = 0; i < ARM_DOF; ++i) {
        params.push_back({arm.kp[i], arm.kd[i], arm.hold_pos[i], 0.0, 0.0});
    }
    arm.hw->get_arm().mit_control_all(params);
    arm.hw->get_gripper().mit_control_all(
        {{arm.kp[ARM_DOF], arm.kd[ARM_DOF], arm.hold_pos[ARM_DOF], 0.0, 0.0}});
}

void print_positions(const std::vector<Arm>& arms) {
    for (const auto& arm : arms) {
        std::printf("  %-6s hold:", arm.interface.c_str());
        for (double q : arm.hold_pos) std::printf(" %+7.3f", q);
        std::printf("\n");
    }
}

// Puts the terminal in raw non-blocking mode so SPACE arrives without Enter.
// Restores the previous state on destruction.
struct RawTerminal {
    bool enter() {
        if (!isatty(STDIN_FILENO)) return false;
        if (tcgetattr(STDIN_FILENO, &old_t_) != 0) return false;
        termios raw = old_t_;
        raw.c_lflag &= ~static_cast<tcflag_t>(ICANON | ECHO);
        raw.c_cc[VMIN] = 0;
        raw.c_cc[VTIME] = 0;
        if (tcsetattr(STDIN_FILENO, TCSANOW, &raw) != 0) return false;
        old_fl_ = fcntl(STDIN_FILENO, F_GETFL, 0);
        fcntl(STDIN_FILENO, F_SETFL, old_fl_ | O_NONBLOCK);
        active_ = true;
        return true;
    }
    ~RawTerminal() {
        if (!active_) return;
        tcsetattr(STDIN_FILENO, TCSANOW, &old_t_);
        fcntl(STDIN_FILENO, F_SETFL, old_fl_);
    }
    termios old_t_{};
    int old_fl_ = 0;
    bool active_ = false;
};

}  // namespace

int main(int argc, char** argv) {
    CLI::App app{"Toggle OpenArm motors between free and hold. SPACE toggles, q/ESC quits."};
    std::vector<std::string> interfaces{"can0", "can1"};
    app.add_option("interface", interfaces, "SocketCAN interface per arm (right, left)")
        ->expected(0, -1)
        ->capture_default_str();
    bool classic_can = false;
    app.add_flag("--no-fd", classic_can, "Use Classic CAN instead of CAN-FD");
    CLI11_PARSE(app, argc, argv);

    if (interfaces.empty()) {
        std::fprintf(stderr, "error: at least one interface required\n");
        return 1;
    }

    try {
        std::vector<Arm> arms;
        arms.reserve(interfaces.size());
        for (const auto& iface : interfaces) {
            arms.push_back(make_arm(iface, !classic_can));
        }

        // Start disarmed: a previous process may have left the motors enabled.
        for (auto& arm : arms) arm.hw->disable_all();
        for (auto& arm : arms) arm.hw->recv_all(500);

        RawTerminal raw;
        if (!raw.enter()) {
            std::fprintf(stderr,
                         "warning: stdin is not a terminal; SPACE toggle unavailable\n");
        }

        std::signal(SIGINT, handle_sigint);

        std::printf("Motors are DISABLED (free). SPACE = enable/hold, q/ESC = quit.\n");
        std::printf("Interfaces: %s\n\n", [&] {
            std::string s;
            for (const auto& a : arms) s += (s.empty() ? "" : ", ") + a.interface;
            return s;
        }().c_str());

        bool enabled = false;
        bool need_latch = false;
        auto last_disable = std::chrono::steady_clock::now();

        while (g_running) {
            // Drain any pending keypresses.
            char c;
            while (read(STDIN_FILENO, &c, 1) == 1) {
                if (c == ' ') {
                    enabled = !enabled;
                    need_latch = enabled;
                } else if (c == 'q' || c == 0x1b) {
                    g_running = false;
                }
            }

            if (need_latch) {
                for (auto& arm : arms) latch_positions(arm);
                for (auto& arm : arms) arm.hw->enable_all();
                need_latch = false;
                std::printf("\n>>> ENABLED — holding current positions:\n");
                print_positions(arms);
                std::printf("\n");
            }

            if (enabled) {
                for (auto& arm : arms) hold(arm);
            } else {
                // Re-send the disable periodically so a watchdog or a stray
                // enable cannot silently re-arm a motor.
                auto now = std::chrono::steady_clock::now();
                if (now - last_disable >= std::chrono::milliseconds(500)) {
                    for (auto& arm : arms) arm.hw->disable_all();
                    last_disable = now;
                }
            }

            for (auto& arm : arms) arm.hw->recv_all(100);
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
        }

        // Leave the motors free on exit.
        std::printf("\n>>> exiting, disabling motors\n");
        for (auto& arm : arms) arm.hw->disable_all();
        for (auto& arm : arms) arm.hw->recv_all(500);
    } catch (const std::exception& e) {
        std::fprintf(stderr, "error: %s\n", e.what());
        return 1;
    }
    return 0;
}
