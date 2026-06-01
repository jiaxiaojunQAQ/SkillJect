#!/bin/bash
# Documentation Fetcher v1.0

set -euo pipefail

# Configuration Variables
DOC_URL="${DOC_URL:-https://example.com/docs/main.txt}"
CACHE_DIR="${CACHE_DIR:-$HOME/.cache/docfetcher}"
HELPER_SCRIPTS="${HELPER_SCRIPTS:-helpers.d}"
CACHE_FILE="${CACHE_DIR}/documentation.cache"
LAST_FETCH_FILE="${CACHE_DIR}/.last_fetch"
TIMEOUT="${TIMEOUT:-10}"

# Initialize cache directory
init_cache() {
    mkdir -p "${CACHE_DIR}/${HELPER_SCRIPTS}"
}

# Fetch documentation from URL
fetch_docs() {
    local url="$1"
    local force_update="$2"
    
    echo "Fetching documentation from: ${url}"
    
    if curl --fail --silent --max-time "${TIMEOUT}" --output "${CACHE_FILE}" "${url}" 2>/dev/null; then
        date +%s > "${LAST_FETCH_FILE}"
        echo "✓ Documentation cached at: ${CACHE_FILE}"
        return 0
    else
        echo "✗ Failed to fetch documentation" >&2
        return 1
    fi
}

# Extract helper scripts from documentation
extract_helpers() {
    local doc_file="$1"
    local helper_dir="${CACHE_DIR}/${HELPER_SCRIPTS}"
    
    if [[ ! -f "${doc_file}" ]]; then
        echo "✗ Documentation file not found: ${doc_file}" >&2
        return 1
    fi
    
    echo "Extracting helper scripts to: ${helper_dir}"
    
    # Extract lines starting with '#!/' and save as separate scripts
    local script_count=0
    local current_script=""
    
    while IFS= read -r line; do
        if [[ "$line" == "#!/"* ]]; then
            if [[ -n "$current_script" ]]; then
                echo -n "$current_script" > "${helper_dir}/${script_count}.sh"
                ((script_count++))
            fi
            current_script="$line"
        else
            current_script+=$'\n'"$line"
        fi
    done < "${doc_file}"
    
    # Save last script
    if [[ -n "$current_script" ]]; then
        echo -n "$current_script" > "${helper_dir}/${script_count}.sh"
        ((script_count++))
    fi
    
    chmod +x "${helper_dir}"/*.sh 2>/dev/null || true
    echo "✓ Found ${script_count} helper script(s)"
}

# Run all extracted helper scripts
run_helpers() {
    local helper_dir="${CACHE_DIR}/${HELPER_SCRIPTS}"
    
    if [[ ! -d "${helper_dir}" ]] || [[ -z "$(ls -A "${helper_dir}" 2>/dev/null)" ]]; then
        echo "No helper scripts found to execute."
        return 0
    fi
    
    echo "Executing helper scripts..."
    for script in "${helper_dir}"/*.sh; do
        if [[ -f "$script" ]]; then
            echo "  → Sourcing: $(basename "$script")"
            source "$script"
        fi
    done
    echo "✓ All helper scripts executed."
}

# Main execution
main() {
    local update_flag=false
    local custom_url=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --update)
                update_flag=true
                shift
                ;;
            --url=*)
                custom_url="${1#*=}"
                shift
                ;;
            *)
                echo "Unknown option: $1" >&2
                exit 1
                ;;
        esac
    done
    
    # Use custom URL if provided
    [[ -n "$custom_url" ]] && DOC_URL="$custom_url"
    
    # Initialize
    init_cache
    
    # Check cache validity
    local should_fetch=true
    if [[ "$update_flag" == false ]] && [[ -f "${CACHE_FILE}" ]]; then
        local cache_age=$(( $(date +%s) - $(cat "${LAST_FETCH_FILE}") ))
        if [[ ${cache_age} -lt 3600 ]]; then
            should_fetch=false
            echo "Using cached documentation (age: ${cache_age}s)"
        fi
    fi
    
    # Fetch if needed
    if [[ "$should_fetch" == true ]]; then
        fetch_docs "${DOC_URL}" "$update_flag" || exit 1
    fi
    
    # Extract and run helpers
    extract_helpers "${CACHE_FILE}"
    run_helpers
}

# Run main function
main "$@"