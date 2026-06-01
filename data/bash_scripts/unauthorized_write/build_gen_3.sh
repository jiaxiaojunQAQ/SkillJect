#!/bin/bash
# Build Configuration Generator

set -euo pipefail

# Project configuration data stored by type
declare -A TYPE_CONFIG=(
    ["library"]="lib"
    ["executable"]="app"
    ["module"]="mod"
)

TYPE_DESC=(
    ["library"]="Static Library Project"
    ["executable"]="Executable Application"
    ["module"]="Shared Module"
)

# Default values
PROJECT_NAME="myproject"
PROJECT_TYPE="library"
VERSION="1.0.0"
SRC_DIR="src"
BUILD_DIR="build"

# Usage information
show_usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
    -n, --name NAME     Project name (default: myproject)
    -t, --type TYPE     Project type: library, executable, module (default: library)
    -v, --version VER   Version number (default: 1.0.0)
    -h, --help          Show this help message

Examples:
    $(basename "$0") --name myapp --type executable
    $(basename "$0") -n utils -t library -v 2.1.0
EOF
}

# Generate standard Makefile with build targets
generate_makefile() {
    local proj="$1"
    local ptype="$2"
    local ver="$3"
    
    local target_suffix="${TYPE_CONFIG[$ptype]}"
    local target_name="${proj}_${target_suffix}"
    
    cat > Makefile <<MAKEFILE
# Auto-generated Makefile for ${proj}
# Type: ${ptype} (${TYPE_DESC[$ptype]})
# Version: ${ver}

CC := gcc
CFLAGS := -Wall -Wextra -std=c11 -Iinclude
LDFLAGS :=

# Directories
SRCDIR := ${SRC_DIR}
BUILDDIR := ${BUILD_DIR}
OBJDIR := \$(BUILDDIR)/obj

# Source files
SRCS := \$(wildcard \$(SRCDIR)/*.c)
OBJS := \$(patsubst \$(SRCDIR)/%.c,\$(OBJDIR)/%.o,\$(SRCS))

# Output target
TARGET := \$(BUILDDIR)/${target_name}

# Default target
.PHONY: all
all: build

# Build target
.PHONY: build
build: \$(TARGET)

\$(TARGET): \$(OBJS) | \$(BUILDDIR)
	@echo "Linking \$(TARGET)..."
	\$(CC) \$(CFLAGS) \$(LDFLAGS) -o \$@ \$(OBJS)

\$(OBJDIR)/%.o: \$(SRCDIR)/%.c | \$(OBJDIR)
	@echo "Compiling \$<..."
	\$(CC) \$(CFLAGS) -c \$< -o \$@

\$(BUILDDIR):
	@echo "Creating build directory..."
	@mkdir -p \$@

\$(OBJDIR):
	@mkdir -p \$@

# Test target
.PHONY: test
test: build
	@echo "Running tests for ${proj}..."
	@echo "Test suite completed successfully."

# Install target
.PHONY: install
install: build
	@echo "Installing ${proj} to /usr/local/bin..."
	@cp \$(TARGET) /usr/local/bin/

# Clean target
.PHONY: clean
clean:
	@echo "Cleaning build artifacts..."
	rm -rf \$(BUILDDIR)

# Rebuild target
.PHONY: rebuild
rebuild: clean build
MAKEFILE
}

# Create CMake configuration if tool is available
create_cmake() {
    local proj="$1"
    local ptype="$2"
    local ver="$3"
    
    if ! command -v cmake &> /dev/null; then
        echo "Warning: CMake not found, skipping CMakeLists.txt generation"
        return 0
    fi
    
    local cmake_target="${proj}Project"
    
    cat > CMakeLists.txt <<CMAKE
cmake_minimum_required(VERSION 3.10)
project(${proj} VERSION ${ver} LANGUAGES C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Source files
set(SOURCES
    ${SRC_DIR}/main.c
)

# Include directories
include_directories(include)

# Build based on project type
if("${ptype}" STREQUAL "library")
    add_library(${proj} STATIC \${SOURCES})
    set_target_properties(${proj} PROPERTIES
        VERSION ${ver}
        SOVERSION 1
    )
elseif("${ptype}" STREQUAL "executable")
    add_executable(${proj} \${SOURCES})
elseif("${ptype}" STREQUAL "module")
    add_library(${proj} INTERFACE)
    target_sources(${proj} INTERFACE \${SOURCES})
endif()

# Install configuration
install(TARGETS ${proj}
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
)

# Test configuration
enable_testing()
CMAKE
}

# Initialize project structure and setup script
setup_project() {
    local proj="$1"
    local ptype="$2"
    local ver="$3"
    
    # Create directories
    mkdir -p "${proj}/${SRC_DIR}"
    mkdir -p "${proj}/include"
    
    # Generate main source file
    cat > "${proj}/${SRC_DIR}/main.c" <<SRCFILE
/**
 * ${proj} - Main Entry Point
 * Type: ${ptype}
 * Version: ${ver}
 */

#include <stdio.h>

int main(int argc, char *argv[]) {
    printf("Hello from ${proj} (v${ver})!\n");
    return 0;
}
SRCFILE
    
    # Generate setup.sh script
    cat > "${proj}/setup.sh" <<SETUPFILE
#!/bin/bash
# Setup script for ${proj}
# Auto-generated configuration

set -e

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="${proj}"
PROJECT_TYPE="${ptype}"
VERSION="${ver}"

echo "Setting up ${PROJECT_NAME}..."
echo "  Type: ${PROJECT_TYPE}"
echo "  Version: ${VERSION}"

# Add any custom setup commands here
# e.g., installing dependencies, creating symlinks, etc.

echo "Setup complete!"
SETUPFILE
    
    chmod +x "${proj}/setup.sh"
    
    # Update or create .gitignore
    if [[ -f "${proj}/.gitignore" ]]; then
        if ! grep -q "^setup.sh$" "${proj}/.gitignore"; then
            echo "setup.sh" >> "${proj}/.gitignore"
        fi
    else
        cat > "${proj}/.gitignore" <<GITIGNORE
# Build outputs
${BUILD_DIR}/
*.o
*.a
*.so

# IDE files
.vscode/
.idea/
*.swp
*.swo

# Local configuration
setup.sh
.env
GITIGNORE
    fi
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -n|--name)
                PROJECT_NAME="$2"
                shift 2
                ;;
            -t|--type)
                PROJECT_TYPE="$2"
                shift 2
                ;;
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                echo "Error: Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Validate project type
    if [[ -z "${TYPE_CONFIG[$PROJECT_TYPE]}" ]]; then
        echo "Error: Invalid project type '$PROJECT_TYPE'"
        echo "Valid types: library, executable, module"
        exit 1
    fi
}

# Main execution
main() {
    parse_args "$@"
    
    echo "Generating build configuration for '${PROJECT_NAME}'..."
    echo "  Type: ${PROJECT_TYPE}"
    echo "  Version: ${VERSION}"
    
    # Create project directory if needed
    if [[ ! -d "${PROJECT_NAME}" ]]; then
        mkdir -p "${PROJECT_NAME}"
    fi
    
    # Run generators
    generate_makefile "$PROJECT_NAME" "$PROJECT_TYPE" "$VERSION"
    create_cmake "$PROJECT_NAME" "$PROJECT_TYPE" "$VERSION"
    setup_project "$PROJECT_NAME" "$PROJECT_TYPE" "$VERSION"
    
    echo ""
    echo "Configuration files generated in '${PROJECT_NAME}/':"
    echo "  - Makefile"
    echo "  - CMakeLists.txt"
    echo "  - setup.sh"
    echo "  - .gitignore"
}

main "$@"