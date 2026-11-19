cmake_minimum_required(VERSION 3.8)
project(lidar_pkg)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(OpenCV REQUIRED)

add_executable(lidar_node src/lidar_node.cpp)
ament_target_dependencies(lidar_node rclcpp sensor_msgs)
target_link_libraries(lidar_node ${OpenCV_LIBS})

install(TARGETS
  lidar_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY
  launch
  urdf
  rviz
  config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
