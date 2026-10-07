// Interactive gravity-torque validation for OpenArm v1.0.
//
// One-off validation tool, NOT part of the control loop. It is the SOLE owner
// of the CAN bus: stop the ros2_control stack (and any other tool that opens
// the same CAN interface) before running it.
//
// Guided flow (default, interactive):
//   Walks you through joints 7 -> 1. For each joint you physically pose the
//   arm (motors are limp while you move it), press Enter, and the tool enables
//   the motors, holds the current pose with MIT control at tau_ff = 0 (exactly
//   what openarm_hardware::write() does), reads the measured torque, and
//   compares it against pinocchio::computeGeneralizedGravity(q) joint by joint.
//   It reports per joint whether the angle is near a mechanical limit, whether
//   the gravity signal is large enough to trust, and whether sign + magnitude
//   match. Then it disables the motors again so you can move to the next pose.
//
//   Steady-state relation: measured torque == +g(q) (same sign, same magnitude,
//   differing only by a friction bias).
//
// Run once per arm:
//   gravcheck <urdf> --prefix openarm_right --can can0   # right arm
//   gravcheck <urdf> --prefix openarm_left  --can can1   # left arm
//
//   --dry-run skips CAN entirely and prints g(q) at a demo pose (model check).

#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#include <openarm/can/socket/openarm.hpp>
#include <openarm/config/openarm_v10_config.hpp>

#include <pinocchio/algorithm/rnea.hpp>  // computeGeneralizedGravity
#include <pinocchio/multibody/data.hpp>
#include <pinocchio/multibody/model.hpp>
#include <pinocchio/parsers/urdf.hpp>

using openarm::damiao_motor::CallbackMode;
using openarm::damiao_motor::MITParam;

namespace {

constexpr double kLimitMargin = 0.05;  // rad — closer than this to a limit = "against the stop"
constexpr double kLoadMin = 0.4;       // Nm  — |g| below this = "signal too small to trust"

struct Options {
  std::string urdf_path;
  std::string can_if = "can0";
  bool enable_fd = true;               // V1.0 hardware interface defaults to CAN-FD
  std::string joint_prefix = "openarm_left";  // joint names: <prefix>_joint1..7
  double hold_s = 2.0;                 // settle time while holding pose
  int samples = 100;                   // samples to average
  double period_ms = 10.0;             // loop period
  bool dry_run = false;                // skip CAN; verify the Pinocchio half only
};

void usage(const char* argv0) {
  std::cerr
      << "usage: " << argv0 << " <urdf_path> [options]\n"
      << "  --can <iface>        CAN interface (default: can0)\n"
      << "  --no-fd              disable CAN-FD (default: enabled)\n"
      << "  --prefix <p>         arm joint prefix (default: openarm_left)\n"
      << "  --hold-s <s>         settle time holding pose (default: 2)\n"
      << "  --samples <n>        samples to average (default: 100)\n"
      << "  --period-ms <ms>     loop period (default: 10)\n"
      << "  --dry-run            skip CAN; verify model + joint mapping only\n";
}

Options parse_args(int argc, char** argv) {
  Options o;
  if (argc < 2) {
    usage(argv[0]);
    std::exit(2);
  }
  o.urdf_path = argv[1];
  for (int i = 2; i < argc; ++i) {
    std::string a = argv[i];
    auto next = [&]() -> std::string {
      if (i + 1 >= argc) {
        usage(argv[0]);
        std::exit(2);
      }
      return argv[++i];
    };
    if (a == "--can") o.can_if = next();
    else if (a == "--no-fd") o.enable_fd = false;
    else if (a == "--prefix") o.joint_prefix = next();
    else if (a == "--hold-s") o.hold_s = std::stod(next());
    else if (a == "--samples") o.samples = std::stoi(next());
    else if (a == "--period-ms") o.period_ms = std::stod(next());
    else if (a == "--dry-run") o.dry_run = true;
    else { usage(argv[0]); std::exit(2); }
  }
  return o;
}

std::string read_file(const std::string& path) {
  std::ifstream in(path);
  if (!in) {
    std::cerr << "cannot open URDF: " << path << "\n";
    std::exit(1);
  }
  std::stringstream ss;
  ss << in.rdbuf();
  return ss.str();
}

struct Joint {
  std::string name;
  pinocchio::JointIndex jid;
  int idx_q;
  int idx_v;
  double lower;  // rad
  double upper;  // rad
};

struct Measurement {
  std::vector<double> q;     // measured joint position (mean), rad
  std::vector<double> tau;   // measured motor torque (mean), Nm
  std::vector<double> g;     // model gravity torque, Nm
  std::vector<bool> stale;   // per-joint comms freshness flag
};

std::vector<Joint> map_joints(const pinocchio::Model& model, const std::string& prefix) {
  std::vector<Joint> joints(7);
  for (int i = 1; i <= 7; ++i) {
    std::string name = prefix + "_joint" + std::to_string(i);
    if (!model.existJointName(name)) {
      std::cerr << "joint not found: " << name << "\navailable joints:\n";
      for (pinocchio::JointIndex j = 1;
           j < static_cast<pinocchio::JointIndex>(model.joints.size()); ++j) {
        std::cerr << "  " << model.names[j] << "\n";
      }
      std::exit(1);
    }
    pinocchio::JointIndex jid = model.getJointId(name);
    int idx_q = model.joints[jid].idx_q();
    int idx_v = model.joints[jid].idx_v();
    joints[static_cast<size_t>(i - 1)] = {
        name, jid, idx_q, idx_v,
        model.lowerPositionLimit[idx_q], model.upperPositionLimit[idx_q]};
  }
  return joints;
}

// Enable -> latch current pose -> hold (tau_ff=0) -> sample -> disable.
Measurement measure(openarm::can::socket::OpenArm& arm,
                    const std::vector<Joint>& joints,
                    const pinocchio::Model& model,
                    const Options& o) {
  Measurement m;
  m.q.assign(7, 0.0);
  m.tau.assign(7, 0.0);
  m.g.assign(7, 0.0);
  m.stale.assign(7, false);

  arm.enable_all();
  arm.recv_all(5000);
  arm.set_callback_mode_all(CallbackMode::STATE);
  arm.refresh_all();
  arm.recv_all(2000);

  // Latch the current position (never command a new pose — just hold).
  std::vector<double> q_hold(7);
  {
    const auto& motors = arm.get_arm().get_motors();
    for (int i = 0; i < 7; ++i) q_hold[static_cast<size_t>(i)] = motors[i].get_position();
  }
  std::cout << "    锁住位姿 (rad): ";
  for (double q : q_hold) std::cout << std::fixed << std::setprecision(3) << q << " ";
  std::cout << "\n";

  std::vector<MITParam> hold(7);
  for (int i = 0; i < 7; ++i) {
    hold[static_cast<size_t>(i)] = {
        openarm::OpenArmV10Config::ARM_KP[static_cast<size_t>(i)],
        openarm::OpenArmV10Config::ARM_KD[static_cast<size_t>(i)],
        q_hold[static_cast<size_t>(i)], 0.0, 0.0};
  }

  // One control cycle mirrors the hardware: write() mit_control + read() refresh.
  auto tick = [&]() {
    arm.get_arm().mit_control_all(hold);
    arm.recv_all(1000);
    arm.refresh_all();
    arm.recv_all(1000);
  };

  int settle_ticks = static_cast<int>(o.hold_s * 1000.0 / o.period_ms);
  for (int k = 0; k < settle_ticks; ++k) {
    tick();
    std::this_thread::sleep_for(std::chrono::milliseconds(static_cast<int>(o.period_ms)));
  }

  for (int k = 0; k < o.samples; ++k) {
    tick();
    const auto& motors = arm.get_arm().get_motors();
    for (int i = 0; i < 7; ++i) {
      m.q[static_cast<size_t>(i)] += motors[i].get_position();
      m.tau[static_cast<size_t>(i)] += motors[i].get_torque();
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(static_cast<int>(o.period_ms)));
  }
  for (int i = 0; i < 7; ++i) {
    m.q[static_cast<size_t>(i)] /= o.samples;
    m.tau[static_cast<size_t>(i)] /= o.samples;
  }

  // Comms freshness: a motor that stopped replying would silently report stale values.
  for (int i = 0; i < 7; ++i) {
    m.stale[static_cast<size_t>(i)] =
        arm.get_arm().get_link_stats(i).is_stale(std::chrono::milliseconds(200));
  }

  // Disable so the arm goes limp for the next repositioning.
  arm.disable_all();
  arm.recv_all(2000);

  // Model gravity at the measured pose.
  Eigen::VectorXd qv = Eigen::VectorXd::Zero(model.nq);
  for (int i = 0; i < 7; ++i) qv[joints[static_cast<size_t>(i)].idx_q] = m.q[static_cast<size_t>(i)];
  pinocchio::Data data(model);
  pinocchio::computeGeneralizedGravity(model, data, qv);
  for (int i = 0; i < 7; ++i) m.g[static_cast<size_t>(i)] = data.g[joints[static_cast<size_t>(i)].idx_v];

  return m;
}

void print_table(const std::vector<Joint>& joints, const Measurement& m, int highlight) {
  std::cout << std::left << std::setw(24) << "joint" << std::right
            << std::setw(10) << "q_meas" << std::setw(11) << "tau_meas"
            << std::setw(11) << "g(q)" << std::setw(11) << "diff" << std::setw(8)
            << "sign" << "\n";
  std::cout << std::string(75, '-') << "\n";
  for (size_t i = 0; i < joints.size(); ++i) {
    double diff = m.tau[i] - m.g[i];
    bool sign_ok = (m.g[i] == 0.0) || (m.tau[i] * m.g[i] > 0.0);
    std::cout << (static_cast<int>(i) == highlight ? ">>" : "  ")
              << std::left << std::setw(22) << joints[i].name << std::right
              << std::fixed << std::setprecision(3)
              << std::setw(10) << m.q[i] << std::setw(11) << m.tau[i]
              << std::setw(11) << m.g[i] << std::setw(11) << diff << std::setw(8)
              << (sign_ok ? "OK" : "FLIP") << (m.stale[i] ? "  STALE" : "") << "\n";
  }
  std::cout << std::string(75, '-') << "\n";
}

bool read_line(const std::string& prompt, std::string& line) {
  std::cout << prompt << std::flush;
  if (!std::getline(std::cin, line)) return false;  // EOF
  return true;
}

}  // namespace

int main(int argc, char** argv) {
  Options o = parse_args(argc, argv);

  // ---- 1. Pinocchio model from URDF ----
  std::string urdf_xml = read_file(o.urdf_path);
  pinocchio::Model model;
  pinocchio::urdf::buildModelFromXML(urdf_xml, model, /*verbose=*/false,
                                     /*mimic=*/true);
  std::vector<Joint> joints = map_joints(model, o.joint_prefix);

  std::cout << "URDF: " << o.urdf_path << "\n"
            << "model: nq=" << model.nq << " nv=" << model.nv
            << "  arm prefix: " << o.joint_prefix << "\n";
  for (const auto& j : joints) {
    std::cout << "  " << j.name << " -> joint " << j.jid << " (idx_q=" << j.idx_q
              << ", idx_v=" << j.idx_v << ")  limits [" << j.lower << ", "
              << j.upper << "]\n";
  }

  if (o.dry_run) {
    std::vector<double> q_demo = {0.5, -0.4, 0.3, -0.6, 0.2, -0.3, 0.4};
    Eigen::VectorXd qv = Eigen::VectorXd::Zero(model.nq);
    for (size_t i = 0; i < joints.size(); ++i) qv[joints[i].idx_q] = q_demo[i];
    pinocchio::Data data(model);
    pinocchio::computeGeneralizedGravity(model, data, qv);
    std::cout << "\n[dry-run] g(q) at demo pose (no CAN, no motors):\n";
    for (size_t i = 0; i < joints.size(); ++i) {
      std::cout << std::left << std::setw(24) << joints[i].name << std::right
                << std::fixed << std::setprecision(3) << std::setw(10)
                << q_demo[i] << std::setw(11) << data.g[joints[i].idx_v] << "\n";
    }
    return 0;
  }

  // ---- 2. CAN + motors (same config as the hardware interface) ----
  openarm::can::socket::OpenArm arm(o.can_if, o.enable_fd);
  arm.init_arm_motors(openarm::OpenArmV10Config::ARM_MOTOR_TYPES,
                      openarm::OpenArmV10Config::ARM_SEND_CAN_IDS,
                      openarm::OpenArmV10Config::ARM_RECV_CAN_IDS);

  // Comms check (motors stay disabled here).
  arm.refresh_all();
  arm.recv_all(3000);
  {
    const auto& motors = arm.get_arm().get_motors();
    std::cout << "\n启动自检（未使能）—— 电机反馈位置 (rad):\n";
    for (int i = 0; i < 7; ++i) {
      std::cout << "  " << joints[static_cast<size_t>(i)].name << ": "
                << std::fixed << std::setprecision(3) << motors[i].get_position();
      if (arm.get_arm().get_link_stats(i).is_stale(std::chrono::milliseconds(500))) {
        std::cout << "  ⚠️ 无响应";
      }
      std::cout << "\n";
    }
  }

  std::cout << "\n=== 交互式重力对拍（joint7 -> joint1）===\n"
            << "摆位时电机是松的（禁用），回车后锁住测约 "
            << (o.hold_s + o.samples * o.period_ms / 1000.0)
            << " 秒再松开。\n"
            << "每个关节测完会给反馈；输入 a 接受进入下一关节，r 重测，s 跳过，q 退出。\n";

  // Results for the final summary.
  std::vector<std::pair<int, Measurement>> accepted;

  for (int j = 6; j >= 0; --j) {  // joint7 -> joint1
    const Joint& jt = joints[static_cast<size_t>(j)];
    bool done = false;
    while (!done) {
      std::cout << "\n========== joint" << (j + 1) << " (" << jt.name << ") ==========\n"
                << "角度范围 [" << jt.lower << ", " << jt.upper
                << "] rad；请摆到位（承重且远离限位），按回车测试 / s 跳过 / q 退出\n> ";
      std::string line;
      if (!read_line("", line)) return 0;
      if (line == "q" || line == "Q") return 0;
      if (line == "s" || line == "S") { done = true; continue; }

      Measurement m = measure(arm, joints, model, o);
      print_table(joints, m, j);

      const double q = m.q[static_cast<size_t>(j)];
      const double tau = m.tau[static_cast<size_t>(j)];
      const double g = m.g[static_cast<size_t>(j)];
      std::cout << "\n--- joint" << (j + 1) << " 反馈 ---\n"
                << "角度 q=" << std::fixed << std::setprecision(3) << q << " rad\n";
      if (m.stale[static_cast<size_t>(j)]) {
        std::cout << "⚠️  该电机无响应（STALE），本次数据不可用，请检查线缆\n";
      }
      bool near_low = (q - jt.lower) < kLimitMargin;
      bool near_up = (jt.upper - q) < kLimitMargin;
      if (near_low || near_up) {
        std::cout << "⚠️  角度贴近" << (near_low ? "下限" : "上限")
                  << "限位，挡块可能吃了重力，本次数据无效——请换个位姿\n";
      }
      bool loaded = std::fabs(g) >= kLoadMin;
      if (!loaded) {
        std::cout << "⚠️  重力信号太小 (|g|=" << std::fixed << std::setprecision(3)
                  << std::fabs(g) << " Nm < " << kLoadMin
                  << ")，判定不可靠——请摆到更有载荷的位姿\n";
      }
      if (!m.stale[static_cast<size_t>(j)] && !near_low && !near_up && loaded) {
        double diff = tau - g;
        bool sign_ok = (g == 0.0) || (tau * g > 0.0);
        bool mag_ok = std::fabs(diff) < std::max(0.5, 0.3 * std::fabs(g));
        if (sign_ok && mag_ok) {
          std::cout << "✅ 匹配：tau_meas=" << std::fixed << std::setprecision(3) << tau
                    << " vs g(q)=" << g << "（diff=" << diff << " ≈ 摩擦）\n";
        } else if (!sign_ok) {
          std::cout << "❌ 符号反了：tau_meas=" << tau << " vs g(q)=" << g
                    << " —— 该关节轴方向/符号约定可能有问题\n";
        } else {
          std::cout << "❌ 量级不符：tau_meas=" << tau << " vs g(q)=" << g
                    << "（diff=" << diff << "）—— 惯量或轴方向可能有问题\n";
        }
      }

      std::string act;
      if (!read_line("下一步: 回车/输入 a=接受进入下一关节, r=重测, s=跳过, q=退出\n> ", act)) return 0;
      if (act == "q" || act == "Q") return 0;
      if (act == "r" || act == "R") continue;  // retry same joint
      if (act == "s" || act == "S") { done = true; continue; }
      // empty or "a" -> accept and move on
      accepted.emplace_back(j, m);
      done = true;
    }
  }

  // ---- Summary ----
  std::cout << "\n========== 汇总 ==========\n";
  std::cout << std::left << std::setw(22) << "joint" << std::right
            << std::setw(10) << "q" << std::setw(11) << "tau_meas"
            << std::setw(11) << "g(q)" << std::setw(10) << "diff" << "\n";
  std::cout << std::string(64, '-') << "\n";
  for (const auto& [j, m] : accepted) {
    double diff = m.tau[static_cast<size_t>(j)] - m.g[static_cast<size_t>(j)];
    std::cout << std::left << std::setw(22) << joints[static_cast<size_t>(j)].name
              << std::right << std::fixed << std::setprecision(3)
              << std::setw(10) << m.q[static_cast<size_t>(j)]
              << std::setw(11) << m.tau[static_cast<size_t>(j)]
              << std::setw(11) << m.g[static_cast<size_t>(j)]
              << std::setw(10) << diff << "\n";
  }
  std::cout << std::string(64, '-') << "\n";
  std::cout << "已测 " << accepted.size() << "/7 关节。\n";

  arm.disable_all();
  arm.recv_all(2000);
  std::cout << "电机已禁用，退出。\n";
  return 0;
}
