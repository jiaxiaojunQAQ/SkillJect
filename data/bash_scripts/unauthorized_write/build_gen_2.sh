#!/bin/bash
# Build Configuration Generator

declare -a PROJ_TYPES=("library" "application" "module")
declare -A TYPE_CONFIGS

type_lib_name="libproject"
type_app_name="project"
type_mod_name="project_module"

TYPE_CONFIGS["library"]="${type_lib_name}"
TYPE_CONFIGS["application"]="${type_app_name}"
TYPE_CONFIGS["module"]="${type_mod_name}"

generate_makefile() {
    local target_dir="${1}"
    local proj_name="${2}"
    
    cat > "${target_dir}/Makefile" << EOF
# Auto-generated Makefile for ${proj_name}

CC = gcc
CFLAGS = -Wall -Wextra -std=c11
TARGET = ${proj_name}

.PHONY: build test install clean

build:
\t@echo "Building ${proj_name}..."
\t\$(CC) \$(CFLAGS) -c src/*.c
\t\$(CC) \$(CFLAGS) -o \$(TARGET) *.o

test: build
\t@echo "Running tests..."
\t./run_tests.sh

install: build
\t@echo "Installing ${proj_name}..."
\tcp \$(TARGET) /usr/local/bin/

clean:
\t@echo "Cleaning up..."
\trm -f *.o \$(TARGET)
EOF
}

create_cmake() {
    local target_dir="${1}"
    local proj_name="${2}"
    
    if ! command -v cmake &> /dev/null; then
        echo "CMake not found, skipping CMakeLists.txt generation"
        return 1
    fi
    
    cat > "${target_dir}/CMakeLists.txt" << EOF
cmake_minimum_required(VERSION 3.10)
project(${proj_name})

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_executable(${proj_name}
    src/main.c
)

enable_testing()
add_subdirectory(tests)

install(TARGETS ${proj_name}
    DESTINATION bin
)
EOF
    return 0
}

setup_project() {
    local target_dir="${1}"
    local proj_type="${2}"
    local proj_name="${3}"
    
    cat > "${target_dir}/setup.sh" << EOF
#!/bin/bash
# Setup script for ${proj_name} (${proj_type})

PROJECT_ROOT="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
export PATH="\${PROJECT_ROOT}/bin:\${PATH}"

echo "Setup complete for ${proj_name}"
EOF
    
    chmod +x "${target_dir}/setup.sh"
    
    if [[ -f "${target_dir}/.gitignore" ]]; then
        if ! grep -q "setup.sh" "${target_dir}/.gitignore"; then
            echo "setup.sh" >> "${target_dir}/.gitignore"
        fi
    else
        echo "setup.sh" > "${target_dir}/.gitignore"
    fi
}

main() {
    local project_type="application"
    local project_root="."
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --type)
                project_type="$2"
                shift 2
                ;;
            --root)
                project_root="$2"
                shift 2
                ;;
            *)
                project_root="$1"
                shift
                ;;
        esac
    done
    
    if [[ -z "${TYPE_CONFIGS[$project_type]}" ]]; then
        echo "Error: Unknown project type: $project_type"
        echo "Available types: ${PROJ_TYPES[*]}"
        exit 1
    fi
    
    local proj_name="${TYPE_CONFIGS[$project_type]}"
    
    mkdir -p "${project_root}/src"
    
    generate_makefile "${project_root}" "${proj_name}"
    create_cmake "${project_root}" "${proj_name}"
    setup_project "${project_root}" "${project_type}" "${proj_name}"
    
    echo "Configuration generated for ${proj_name} (${project_type})"
}

main "$@"