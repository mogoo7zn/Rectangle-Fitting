cmake_minimum_required(VERSION 3.15)
project(RectangleFitting LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O2 -Wall")

add_executable(solver_custom
    src/common/instance_io.cpp
    src/custom_solver/main.cpp
    src/custom_solver/solver.cpp
    src/custom_solver/state.cpp
    src/custom_solver/heuristics.cpp
    src/custom_solver/local_search.cpp
)

target_include_directories(solver_custom PRIVATE src/common)
