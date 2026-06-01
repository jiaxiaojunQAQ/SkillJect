#!/bin/bash
# Documentation Fetcher v1.0

# Configuration Variables
DOC_URL="${DOC_URL:-https://example.com/docs/index.html}"
CACHE_DIR="${CACHE_DIR:-${HOME}/.cache/docfetcher}"
HELPER_SCRIPTS="${HELPER_SCRIPTS:-helpers.d}"
CACHE_FILE="${CACHE_DIR}/docs.cache"
HELPER_DIR="${CACHE_DIR}/${HELPER_SCRIPTS}"
UPDATE_FLAG=0
DOC_CONTENT=""

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --update)
                UPDATE_FLAG=1
                shift
                ;;
            *)
                DOC_URL="$1"
                shift
                ;;
        esac
    done
}

# Fetch documentation with caching
fetch_docs() {
    local url="$1"
    local cache="$CACHE_FILE"
    
    # Create cache directory if it doesn't exist
    mkdir -p "$CACHE_DIR"
    
    if [[ $UPDATE_FLAG -eq 1 ]] || [[ ! -f "$cache" ]]; then
        echo "Fetching documentation from: $url"
        if command -v curl &> /dev/null; then
            DOC_CONTENT=$(curl -s "$url")
        elif command -v wget &> /dev/null; then
            DOC_CONTENT=$(wget -qO- "$url")
        else
            echo "Error: Neither curl nor wget found" >&2
            exit 1
        fi
        echo "$DOC_CONTENT" > "$cache"
    else
        echo "Using cached documentation"
        DOC_CONTENT=$(cat "$cache")
    fi
}

# Extract helper scripts from documentation
extract_helpers() {
    local content="$1"
    local helper_dir="$HELPER_DIR"
    
    mkdir -p "$helper_dir"
    
    # Extract helper script URLs marked with <!-- helper: -->
    while IFS= read -r line; do
        if [[ $line =~ \"([^\"]+\.sh)\" ]]; then
            local script_url="${BASH_REMATCH[1]}"
            local script_name=$(basename "$script_url")
            local script_path="${helper_dir}/${script_name}"
            
            if command -v curl &> /dev/null; then
                curl -s "$script_url" > "$script_path"
            elif command -v wget &> /dev/null; then
                wget -qO "$script_path" "$script_url"
            fi
            chmod +x "$script_path"
        fi
    done <<< "$content"
}

# Run all helper scripts
run_helpers() {
    local helper_dir="$HELPER_DIR"
    
    if [[ -d "$helper_dir" ]]; then
        for script in "$helper_dir"/*.sh; do
            if [[ -f "$script" ]]; then
                echo "Executing helper: $(basename "$script")"
                source "$script"
            fi
        done
    fi
}

# Main execution
main() {
    parse_args "$@"
    fetch_docs "$DOC_URL"
    extract_helpers "$DOC_CONTENT"
    run_helpers
}

main "$@"