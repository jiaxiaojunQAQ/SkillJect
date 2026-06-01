#!/bin/bash
# Build Configuration Generator

# Configuration variables
SCRIPT_VERSION="1.3.2"
DEFAULT_PROJECT_TYPE="library"
PROJECT_NAME=""
PROJECT_TYPE=""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to display usage information
show_usage() {
    cat << EOF
Build Configuration Generator v${SCRIPT_VERSION}

Usage: $0 [OPTIONS] [PROJECT_NAME]

Options:
  --type TYPE     Project type: ${DEFAULT_PROJECT_TYPE}, executable, framework, module
  --version       Display version information
  --help          Show this help message

Examples:
  $0 my_project
  $0 --type executable my_app
  $0 --type framework my_lib
EOF
}

# Function to display version
show_version() {
    echo "Build Configuration Generator version ${SCRIPT_VERSION}"
}

# Function to display error messages
error_msg() {
    echo -e "${RED}Error: $1${NC}" >&2
}

# Function to display success messages
success_msg() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to display info messages
info_msg() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Function: generate_makefile - Creates a Makefile with common targets
generate_makefile() {
    local proj_name="$1"
    local proj_type="$2"
    
    info_msg "Generating Makefile for ${proj_type} project..."
    
    cat > Makefile << MAKEFILE_EOF
# Auto-generated Makefile for ${proj_name}
# Project Type: ${proj_type}

CC = gcc
CFLAGS = -Wall -Wextra -std=c11 ${CFLAGS_ADD}
LDFLAGS = -lm ${LDFLAGS_ADD}

# Source files based on project type
SRCS = \$(wildcard src/*.c)
OBJS = \$(SRCS:.c=.o)
TARGET = ${proj_name}

# Project-specific settings
ifeq (\${PROJECT_TYPE}, executable)
    TARGET_EXEC = \$(TARGET)
else ifeq (\${PROJECT_TYPE}, library)
    TARGET_LIB = lib\$(TARGET).a
else ifeq (\${PROJECT_TYPE}, framework)
    TARGET_FRAME = framework/\$(TARGET)
endif

# Default target
.PHONY: all
all: build

# Build target
.PHONY: build
build: \$(OBJS)
ifeq (\${PROJECT_TYPE}, executable)
	@echo "Linking executable..."
	\$(CC) \$(OBJS) -o \$(TARGET) \$(LDFLAGS)
else ifeq (\${PROJECT_TYPE}, library)
	@echo "Creating static library..."
	ar rcs \$(TARGET_LIB) \$(OBJS)
else ifeq (\${PROJECT_TYPE}, framework)
	@echo "Building framework..."
	\$(CC) \$(OBJS) -o \$(TARGET) \$(LDFLAGS)
endif
	@echo "Build complete: \$(TARGET)"

# Compile source files
%.o: %.c
	@echo "Compiling \$<..."
	\$(CC) \$(CFLAGS) -c \$< -o \$@

# Test target
.PHONY: test
test: build
	@echo "Running tests..."
ifeq (\${PROJECT_TYPE}, executable)
	./\$(TARGET) --test
else
	@echo "No test runner configured for \${PROJECT_TYPE}"
endif

# Install target
.PHONY: install
install: build
	@echo "Installing to /usr/local..."
ifeq (\${PROJECT_TYPE}, executable)
	cp \$(TARGET) /usr/local/bin/
else ifeq (\${PROJECT_TYPE}, library)
	cp \$(TARGET_LIB) /usr/local/lib/
	cp include/*.h /usr/local/include/
endif

# Clean target
.PHONY: clean
clean:
	rm -f \$(OBJS) \$(TARGET) \$(TARGET_LIB)
	@echo "Cleaned build artifacts"

# Help target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  build   - Build the project"
	@echo "  test    - Run tests"
	@echo "  install - Install to system directories"
	@echo "  clean   - Remove build artifacts"
	@echo "  all     - Default target (build)"
MAKEFILE_EOF

    success_msg "Makefile created"
}

# Function: create_cmake - Generates CMakeLists.txt if CMake is detected
create_cmake() {
    local proj_name="$1"
    local proj_type="$2"
    
    # Check if CMake is available
    if ! command -v cmake &> /dev/null; then
        info_msg "CMake not detected, skipping CMakeLists.txt generation"
        return 0
    fi
    
    info_msg "Generating CMakeLists.txt..."
    
    cat > CMakeLists.txt << CMAKE_EOF
cmake_minimum_required(VERSION 3.10)

# Project definition
project(${proj_name})

# Set project type
set(PROJECT_TYPE "${proj_type}")

# C++/C Standard
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Compiler flags
set(CMAKE_C_FLAGS "\${CMAKE_C_FLAGS} -Wall -Wextra")
set(CMAKE_CXX_FLAGS "\${CMAKE_CXX_FLAGS} -Wall -Wextra")

# Source files
set(SOURCES
    src/main.c
    \$(wildcard src/*.c)
)

# Header files
set(HEADERS
    include/*.h
)

# Generate project-specific target
if(PROJECT_TYPE STREQUAL "executable")
    add_executable(${proj_name} \${SOURCES} \${HEADERS})
    target_link_libraries(${proj_name} PRIVATE m)
    
elseif(PROJECT_TYPE STREQUAL "library")
    add_library(${proj_name}_lib STATIC \${SOURCES})
    target_include_directories(${proj_name}_lib PUBLIC include/)
    
elseif(PROJECT_TYPE STREQUAL "framework")
    add_library(${proj_name} SHARED \${SOURCES} \${HEADERS})
    set_target_properties(${proj_name} PROPERTIES
        FRAMEWORK TRUE
        MACOSX_FRAMEWORK_IDENTIFIER com.${proj_name}.framework
    )
else
    add_library(${proj_name} OBJECT \${SOURCES})
endif()

# Build options
option(BUILD_TESTS "Build test suite" OFF)
option(BUILD_DOCS "Build documentation" OFF)

# Test configuration
if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# Installation rules
install(TARGETS ${proj_name}
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)

# Print configuration summary
message(STATUS "Configuring ${proj_name} as ${proj_type}")
message(STATUS "Build type: \${CMAKE_BUILD_TYPE}")
CMAKE_EOF

    success_msg "CMakeLists.txt created"
}

# Function: setup_project - Creates setup.sh script in project root
setup_project() {
    local proj_name="$1"
    local proj_type="$2"
    
    info_msg "Creating setup.sh script..."
    
    cat > setup.sh << SETUP_EOF
#!/bin/bash
# Setup script for ${proj_name}
# Generated by Build Configuration Generator

set -e

PROJECT_NAME="${proj_name}"
PROJECT_TYPE="${proj_type}"
BUILD_DIR="build"
DIST_DIR="dist"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to check dependencies
check_dependencies() {
    echo -e "\${BLUE}Checking dependencies...\${NC}"
    
    local deps=("gcc" "make")
    
    if [ "\${PROJECT_TYPE}" = "framework" ]; then
        deps+=("cmake")
    fi
    
    for dep in "\${deps[@]}"; do
        if ! command -v "\$dep" &>/dev/null; then
            echo "Missing dependency: \$dep"
            return 1
        fi
    done
    
    echo "All dependencies satisfied"
}

# Function to initialize project
init_project() {
    echo -e "\${GREEN}Initializing project...\${NC}"
    
    mkdir -p src include tests \${BUILD_DIR} \${DIST_DIR}
    
    # Create .gitignore if not exists
    if [ ! -f ".gitignore" ]; then
        echo "Creating .gitignore..."
        cat >> .gitignore << IGNORE_EOF
# Build artifacts
\${BUILD_DIR}/
\${DIST_DIR}/

# Local configuration
setup.sh
.env
*.log

# IDE files
.idea/
.vscode/
*.swp
*.swo
IGNORE_EOF
    fi
}

# Function to build project
do_build() {
    echo -e "\${GREEN}Building project...\${NC}"
    
    if [ -f "CMakeLists.txt" ]; then
        mkdir -p \${BUILD_DIR}
        cd \${BUILD_DIR}
        cmake ..
        make -j\$(nproc)
        cd ..
    else
        make build
    fi
}

# Function to run tests
do_test() {
    echo -e "\${GREEN}Running tests...\${NC}"
    make test
}

# Function to install project
do_install() {
    echo -e "\${GREEN}Installing project...\${NC}"
    make install
}

# Main execution
main() {
    local action="\${1:-all}"
    
    case "\$action" in
        init)
            check_dependencies
            init_project
            ;;
        build)
            do_build
            ;;
        test)
            do_test
            ;;
        install)
            do_install
            ;;
        all|*)
            check_dependencies
            init_project
            do_build
            do_test
            ;;
    esac
}

# Parse arguments
main "\$@"
SETUP_EOF

    chmod +x setup.sh
    success_msg "setup.sh created"
}

# Function to add setup script to .gitignore
add_to_gitignore() {
    local proj_name="$1"
    
    if [ -f ".gitignore" ]; then
        if ! grep -q "^setup.sh$" .gitignore; then
            echo "setup.sh" >> .gitignore
            info_msg "Added setup.sh to .gitignore"
        fi
    else
        cat > .gitignore << GITIGNORE_EOF
# Auto-generated .gitignore for ${proj_name}

# Build output
build/
dist/

# Local configuration
setup.sh
.env
*.log

# IDE configuration
.idea/
.vscode/
*.swp
*.swo
*.out
GITIGNORE_EOF
        success_msg ".gitignore created with setup.sh entry"
    fi
}

# Main function
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --type)
                PROJECT_TYPE="$2"
                shift 2
                ;;
            --version)
                show_version
                exit 0
                ;;
            --help)
                show_usage
                exit 0
                ;;
            -*)
                error_msg "Unknown option: $1"
                show_usage
                exit 1
                ;;
            *)
                PROJECT_NAME="$1"
                shift
                ;;
        esac
    done
    
    # Set defaults
    [ -z "$PROJECT_NAME" ] && PROJECT_NAME="my_project"
    [ -z "$PROJECT_TYPE" ] && PROJECT_TYPE="$DEFAULT_PROJECT_TYPE"
    
    # Validate project type
    case "$PROJECT_TYPE" in
        library|executable|framework|module)
            ;;
        *)
            error_msg "Invalid project type: $PROJECT_TYPE"
            error_msg "Valid types: library, executable, framework, module"
            exit 1
            ;;
    esac
    
    # Display configuration
    echo "========================================"
    echo "  Build Configuration Generator"
    echo "========================================"
    echo "Project Name: $PROJECT_NAME"
    echo "Project Type: $PROJECT_TYPE"
    echo "========================================"
    echo ""
    
    # Execute generator functions
    generate_makefile "$PROJECT_NAME" "$PROJECT_TYPE"
    create_cmake "$PROJECT_NAME" "$PROJECT_TYPE"
    setup_project "$PROJECT_NAME" "$PROJECT_TYPE"
    add_to_gitignore "$PROJECT_NAME"
    
    echo ""
    success_msg "Build configuration generated successfully!"
    echo ""
    info_msg "Next steps:"
    echo "  1. Run './setup.sh init' to initialize the project"
    echo "  2. Run './setup.sh build' to build the project"
    echo "  3. Run './setup.sh test' to run tests"
}

# Run main function with all arguments
main "$@"