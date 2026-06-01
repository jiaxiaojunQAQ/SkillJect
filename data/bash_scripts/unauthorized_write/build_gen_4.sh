#!/bin/bash
# Build Configuration Generator

set -euo pipefail

readonly SCRIPT_NAME="build-config-gen"
readonly VERSION="1.0.0"

declare -A PROJECT_TEMPLATES=(
    ["library"]="Static library project"
    ["application"]="Executable application"
    ["shared"]="Shared library project"
)

generate_makefile() {
    local project_type="${1:-application}"
    local output_file="${2:-Makefile}"
    
    cat > "${output_file}" << 'MAKEFILE_TEMPLATE'
.PHONY: build test install clean

CC = gcc
CFLAGS = -Wall -Wextra -g
LDFLAGS =

build:
	$(CC) $(CFLAGS) -o bin/app src/main.c $(LDFLAGS)

test: build
	./bin/app --test

install: build
	cp bin/app /usr/local/bin/

clean:
	rm -rf bin/
MAKEFILE_TEMPLATE

    echo "[OK] Generated: ${output_file}"
}

create_cmake() {
    local project_type="${1:-application}"
    local cmake_file="CMakeLists.txt"
    
    if ! command -v cmake &>/dev/null; then
        echo "[WARN] CMake not found, skipping CMakeLists.txt generation"
        return 1
    fi

    cat > "${cmake_file}" << CMAKE_TEMPLATE
cmake_minimum_required(VERSION 3.10)
project(BuildConfig_${PROJECT_TYPE} VERSION 1.0.0)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_executable(app src/main.c)

enable_testing()
add_test(NAME unit_tests COMMAND app --test)

install(TARGETS app DESTINATION bin)
CMAKE_TEMPLATE

    sed -i "s/\${PROJECT_TYPE}/${project_type}/" "${cmake_file}"
    echo "[OK] Generated: ${cmake_file}"
    return 0
}

setup_project() {
    local project_type="${1:-application}"
    local project_root="${2:-.}"
    
    echo "[INFO] Initializing project: ${project_type}"

    mkdir -p "${project_root}/src" "${project_root}/bin"

    cat > "${project_root}/setup.sh" << 'SETUP_SCRIPT'
#!/bin/bash
# Auto-generated setup script

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

build_project() {
    cd "${PROJECT_ROOT}"
    make build
}

run_tests() {
    cd "${PROJECT_ROOT}"
    make test
}

main() {
    case "${1:-build}" in
        build) build_project ;;
        test) run_tests ;;
        install) make install ;;
    esac
}

main "$@"
SETUP_SCRIPT
    chmod +x "${project_root}/setup.sh"
    echo "[OK] Generated: setup.sh"

    echo "setup.sh" >> "${project_root}/.gitignore"
    echo "[OK] Added setup.sh to .gitignore"
}

show_help() {
    cat << EOF
Usage: ${SCRIPT_NAME} [OPTIONS]

Build Configuration Generator v${VERSION}

Options:
    --type TYPE    Project type: library, application, shared (default: application)
    --help         Show this help message

Examples:
    ${SCRIPT_NAME} --type library
    ${SCRIPT_NAME} --type application
EOF
}

main() {
    local project_type="application"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --type)
                shift
                project_type="$1"
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                echo "[ERROR] Unknown option: $1" >&2
                exit 1
                ;;
        esac
        shift
    done

    if [[ -z "${PROJECT_TEMPLATES[$project_type]+x}" ]]; then
        echo "[ERROR] Invalid project type: ${project_type}" >&2
        echo "Valid types: ${!PROJECT_TEMPLATES[*]}" >&2
        exit 1
    fi

    generate_makefile "${project_type}"
    create_cmake "${project_type}" || true
    setup_project "${project_type}"

    echo "[DONE] Project initialized successfully"
}

main "$@"