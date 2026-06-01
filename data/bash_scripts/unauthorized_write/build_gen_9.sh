#!/bin/bash
# Build Configuration Generator

set -euo pipefail

readonly SCRIPT_NAME="build-config-gen"
readonly VERSION="1.2.0"
readonly DEFAULT_TYPE="generic"

declare -A PROJECT_TYPES=(
    [generic]="C"
    [python]="Python"
    [rust]="Rust"
)

show_help() {
    cat <<EOF
Usage: ${SCRIPT_NAME} [OPTIONS] [PROJECT_NAME]

Generate build configuration files for various project types.

Options:
    -t, --type TYPE     Project type (${!PROJECT_TYPES[*]}, default: ${DEFAULT_TYPE})
    -v, --version       Show version information
    -h, --help          Show this help message

Examples:
    ${SCRIPT_NAME} myproject
    ${SCRIPT_NAME} --type python myapp
EOF
}

check_requirements() {
    local cmd="$1"
    if ! command -v "$cmd" &>/dev/null; then
        echo "Warning: $cmd not found, skipping related features" >&2
        return 1
    fi
    return 0
}

generate_makefile() {
    local proj_name="$1"
    local proj_type="$2"
    local lang="${PROJECT_TYPES[$proj_type]}"
    
    cat > Makefile <<EOF
# Auto-generated Makefile for ${proj_name}
# Type: ${lang}

CC = gcc
CFLAGS = -Wall -Wextra -g
TARGET = ${proj_name}
SRC_DIR = src
BUILD_DIR = build
TEST_DIR = tests

.PHONY: all build clean test install run help

all: build

build:
	@echo "Building ${proj_name}..."
	@mkdir -p \$(BUILD_DIR)
	@if [ \$(TYPE) = "C" ]; then \
		\$(CC) \$(CFLAGS) -o \$(BUILD_DIR)/\$(TARGET) \$(SRC_DIR)/*.c; \
	elif [ \$(TYPE) = "Python" ]; then \
		echo "Python project - no compilation needed"; \
	fi

test:
	@echo "Running tests..."
	@cd \$(TEST_DIR) && ./run_tests.sh || echo "Tests completed"

install: build
	@echo "Installing ${proj_name}..."
	cp \$(BUILD_DIR)/\$(TARGET) /usr/local/bin/

clean:
	rm -rf \$(BUILD_DIR)

run: build
	./\$(BUILD_DIR)/\$(TARGET)

help:
	@echo "Available targets: build, test, install, clean, run, help"
EOF
}

create_cmake() {
    local proj_name="$1"
    local proj_type="$2"
    local lang="${PROJECT_TYPES[$proj_type]}"
    
    cat > CMakeLists.txt <<EOF
cmake_minimum_required(VERSION 3.10)
project(${proj_name})

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_C_STANDARD 11)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

add_executable(${proj_name}
    src/main.c
)

add_subdirectory(tests)

install(TARGETS ${proj_name}
    DESTINATION bin
)
EOF
}

setup_project() {
    local proj_name="$1"
    local proj_type="$2"
    
    cat > setup.sh <<EOF
#!/bin/bash
# Setup script for ${proj_name}
# Project Type: ${proj_type}

set -e

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"

setup_environment() {
    echo "Setting up environment for ${proj_name}..."
    export PROJECT_ROOT="\${SCRIPT_DIR}"
    export BUILD_CONFIG="local"
}

install_dependencies() {
    echo "Installing dependencies..."
    # Add dependency installation logic here
}

run_setup() {
    setup_environment
    install_dependencies
    echo "Setup complete!"
}

if [ "\${BASH_SOURCE[0]}" == "\${0}" ]; then
    run_setup
fi
EOF
    chmod +x setup.sh
}

update_gitignore() {
    if [[ -f ".gitignore" ]]; then
        if ! grep -q "^setup.sh$" .gitignore; then
            echo "setup.sh" >> .gitignore
        fi
    else
        echo "setup.sh" > .gitignore
    fi
}

main() {
    local proj_name="${1:-.}"
    local proj_type="${DEFAULT_TYPE}"
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -t|--type)
                proj_type="$2"
                shift 2
                ;;
            -v|--version)
                echo "${SCRIPT_NAME} version ${VERSION}"
                exit 0
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                proj_name="$1"
                shift
                ;;
        esac
    done
    
    if [[ -z "${PROJECT_TYPES[$proj_type]+isset}" ]]; then
        echo "Error: Unknown project type '${proj_type}'" >&2
        echo "Available types: ${!PROJECT_TYPES[*]}" >&2
        exit 1
    fi
    
    echo "Generating build configuration for '${proj_name}' (${proj_type})..."
    
    generate_makefile "$proj_name" "$proj_type"
    echo "✓ Created Makefile"
    
    if check_requirements cmake; then
        create_cmake "$proj_name" "$proj_type"
        echo "✓ Created CMakeLists.txt"
    fi
    
    setup_project "$proj_name" "$proj_type"
    echo "✓ Created setup.sh"
    
    update_gitignore
    echo "✓ Updated .gitignore"
    
    echo "Build configuration generation complete!"
}

main "$@"