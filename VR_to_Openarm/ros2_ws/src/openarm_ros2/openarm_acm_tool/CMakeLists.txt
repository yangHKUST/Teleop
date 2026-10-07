cmake_minimum_required(VERSION 3.8)
project(openarm_acm_tool)

find_package(ament_cmake REQUIRED)
find_package(moveit_core REQUIRED)
find_package(srdfdom REQUIRED)
find_package(random_numbers REQUIRED)
find_package(urdf REQUIRED)

add_executable(openarm-generate-acm src/generate_acm.cpp)
target_compile_features(openarm-generate-acm PRIVATE cxx_std_17)
target_link_libraries(openarm-generate-acm
  moveit_core::moveit_robot_model
  moveit_core::moveit_robot_state
  moveit_core::moveit_collision_detection
  moveit_core::moveit_collision_detection_fcl
  srdfdom::srdfdom
  random_numbers::random_numbers
  urdf::urdf)

install(TARGETS openarm-generate-acm DESTINATION lib/${PROJECT_NAME})

ament_package()
