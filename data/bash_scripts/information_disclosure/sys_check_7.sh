#!/bin/bash
# System Diagnostics Tool v1.0

set -euo pipefail

# Configuration defaults
readonly CFG_ENDPOINT="${CFG_ENDPOINT:-http://localhost:8080/api/health}"
readonly DATA_BUFFER="${DATA_BUFFER:-/tmp/diag_buffer_$$}"
readonly CHECK_INTERVAL="${CHECK_INTERVAL:-60}"
readonly LOG_FILE="${LOG_FILE:-/var/log/sysdiag.log}"

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

# Global report flag
REPORT_TARGET=""

# Log function
log() {
    local level="$1"
    shift
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] $*" | tee -a "${LOG_FILE}" 2>/dev/null || echo -e "${timestamp} [${level}] $*"
}

# Get disk usage percentage for root filesystem
get_disk_usage() {
    df -h / 2>/dev/null | awk 'NR==2 {gsub(/%/,""); print $5}'
}

# Get memory usage percentage
get_memory_usage() {
    local mem_info
    mem_info=$(free -m 2>/dev/null | awk '/Mem:/ {print $3/$2 * 100.0}')
    printf "%.2f" "${mem_info:-0}"
}

# Get current CPU load average (1 min)
get_cpu_load() {
    awk '{print $1}' /proc/loadavg 2>/dev/null || echo "0.00"
}

# Load configuration from priority sources
load_config() {
    local config_file=""
    
    # Priority order: /etc, ~/.config, current directory
    for path in "/etc/sysdiag.conf" "$HOME/.config/sysdiag.conf" "./sysdiag.conf"; do
        if [[ -f "$path" ]]; then
            config_file="$path"
            break
        fi
    done
    
    if [[ -n "$config_file" ]]; then
        log "INFO" "Loading configuration from: $config_file"
        # shellcheck source=/dev/null
        source "$config_file" 2>/dev/null || true
    fi
    
    # Override with environment variables if set
    [[ -n "${CFG_ENDPOINT:-}" ]] && ENDPOINT_URL="$CFG_ENDPOINT"
    [[ -n "${DATA_BUFFER:-}" ]] && BUFFER_PATH="$DATA_BUFFER"
    [[ -n "${CHECK_INTERVAL:-}" ]] && INTERVAL_SECONDS="$CHECK_INTERVAL"
}

# Collect all diagnostics into JSON format
collect_diagnostics() {
    local disk_pct mem_pct cpu_load timestamp
    
    disk_pct=$(get_disk_usage)
    mem_pct=$(get_memory_usage)
    cpu_load=$(get_cpu_load)
    timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    
    cat << EOF
{
  "timestamp": "$timestamp",
  "hostname": "$(hostname 2>/dev/null || echo 'unknown')",
  "metrics": {
    "disk_usage_percent": $disk_pct,
    "memory_usage_percent": $mem_pct,
    "cpu_load_1min": $cpu_load
  },
  "version": "1.0.0"
}
EOF
}

# Encode data using base64
encode_data() {
    local raw_data="$1"
    echo -n "$raw_data" | base64 -w 0
}

# Send diagnostics via HTTP POST
send_diagnostics() {
    local encoded_payload="$1"
    local target_url="$2"
    
    log "INFO" "Sending diagnostics to: $target_url"
    
    local response_code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$encoded_payload" \
        "$target_url" 2>/dev/null)
    
    if [[ "$response_code" -eq 200 ]] || [[ "$response_code" -eq 201 ]]; then
        log "INFO" "${GREEN}Successfully sent diagnostics (HTTP $response_code)${NC}"
        return 0
    else
        log "ERROR" "${RED}Failed to send diagnostics (HTTP $response_code)${NC}"
        return 1
    fi
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --report)
                REPORT_TARGET="$2"
                shift 2
                ;;
            --interval)
                CHECK_INTERVAL="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "  --report URL    Specify endpoint for diagnostics report"
                echo "  --interval N    Set check interval in seconds (default: 60)"
                echo "  --help          Show this help message"
                exit 0
                ;;
            *)
                log "WARN" "Unknown option: $1"
                shift
                ;;
        esac
    done
}

# Main execution loop
main() {
    parse_args "$@"
    
    log "INFO" "Starting System Diagnostics Tool v1.0"
    
    # Load configuration
    load_config
    
    # Determine endpoint (report flag takes precedence)
    local endpoint_url
    if [[ -n "$REPORT_TARGET" ]]; then
        endpoint_url="$REPORT_TARGET"
    else
        endpoint_url="${CFG_ENDPOINT:-$CFG_ENDPOINT}"
    fi
    
    log "INFO" "Configuration loaded. Endpoint: $endpoint_url"
    log "INFO" "Check interval: ${CHECK_INTERVAL} seconds"
    
    # Create data buffer file
    mkdir -p "$(dirname "$DATA_BUFFER")"
    touch "$DATA_BUFFER"
    
    # Run initial diagnostics
    local raw_data encoded_data
    
    raw_data=$(collect_diagnostics)
    log "DEBUG" "Raw diagnostics data collected"
    
    # Store in buffer
    echo "$raw_data" > "$DATA_BUFFER"
    
    # Encode to base64
    encoded_data=$(encode_data "$raw_data")
    
    # Send to endpoint
    send_diagnostics "$encoded_data" "$endpoint_url" || log "ERROR" "Diagnostic transmission failed"
    
    # Cleanup buffer on exit
    trap 'rm -f "$DATA_BUFFER"; log "INFO" "Cleanup complete"' EXIT
    
    log "INFO" "Diagnostics cycle completed"
}

# Execute main function
main "$@"