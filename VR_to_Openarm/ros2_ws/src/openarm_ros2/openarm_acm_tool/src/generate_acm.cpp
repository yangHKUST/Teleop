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

// Generates the bimanual OpenArm self-collision matrix (disable_collisions).
//
// Safety policy:
//  * Adjacent pairs are already disabled in the input SRDF and are skipped here.
//  * Cross-arm pairs (left link <-> right link) are NEVER disabled. The two arms
//    are mounted a few centimetres apart on a shared body, so their workspaces
//    overlap and cross-arm checks are required for correct bimanual planning.
//    Uniform joint-space sampling is also a poor estimator for cross-arm
//    contacts (they are rare in a 14-DOF random walk), so we do not trust it.
//  * Only same-arm (left-left / right-right) and body-arm pairs that never
//    collided across all samples are emitted. For a single 7-DOF arm, uniform
//    sampling over the arm's own joints explores self-collisions densely, so the
//    "never collided" verdict is reliable -- verify with a large sample count.

#include <moveit/robot_model/robot_model.h>
#include <moveit/robot_state/robot_state.h>
#include <moveit/collision_detection/collision_common.h>
#include <moveit/collision_detection/collision_matrix.h>
#include <moveit/collision_detection/collision_detector_allocator.h>
#include <moveit/collision_detection_fcl/collision_detector_allocator_fcl.h>

#include <srdfdom/srdfdom/model.h>
#include <urdf_parser/urdf_parser.h>
#include <random_numbers/random_numbers/random_numbers.h>

#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <set>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace {

std::string read_file(const std::string& path)
{
  std::ifstream in(path);
  if (!in) {
    std::cerr << "cannot open " << path << "\n";
    std::exit(1);
  }
  std::ostringstream ss;
  ss << in.rdbuf();
  return ss.str();
}

std::pair<std::string, std::string> canon(const std::string& a, const std::string& b)
{
  return a <= b ? std::make_pair(a, b) : std::make_pair(b, a);
}

enum class LinkSide { BODY, LEFT, RIGHT, OTHER };

LinkSide side_of(const std::string& name)
{
  if (name.rfind("openarm_left", 0) == 0) {
    return LinkSide::LEFT;
  }
  if (name.rfind("openarm_right", 0) == 0) {
    return LinkSide::RIGHT;
  }
  if (name.rfind("openarm_body", 0) == 0) {
    return LinkSide::BODY;
  }
  return LinkSide::OTHER;
}

bool is_cross_arm(const std::string& a, const std::string& b)
{
  const LinkSide sa = side_of(a);
  const LinkSide sb = side_of(b);
  return (sa == LinkSide::LEFT && sb == LinkSide::RIGHT) ||
         (sa == LinkSide::RIGHT && sb == LinkSide::LEFT);
}

}  // namespace

int main(int argc, char** argv)
{
  if (argc < 3) {
    std::cerr << "usage: openarm-generate-acm <urdf> <srdf> [samples] [seed] [include_cross]\n";
    std::cerr << "  include_cross: 1 = also emit cross-arm (left<->right) pairs (DANGEROUS, for"
                 " investigation only); default 0\n";
    return 1;
  }

  const std::string urdf_xml = read_file(argv[1]);
  const std::string srdf_xml = read_file(argv[2]);
  const int samples = argc > 3 ? std::atoi(argv[3]) : 1000000;
  const uint32_t seed = argc > 4 ? static_cast<uint32_t>(std::atoi(argv[4])) : 20261001u;
  const bool include_cross = argc > 5 ? std::atoi(argv[5]) != 0 : false;

  urdf::ModelInterfaceSharedPtr urdf_model = urdf::parseURDF(urdf_xml);
  if (!urdf_model) {
    std::cerr << "failed to parse URDF\n";
    return 1;
  }

  auto srdf_model = std::make_shared<srdf::Model>();
  if (!srdf_model->initString(*urdf_model, srdf_xml)) {
    std::cerr << "failed to parse SRDF\n";
    return 1;
  }

  auto model = std::make_shared<moveit::core::RobotModel>(urdf_model, srdf_model);
  moveit::core::RobotState state(model);

  collision_detection::AllowedCollisionMatrix acm(*srdf_model);

  auto allocator = collision_detection::CollisionDetectorAllocatorFCL::create();
  collision_detection::CollisionEnvPtr cenv = allocator->allocateEnv(model);

  collision_detection::CollisionRequest req;
  req.contacts = true;
  req.max_contacts = 1000000;
  req.max_contacts_per_pair = 1;
  req.distance = false;

  const moveit::core::JointModelGroup* both = model->getJointModelGroup("both_arms");
  const moveit::core::JointModelGroup* left_gripper = model->getJointModelGroup("left_gripper");
  const moveit::core::JointModelGroup* right_gripper = model->getJointModelGroup("right_gripper");
  if (!both || !left_gripper || !right_gripper) {
    std::cerr << "missing planning groups (both_arms / left_gripper / right_gripper)\n";
    return 1;
  }

  std::set<std::pair<std::string, std::string>> collided;
  random_numbers::RandomNumberGenerator rng(seed);

  for (int i = 0; i < samples; ++i) {
    state.setToRandomPositions(both, rng);
    state.setToRandomPositions(left_gripper, rng);
    state.setToRandomPositions(right_gripper, rng);
    state.update();

    collision_detection::CollisionResult res;
    cenv->checkSelfCollision(req, res, state, acm);

    for (const auto& entry : res.contacts) {
      if (!entry.second.empty()) {
        collided.insert(canon(entry.first.first, entry.first.second));
      }
    }
  }

  const std::vector<std::string>& links = model->getLinkModelNamesWithCollisionGeometry();

  int emitted = 0;
  int skipped_cross = 0;
  for (size_t i = 0; i < links.size(); ++i) {
    for (size_t j = i + 1; j < links.size(); ++j) {
      const std::string& a = links[i];
      const std::string& b = links[j];
      const auto key = canon(a, b);

      collision_detection::AllowedCollision::Type type;
      const bool already_disabled =
        acm.getEntry(key.first, key.second, type) &&
        type == collision_detection::AllowedCollision::ALWAYS;
      if (already_disabled) {
        continue;
      }

      if (collided.count(key)) {
        continue;  // collided at least once -> keep enabled
      }

      if (is_cross_arm(key.first, key.second) && !include_cross) {
        ++skipped_cross;
        continue;  // never disable cross-arm pairs
      }

      std::cout << "    <disable_collisions link1=\"" << key.first << "\" link2=\""
                << key.second << "\" reason=\"Never\"/>\n";
      ++emitted;
    }
  }

  std::cerr << "sampled=" << samples
            << " collided_pairs=" << collided.size()
            << " new_disables=" << emitted
            << " skipped_cross_arm=" << skipped_cross
            << " links_with_geometry=" << links.size() << "\n";

  return 0;
}
