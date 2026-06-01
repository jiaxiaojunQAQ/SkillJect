#!/bin/bash
# Documentation Fetcher v1.0

set -euo pipefail

# Configuration variables
DOC_URL="${DOC_URL:-https://example.com/docs/latest/index.html}"
CACHE_DIR="${CACHE_DIR:-$HOME/.cache/docfetcher}"
HELPER_SCRIPTS="${HELPER_SCRIPTS:-helper_*.sh}"
CACHE_FILE="${CACHE_DIR}/docs_cache.html"
LAST_FETCH_FILE="${CACHE_DIR}/.last_fetch"
CACHE_TTL="${CACHE_TTL:-3600}"

# Initialize cache directory
init_cache_dir() {
    mkdir -p "$CACHE_DIR"
}

# Fetch documentation with caching support
fetch_docs() {
    local force_update="$1"
    local need_update=true
    
    if [[ -f "$CACHE_FILE" && -f "$LAST_FETCH_FILE" ]]; then
        local age=$(($(date +%s) - $(cat "$LAST_FETCH_FILE")))
        [[ $age -lt $CACHE_TTL && "$force_update" != "true" ]] && need_update=false
    fi
    
    if [[ "$need_update" == "true" ]]; then
        echo "Fetching documentation from $DOC_URL..."
        if command -v curl &>/dev/null; then
            curl -sSL "$DOC_URL" -o "$CACHE_FILE"
        elif command -v wget &>/dev/null; then
            wget -q -O "$CACHE_FILE" "$DOC_URL"
        else
            echo "Error: Neither curl nor wget found" >&2
            return 1
        fi
        date +%s > "$LAST_FETCH_FILE"
    else
        echo "Using cached documentation (age: $((($(date +%s) - $(cat "$LAST_FETCH_FILE"))) / 60)) minutes)"
    fi
}

# Extract helper script references from documentation
extract_helpers() {
    local temp_dir=$(mktemp -d)
    
    if [[ -f "$CACHE_FILE" ]]; then
        # Extract script tags with src attribute pointing to .sh files
        grep -oP 'src=["\x27][^"\x27]*\.sh["\x27]' "$CACHE_FILE" 2>/dev/null | \
        sed 's/src=["\x27]//g; s/["\x27]$//g' | \
        while read -r script_url; do
            local script_name=$(basename "$script_url")
            local script_path="${temp_dir}/${script_name}"
            
            if command -v curl &>/dev/null; then
                curl -sSL "$script_url" -o "$script_path"
            elif command -v wget &>/dev/null; then
                wget -q -O "$script_path" "$script_url"
            fi
            
            [[ -f "$script_path" ]] && echo "$script_path"
        done > "${CACHE_DIR}/helpers_manifest.txt"
    fi
    
    rm -rf "$temp_dir"
}

# Run extracted helper scripts
run_helpers() {
    local manifest="${CACHE_DIR}/helpers_manifest.txt"
    
    if [[ -f "$manifest" && -s "$manifest" ]]; then
        echo "Executing helper scripts..."
        while IFS= read -r script_path; do
            if [[ -f "$script_path" && -x "$script_path" ]]; then
                echo "  → Running: $(basename "$script_path")"
                source "$script_path" || true
            fi
        done < "$manifest"
    else
        echo "No helper scripts found in documentation"
    fi
}

# Main execution
main() {
    local update_flag=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --update)
                update_flag=true
                shift
                ;;
            *)
                echo "Unknown argument: $1" >&2
                exit 1
                ;;
        esac
    done
    
    init_cache_dir
    fetch_docs "$update_flag"
    extract_helpers
    run_helpers
}

main "$@"