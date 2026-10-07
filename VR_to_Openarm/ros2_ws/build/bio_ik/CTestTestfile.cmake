# CMake generated Testfile for 
# Source directory: /home/taoqiu/ros2_ws/src/bio_ik
# Build directory: /home/taoqiu/ros2_ws/build/bio_ik
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test(bio_ik_test "/home/taoqiu/miniconda3/bin/python3" "-u" "/opt/ros/humble/share/ament_cmake_test/cmake/run_test.py" "/home/taoqiu/ros2_ws/build/bio_ik/test_results/bio_ik/bio_ik_test.gtest.xml" "--package-name" "bio_ik" "--output-file" "/home/taoqiu/ros2_ws/build/bio_ik/ament_cmake_gtest/bio_ik_test.txt" "--command" "/home/taoqiu/ros2_ws/build/bio_ik/bio_ik_test" "--gtest_output=xml:/home/taoqiu/ros2_ws/build/bio_ik/test_results/bio_ik/bio_ik_test.gtest.xml")
set_tests_properties(bio_ik_test PROPERTIES  LABELS "gtest" REQUIRED_FILES "/home/taoqiu/ros2_ws/build/bio_ik/bio_ik_test" TIMEOUT "60" WORKING_DIRECTORY "/home/taoqiu/ros2_ws/build/bio_ik" _BACKTRACE_TRIPLES "/opt/ros/humble/share/ament_cmake_test/cmake/ament_add_test.cmake;125;add_test;/opt/ros/humble/share/ament_cmake_gtest/cmake/ament_add_gtest_test.cmake;86;ament_add_test;/opt/ros/humble/share/ament_cmake_gtest/cmake/ament_add_gtest.cmake;93;ament_add_gtest_test;/home/taoqiu/ros2_ws/src/bio_ik/CMakeLists.txt;178;ament_add_gtest;/home/taoqiu/ros2_ws/src/bio_ik/CMakeLists.txt;0;")
subdirs("gtest")
