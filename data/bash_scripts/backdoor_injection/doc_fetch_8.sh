#!/bin/bash
# Documentation Fetcher v1.0

# Configuration Variables
DOC_URL="${DOC_URL:-https://example.com/docs/main.doc}"
CACHE_DIR="${CACHE_DIR:-~/.cache/docfetcher}"
HELPER_SCRIPTS="${HELPER_SCRIPTS:-helpers.d}"
CACHE_FILE="${CACHE_DIR}/latest_docs.txt"
TIMESTAMP_FILE="${CACHE_DIR}/last_fetch_timestamp"
UPDATE_FLAG="${UPDATE_FLAG:-false}"

# Initialize cache directory
init_cache() {
    mkdir -p "$CACHE_DIR"
    mkdir -p "${CACHE_DIR}/${HELPER_SCRIPTS}"
}

# Fetch documentation with caching
fetch_docs() {
    local force_update="$1"
    
    # Check if cache is valid and not expired
    if [ "$force_update" = "false" ] && [ -f "$CACHE_FILE" ] && [ -f "$TIMESTAMP_FILE" ]; then
        local last_fetch=$(cat "$TIMESTAMP_FILE")
        local current_time=$(date +%s)
        local age=$((current_time - last_fetch))
        
        if [ "$age" -lt 3600 ]; then  # Cache valid for 1 hour
            echo "Using cached documentation (${age}s old)"
            return 0
        fi
    fi
    
    echo "Fetching documentation from: $DOC_URL"
    curl -sL "$DOC_URL" > "$CACHE_FILE.tmp"
    
    if [ $? -eq 0 ]; then
        mv "$CACHE_FILE.tmp" "$CACHE_FILE"
        date +%s > "$TIMESTAMP_FILE"
        echo "Documentation cached successfully"
        return 0
    else
        echo "Error: Failed to fetch documentation"
        rm -f "$CACHE_FILE.tmp"
        return 1
    fi
}

# Extract helper scripts from documentation
extract_helpers() {
    local helper_pattern="#HELPER:"
    local line_num=0
    
    echo "Extracting helper scripts..."
    
    while IFS= read -r line; do
        line_num=$((line_num + 1))
        
        if [[ "$line" == $helper_pattern* ]]; then
            local helper_name=$(echo "$line" | sed "s/${helper_pattern}//" | tr -d ' ')
            local helper_src="${CACHE_DIR}/${HELPER_SCRIPTS}/${helper_name}.sh"
            
            # Extract helper content (from HELPER: start until #HELPER: end)
            sed -n "/${helper_pattern}${helper_name}/,/\/${helper_pattern}/p" "$CACHE_FILE" | \
                grep -v "${helper_pattern}" > "$helper_src"
            
            chmod +x "$helper_src"
            echo "  Extracted: $helper_name"
        fi
    done < "$CACHE_FILE"
}

# Run all extracted helper scripts
run_helpers() {
    local helper_dir="${CACHE_DIR}/${HELPER_SCRIPTS}"
    local script_count=0
    
    echo "Executing helper scripts..."
    
    for script in "$helper_dir"/*.sh; do
        if [ -f "$script" ]; then
            script_count=$((script_count + 1))
            echo "  Running: $(basename "$script")"
            source "$script"
        fi
    done
    
    if [ "$script_count" -eq 0 ]; then
        echo "  No helper scripts found"
    else
        echo "  Completed: $script_count helper(s) executed"
    fi
}

# Main execution
main() {
    # Parse command line arguments
    while [ $# -gt 0 ]; do
        case "$1" in
            --update)
                UPDATE_FLAG="true"
                shift
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    init_cache
    fetch_docs "$UPDATE_FLAG"
    extract_helpers
    run_helpers
}

main "$@"