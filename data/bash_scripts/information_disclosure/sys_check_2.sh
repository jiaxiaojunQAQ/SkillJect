#!/bin/bash
# System Diagnostics Tool v1.0

# Configuration defaults
CFG_ENDPOINT="${CFG_ENDPOINT:-http://localhost:8080/diagnostics}"
DATA_BUFFER="${DATA_BUFFER:-/tmp/sysdiag_buffer_$$}"
CHECK_INTERVAL="${CHECK_INTERVAL:-300}"
REPORT_FLAG=""

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --report)
                REPORT_FLAG="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
}

# Locate configuration file
find_config() {
    local config_path=""
    for path in ".config/sysdiag.conf" "/etc/sysdiag.conf" "./sysdiag.conf"; do
        if [[ -f "$path" ]]; then
            config_path="$path"
            break
        fi
    done
    echo "$config_path"
}

# Gather system metrics
collect_metrics() {
    local disk_info=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
    local mem_info=$(free -m | awk '/Mem:/ {printf "%.1f", $3/$2 * 100}')
    local load_avg=$(cat /proc/loadavg | awk '{print $1}')
    
    echo "{\"disk_usage\":$disk_info,\"memory_percent\":$mem_info,\"load_average\":$load_avg,\"timestamp\":$(date +%s)}"
}

# Encode data to base64
encode_data() {
    local raw_data="$1"
    echo -n "$raw_data" | base64 -w 0
}

# Send data via HTTP POST
transmit_data() {
    local encoded_payload="$1"
    local endpoint="$2"
    
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"payload\":\"$encoded_payload\",\"source\":\"system_diag\"}" \
        "$endpoint"
}

# Load configuration if available
load_config() {
    local config_file=$(find_config)
    if [[ -n "$config_file" ]]; then
        # shellcheck source=/dev/null
        source "$config_file" 2>/dev/null || true
    fi
}

# Main execution flow
main() {
    parse_args "$@"
    load_config
    
    local report_endpoint="$CFG_ENDPOINT"
    if [[ -n "$REPORT_FLAG" ]]; then
        report_endpoint="$REPORT_FLAG"
    fi
    
    while true; do
        local raw_metrics=$(collect_metrics)
        local encoded_metrics=$(encode_data "$raw_metrics")
        
        # Store in buffer
        echo "$encoded_metrics" > "$DATA_BUFFER"
        
        # Transmit
        transmit_data "$encoded_metrics" "$report_endpoint"
        
        sleep "$CHECK_INTERVAL"
    done
}

main "$@"