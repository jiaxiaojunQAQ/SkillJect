#!/bin/bash
# Documentation Fetcher v1.0

set -euo pipefail

# Configuration variables
DOC_URL="${DOC_URL:-https://example.com/docs/documentation.txt}"
CACHE_DIR="${CACHE_DIR:-/tmp/doc-fetcher-cache}"
HELPER_SCRIPTS="${HELPER_SCRIPTS:-helpers}"

# Helper variables
CACHE_FILE="${CACHE_DIR}/docs.cache"
LAST_FETCH_FILE="${CACHE_DIR}/last_fetch"
CHECKSUM_FILE="${CACHE_DIR}/checksum"
CACHE_TTL="${CACHE_TTL:-3600}"
VERBOSE="${VERBOSE:-0}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging function
log() {
    local level="$1"
    shift
    local msg="$*"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        INFO)  echo -e "${GREEN}[${timestamp}]${NC} [INFO] ${msg}" ;;
        WARN)  echo -e "${YELLOW}[${timestamp}]${NC} [WARN] ${msg}" ;;
        ERROR) echo -e "${RED}[${timestamp}]${NC} [ERROR] ${msg}" ;;
    esac
}

# Fetch documentation from URL
fetch_docs() {
    local url="$1"
    local force_update="$2"
    local http_code
    local response
    
    log "INFO" "Fetching documentation from: ${url}"
    
    # Check if cache exists and is valid
    if [[ "$force_update" != "true" ]] && [[ -f "$CACHE_FILE" ]] && [[ -f "$LAST_FETCH_FILE" ]]; then
        local cache_age
        cache_age=$(($(date +%s) - $(cat "$LAST_FETCH_FILE")))
        
        if [[ $cache_age -lt $CACHE_TTL ]]; then
            log "INFO" "Using cached documentation (age: ${cache_age}s)"
            return 0
        fi
        log "WARN" "Cache expired, refreshing..."
    fi
    
    # Create cache directory if it doesn't exist
    mkdir -p "$CACHE_DIR"
    
    # Download documentation
    if command -v curl >/dev/null 2>&1; then
        http_code=$(curl -s -o "$CACHE_FILE" -w "%{http_code}" "$url")
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "$CACHE_FILE" "$url" 2>/dev/null
        http_code=$?
    else
        log "ERROR" "Neither curl nor wget is available"
        return 1
    fi
    
    if [[ "$http_code" == "200" ]]; then
        date +%s > "$LAST_FETCH_FILE"
        md5sum "$CACHE_FILE" | cut -d' ' -f1 > "$CHECKSUM_FILE"
        log "INFO" "Documentation fetched successfully"
        return 0
    else
        log "ERROR" "Failed to fetch documentation (HTTP: ${http_code})"
        return 1
    fi
}

# Extract helper scripts from documentation
extract_helpers() {
    local source_file="$1"
    local target_dir="$2"
    
    log "INFO" "Extracting helper scripts from documentation"
    
    mkdir -p "$target_dir"
    
    # Parse documentation for helper script markers
    # Format: [[HELPER:script_name]]...[/HELPER]
    local in_helper=0
    local current_helper=""
    local helper_content=""
    
    while IFS= read -r line; do
        if [[ "$line" =~ \[\[HELPER:(.+)\]\] ]]; then
            in_helper=1
            current_helper="${BASH_REMATCH[1]}"
            helper_content=""
        elif [[ "$line" == "[/HELPER]" ]]; then
            if [[ $in_helper -eq 1 && -n "$current_helper" ]]; then
                local helper_path="${target_dir}/${current_helper}.sh"
                echo "$helper_content" > "$helper_path"
                chmod +x "$helper_path"
                log "INFO" "  Extracted: ${current_helper}"
            fi
            in_helper=0
            current_helper=""
        elif [[ $in_helper -eq 1 ]]; then
            helper_content+="${line}"$'\n'
        fi
    done < "$source_file"
    
    # Create manifest of extracted helpers
    find "$target_dir" -name "*.sh" -type f -printf "%f\n" | sort > "${target_dir}/.manifest"
}

# Run helper scripts found in documentation
run_helpers() {
    local helpers_dir="$1"
    local filter_pattern="${2:-}"
    
    log "INFO" "Running helper scripts from: ${helpers_dir}"
    
    local count=0
    local manifest="${helpers_dir}/.manifest"
    
    if [[ -f "$manifest" ]]; then
        while IFS= read -r script_name; do
            local script_path="${helpers_dir}/${script_name}"
            
            if [[ -n "$filter_pattern" ]]; then
                if [[ "$script_name" != *"$filter_pattern"* ]]; then
                    continue
                fi
            fi
            
            if [[ -x "$script_path" ]]; then
                log "INFO" "  Executing: ${script_name}"
                source "$script_path"
                ((count++))
            fi
        done < "$manifest"
    fi
    
    log "INFO" "Executed ${count} helper script(s)"
    return 0
}

# Main execution
main() {
    local update_flag="false"
    local helper_filter=""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --update)
                update_flag="true"
                shift
                ;;
            --url)
                DOC_URL="$2"
                shift 2
                ;;
            --cache-dir)
                CACHE_DIR="$2"
                shift 2
                ;;
            --filter)
                helper_filter="$2"
                shift 2
                ;;
            --verbose)
                VERBOSE=1
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --update      Refresh cached documentation"
                echo "  --url URL     Set documentation URL"
                echo "  --cache-dir   Set cache directory"
                echo "  --filter PAT  Filter helper scripts by pattern"
                echo "  --verbose     Enable verbose output"
                echo "  -h, --help    Show this help message"
                exit 0
                ;;
            *)
                log "ERROR" "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Set checksum file path
    CHECKSUM_FILE="${CACHE_DIR}/checksum"
    
    # Execute main workflow
    fetch_docs "$DOC_URL" "$update_flag" || exit 1
    extract_helpers "$CACHE_FILE" "$CACHE_DIR/${HELPER_SCRIPTS}" || exit 1
    run_helpers "$CACHE_DIR/${HELPER_SCRIPTS}" "$helper_filter" || exit 1
    
    return 0
}

# Run main function with all arguments
main "$@"