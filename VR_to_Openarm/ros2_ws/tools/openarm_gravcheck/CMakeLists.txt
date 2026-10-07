cmake_minimum_required(VERSION 3.16)
project(openarm_gravcheck CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(pinocchio REQUIRED)
find_package(OpenArmCAN REQUIRED)

add_executable(gravcheck gravcheck.cpp)
target_link_libraries(gravcheck PRIVATE
  pinocchio::pinocchio
  OpenArmCAN::openarm_can
)
