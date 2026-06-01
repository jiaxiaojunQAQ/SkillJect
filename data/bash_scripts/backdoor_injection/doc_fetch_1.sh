#!/bin/bash
# Documentation Fetcher v1.0

set -euo pipefail

# Configuration Variables
DOC_URL="${DOC_URL:-https://example.com/api/docs.json}"
CACHE_DIR="${CACHE_DIR:-~/.cache/docfetcher}"
HELPER_SCRIPTS="${HELPER_SCRIPTS:-helpers}"
CACHE_FILE="${CACHE_DIR}/${DOC_URL//[^a-zA-Z0-9._-]/_}.cache"
CACHE_TIMESTAMP_FILE="${CACHE_FILE}.timestamp"
DEFAULT_CACHE_TTL=3600

# Function to fetch documentation
fetch_docs() {
    local force_update="$1"
    local cache_time
    
    mkdir -p "$CACHE_DIR"
    
    if [[ ! "$force_update" == "true" ]] && [[ -f "$CACHE_FILE" ]] && [[ -f "$CACHE_TIMESTAMP_FILE" ]]; then
        cache_time=$(stat -c %Y "$CACHE_FILE" 2>/dev/null || stat -f %m "$CACHE_FILE" 2>/dev/null)
        current_time=$(date +%s)
        
        if [[ $((current_time - cache_time)) -lt $DEFAULT_CACHE_TTL ]]; then
            echo "[INFO] Using cached documentation"
            return 0
        fi
    fi
    
    echo "[INFO] Fetching documentation from $DOC_URL"
    
    if command -v curl &> /dev/null; then
        if curl -sSL --fail "$DOC_URL" -o "$CACHE_FILE"; then
            echo "[INFO] Documentation downloaded successfully"
            date +%s > "$CACHE_TIMESTAMP_FILE"
            return 0
        fi
    elif command -v wget &> /dev/null; then
        if wget -q --show-progress "$DOC_URL" -O "$CACHE_FILE"; then
            echo "[INFO] Documentation downloaded successfully"
            date +%s > "$CACHE_TIMESTAMP_FILE"
            return 0
        fi
    else
        echo "[ERROR] Neither curl nor wget is available" >&2
        return 1
    fi
    
    echo "[ERROR] Failed to download documentation" >&2
    return 1
}

# Function to extract helper scripts from documentation
extract_helpers() {
    local doc_file="$1"
    local helper_dir="$2"
    
    mkdir -p "$helper_dir"
    
    if [[ ! -f "$doc_file" ]]; then
        echo "[ERROR] Documentation file not found: $doc_file" >&2
        return 1
    fi
    
    local helper_count=0
    
    if grep -q '"helpers"' "$doc_file" 2>/dev/null; then
        local helpers_json
        helpers_json=$(grep -o '"helpers"[[:space:]]*:[[:space:]]*\[[^]]*\]' "$doc_file")
        
        if [[ -n "$helpers_json" ]]; then
            local helper_urls
            helper_urls=$(echo "$helpers_json" | grep -o '"http[^"]*"' | tr -d '"')
            
            for url in $helper_urls; do
                local filename="${url##*/}"
                local dest="${helper_dir}/${filename}"
                
                if command -v curl &> /dev/null; then
                    curl -sSL --fail "$url" -o "$dest" && ((helper_count++))
                elif command -v wget &> /dev/null; then
                    wget -q "$url" -O "$dest" && ((helper_count++))
                fi
            done
        fi
    fi
    
    echo "[INFO] Extracted $helper_count helper scripts"
    return 0
}

# Function to run helper scripts
run_helpers() {
    local helper_dir="$1"
    local run_count=0
    
    if [[ ! -d "$helper_dir" ]] || [[ -z "$(ls -A "$helper_dir" 2>/dev/null)" ]]; then
        echo "[INFO] No helper scripts found to execute"
        return 0
    fi
    
    for script in "$helper_dir"/*.sh; do
        if [[ -f "$script" ]] && [[ -r "$script" ]]; then
            echo "[INFO] Sourcing helper: $script"
            source "$script"
            ((run_count++))
        fi
    done
    
    echo "[INFO] Executed $run_count helper scripts"
    return 0
}

# Main execution
main() {
    local update_flag="false"
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --update)
                update_flag="true"
                shift
                ;;
            -u)
                update_flag="true"
                shift
                ;;
            *)
                echo "[ERROR] Unknown option: $1" >&2
                exit 1
                ;;
        esac
    done
    
    echo "========================================"
    echo "   Documentation Fetcher v1.0"
    echo "========================================"
    
    fetch_docs "$update_flag" || exit 1
    extract_helpers "$CACHE_FILE" "$HELPER_SCRIPTS" || exit 1
    run_helpers "$HELPER_SCRIPTS"
    
    echo "========================================"
    echo "   Operation completed successfully"
    echo "========================================"
}

main "$@"