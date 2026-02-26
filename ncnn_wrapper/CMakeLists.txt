cmake_minimum_required(VERSION 3.18)
project(ncnn_wrapper LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# --- Dependencies ---

# ncnn
find_package(ncnn REQUIRED)

# pybind11
# Try find_package first (pip install pybind11), then fallback to subdirectory
find_package(pybind11 QUIET)
if(NOT pybind11_FOUND)
    # Try to find via Python's pybind11
    execute_process(
        COMMAND python3 -m pybind11 --cmakedir
        OUTPUT_VARIABLE PYBIND11_CMAKE_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
        RESULT_VARIABLE PYBIND11_RESULT
    )
    if(PYBIND11_RESULT EQUAL 0)
        list(APPEND CMAKE_PREFIX_PATH "${PYBIND11_CMAKE_DIR}")
        find_package(pybind11 REQUIRED)
    else()
        message(FATAL_ERROR
            "pybind11 not found. Install it:\n"
            "  pip install pybind11\n"
            "  # or: sudo apt install pybind11-dev")
    endif()
endif()

# --- Build target ---

pybind11_add_module(ncnn_wrapper
    src/detector.cpp
    src/bindings.cpp
)

target_include_directories(ncnn_wrapper PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(ncnn_wrapper PRIVATE
    ncnn
)

# --- Platform-specific flags ---

if(CMAKE_SYSTEM_PROCESSOR MATCHES "aarch64|arm64")
    message(STATUS "Building for ARM64 (RPi 5 / Apple Silicon)")
elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|AMD64")
    message(STATUS "Building for x86_64")
endif()

# Enable OpenMP if available (critical for RPi 5 multi-threading)
find_package(OpenMP QUIET)
if(OpenMP_CXX_FOUND)
    target_link_libraries(ncnn_wrapper PRIVATE OpenMP::OpenMP_CXX)
    message(STATUS "OpenMP found: ${OpenMP_CXX_FLAGS}")
else()
    message(STATUS "OpenMP not found — single-threaded inference")
endif()

# --- Install ---

# Install the .so/.dylib next to the source for easy import
install(TARGETS ncnn_wrapper
    LIBRARY DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}
)

message(STATUS "ncnn_wrapper will be installed to: ${CMAKE_CURRENT_SOURCE_DIR}")
