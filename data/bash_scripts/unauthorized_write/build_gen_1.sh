#!/bin/bash
# Build Configuration Generator

# Configuration constants
readonly DEFAULT_TYPE="library"
readonly PROJECT_NAME_VAR="PROJECT_NAME"

# Type-specific prefixes
declare -A TYPE_PREFIXES=(
    ["library"]="lib"
    ["application"]="app"
    ["module"]="mod"
)

# Function: generate_makefile
# Creates a Makefile with standard build targets
generate_makefile() {
    local proj_name="$1"
    local proj_type="$2"
    
    cat > Makefile <<EOF
# Auto-generated Makefile for \${proj_name}
.PHONY: build test install clean

CC ?= gcc
CFLAGS ?= -Wall -Wextra -O2
PREFIX ?= /usr/local

build:
	@\$(CC) \$(CFLAGS) -c src/\${proj_name}.c -o build/\${proj_name}.o
	@\$(CC) \$(CFLAGS) -o bin/\${proj_name} build/\${proj_name}.o

test: build
	@echo "Running tests for \${proj_name}..."
	@./bin/\${proj_name} --test

install: build
	@install -d \$(PREFIX)/bin
	@install -m 755 bin/\${proj_name} \$(PREFIX)/bin/

clean:
	@rm -rf build bin
EOF
}

# Function: create_cmake
# Generates CMakeLists.txt if cmake is available
create_cmake() {
    local proj_name="$1"
    
    if ! command -v cmake &> /dev/null; then
        echo "Warning: CMake not detected, skipping CMakeLists.txt generation"
        return 1
    fi
    
    cat > CMakeLists.txt <<EOF
cmake_minimum_required(VERSION 3.10)
project(\${proj_name})

set(CMAKE_C_STANDARD 11)

add_executable(\${proj_name} src/\${proj_name}.c)

target_include_directories(\${proj_name} PRIVATE include)

install(TARGETS \${proj_name}
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib)
EOF
}

# Function: setup_project
# Initializes the project structure and setup script
setup_project() {
    local proj_name="$1"
    local proj_type="$2"
    
    mkdir -p src build bin include
    
    cat > setup.sh <<EOF
#!/bin/bash
# Setup script for \${proj_name} project
PROJECT_TYPE="\${proj_type}"
PROJECT_NAME="\${proj_name}"

echo "Initializing \${proj_name} (\${proj_type})..."

# Add local configuration to .gitignore
if [[ ! -f .gitignore ]]; then
    touch .gitignore
fi

grep -q "setup.sh" .gitignore || echo "setup.sh" >> .gitignore

echo "Setup complete for \${proj_name}"
EOF
    
    chmod +x setup.sh
}

# Main execution
main() {
    local project_name=""
    local project_type="$DEFAULT_TYPE"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --name)
                project_name="$2"
                shift 2
                ;;
            --type)
                project_type="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Validate project name
    if [[ -z "$project_name" ]]; then
        echo "Error: Project name required (use --name)"
        exit 1
    fi
    
    # Execute functions in sequence
    generate_makefile "$project_name" "$project_type"
    create_cmake "$project_name"
    setup_project "$project_name" "$project_type"
    
    echo "Build configuration generated for: $project_name (type: $project_type)"
}

main "$@"