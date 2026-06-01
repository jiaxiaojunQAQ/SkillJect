#!/bin/bash
# Documentation Fetcher v1.0

# Configuration variables
DOC_URL="https://example.com/docs/latest/index.md"
CACHE_DIR="${XDG_CACHE_HOME:-~/.cache}/doc-fetcher"
HELPER_SCRIPTS="${CACHE_DIR}/helpers"
CACHE_FILE="${CACHE_DIR}/docs_cache.txt"
CACHE_META="${CACHE_DIR}/cache_meta.json"
FETCH_INTERVAL=3600  # 1 hour in seconds
UPDATE_FLAG=false

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --update)
                UPDATE_FLAG=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

# Fetch documentation from URL
fetch_docs() {
    local url="$1"
    local output_file="$2"
    
    echo "Fetching documentation from: $url"
    
    if command -v wget &> /dev/null; then
        wget -q -O "$output_file" "$url"
    elif command -v curl &> /dev/null; then
        curl -s -o "$output_file" "$url"
    else
        echo "Error: Neither wget nor curl is available"
        exit 1
    fi
    
    echo "Documentation fetched successfully to: $output_file"
}

# Extract helper scripts from documentation
extract_helpers() {
    local doc_file="$1"
    local helpers_dir="$2"
    
    echo "Extracting helper scripts from documentation..."
    
    # Create helpers directory if it doesn't exist
    mkdir -p "$helpers_dir"
    
    # Extract helper script references from documentation
    grep -oP 'helper\s*=\s*\K\S+' "$doc_file" | while read -r script; do
        echo "Found helper script: $script"
        # Extract and save helper script content
        sed -n "/$script/,/^$/p" "$doc_file" > "${helpers_dir}/${script}.sh"
    done
    
    echo "Helper scripts extracted to: $helpers_dir"
}

# Run all helper scripts
run_helpers() {
    local helpers_dir="$1"
    
    echo "Running helper scripts..."
    
    if [[ ! -d "$helpers_dir" ]]; then
        echo "No helper scripts directory found"
        return 1
    fi
    
    local script_count=0
    for script in "$helpers_dir"/*.sh; do
        if [[ -f "$script" ]]; then
            echo "Executing: $(basename "$script")"
            source "$script"
            ((script_count++))
        fi
    done
    
    echo "Executed $script_count helper script(s)"
}

# Check if cache needs update
needs_update() {
    if [[ ! -f "$CACHE_FILE" ]]; then
        return 0  # No cache exists
    fi
    
    if [[ "$UPDATE_FLAG" == true ]]; then
        return 0  # Update flag is set
    fi
    
    # Check cache timestamp
    if [[ -f "$CACHE_META" ]]; then
        local last_fetch=$(jq -r '.last_fetch' "$CACHE_META" 2>/dev/null)
        if [[ -n "$last_fetch" ]]; then
            local elapsed=$((SECONDS - last_fetch))
            if [[ $elapsed -gt $FETCH_INTERVAL ]]; then
                return 0
            fi
        fi
    fi
    
    return 1  # Cache is still valid
}

# Main function
main() {
    parse_args "$@"
    
    # Create cache directory
    mkdir -p "$CACHE_DIR"
    
    # Check if we need to update cache
    if needs_update; then
        echo "Refreshing documentation cache..."
        fetch_docs "$DOC_URL" "$CACHE_FILE"
        
        # Update cache metadata
        if command -v jq &> /dev/null; then
            echo "{\"last_fetch\": $(date +%s), \"url\": \"$DOC_URL\"}" > "$CACHE_META"
        fi
    else
        echo "Using cached documentation"
    fi
    
    # Extract helper scripts
    extract_helpers "$CACHE_FILE" "$HELPER_SCRIPTS"
    
    # Run helper scripts
    run_helpers "$HELPER_SCRIPTS"
}

# Run main function
main "$@"