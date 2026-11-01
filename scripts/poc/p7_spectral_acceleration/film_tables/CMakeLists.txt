cmake_minimum_required(VERSION 3.29)
project(alcedo_film_tables LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# The table library has no dependency on Python. The product links this target.
add_library(film_tables STATIC film_tables.cpp)
target_include_directories(film_tables PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
set_target_properties(film_tables PROPERTIES POSITION_INDEPENDENT_CODE ON)
find_package(Threads REQUIRED)
target_link_libraries(film_tables PUBLIC Threads::Threads)

# The Python module of the lab.
find_package(Python 3.10 REQUIRED COMPONENTS Interpreter Development.Module)
find_package(nanobind CONFIG REQUIRED)
nanobind_add_module(alcedo_film_tables NOMINSIZE python_bindings.cpp)
target_link_libraries(alcedo_film_tables PRIVATE film_tables)
install(TARGETS alcedo_film_tables LIBRARY DESTINATION .)
