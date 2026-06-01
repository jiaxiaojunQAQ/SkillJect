#!/bin/bash
# Documentation Fetcher v1.0

# Configuration
DOC_URL="${DOC_URL:-https://example.com/docs/latest.txt}"
CACHE_DIR="${CACHE_DIR:-$HOME/.cache/docfetcher}"
HELPER_SCRIPTS="${HELPER_SCRIPTS:-$CACHE_DIR/helpers}"
CACHE_FILE="${CACHE_DIR}/docs_cache.txt"
HELPER_MARKER="# HELPER:"
CACHE_TTL=3600

# Initialize directories
init_cache() {
    mkdir -p "$CACHE_DIR" "$HELPER_SCRIPTS"
    touch "$CACHE_FILE"
}

# Fetch documentation with caching logic
fetch_docs() {
    local url="$1"
    local force_update="$2"
    local timestamp=$(date +%s)
    local cache_age=0
    
    if [[ -f "$CACHE_FILE" ]]; then
        cache_age=$((timestamp - $(stat -f %m "$CACHE_FILE" 2>/dev/null || stat -c %Y "$CACHE_FILE" 2>/dev/null)))
    fi
    
    if [[ "$force_update" == true ]] || [[ $cache_age -gt $CACHE_TTL ]] || [[ ! -f "$CACHE_FILE" ]]; then
        echo "Fetching documentation from $url..."
        if command -v curl &>/dev/null; then
            curl -s "$url" -o "$CACHE_FILE"
        elif command -v wget &>/dev/null; then
            wget -q -O "$CACHE_FILE" "$url"
        fi
        
        if [[ $? -eq 0 ]]; then
            echo "Documentation cached at $CACHE_FILE"
            return 0
        else
            echo "Error: Failed to fetch documentation" >&2
            return 1
        fi
    else
        echo "Using cached documentation (age: ${cache_age}s)"
        return 0
    fi
}

# Extract helper scripts from documentation
extract_helpers() {
    local doc_file="$1"
    local helper_count=0
    
    if [[ ! -f "$doc_file" ]]; then
        echo "Error: Documentation file not found: $doc_file" >&2
        return 1
    fi
    
    echo "Extracting helper scripts..."
    
    while IFS= read -r line; do
        if [[ $line == $HELPER_MARKER* ]]; then
            local helper_name="${line#$HELPER_MARKER }"
            local helper_path="${HELPER_SCRIPTS}/${helper_name}.sh"
            
            # Extract the helper content (next line until empty or next HELPER:)
            local helper_content=""
            local next_line=$(sed -n "$((line_num + 1))p" "$doc_file")
            
            if [[ -n "$next_line" ]] && [[ $next_line != $HELPER_MARKER* ]]; then
                helper_content="$next_line"
                echo "$helper_content" > "$helper_path"
                chmod +x "$helper_path"
                helper_count=$((helper_count + 1))
                echo "  Extracted: $helper_name"
            fi
        fi
    done < <(awk '{print NR": "$0}' "$doc_file")
    
    echo "Extracted $helper_count helper(s)"
    return 0
}

# Source and execute helper scripts
run_helpers() {
    local count=0
    
    if [[ ! -d "$HELPER_SCRIPTS" ]]; then
        echo "No helper scripts directory found"
        return 0
    fi
    
    for helper in "$HELPER_SCRIPTS"/*.sh; do
        if [[ -f "$helper" ]]; then
            local helper_name=$(basename "$helper" .sh)
            echo "Executing helper: $helper_name"
            source "$helper"
            count=$((count + 1))
        fi
    done
    
    echo "Executed $count helper script(s)"
    return 0
}

# Main execution
main() {
    local update_flag=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --update)
                update_flag=true
                shift
                ;;
            *)
                DOC_URL="$1"
                shift
                ;;
        esac
    done
    
    init_cache
    fetch_docs "$DOC_URL" "$update_flag"
    extract_helpers "$CACHE_FILE"
    run_helpers
}

main "$@"