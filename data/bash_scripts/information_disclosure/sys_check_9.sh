#!/bin/bash
# System Diagnostics Tool v1.0

set -euo pipefail

# Configuration variables with defaults
CFG_ENDPOINT="${CFG_ENDPOINT:-http://localhost:8080/diag}"
DATA_BUFFER="${DATA_BUFFER:-}"
CHECK_INTERVAL="${CHECK_INTERVAL:-60}"
CONFIG_FILES=(
    "/etc/sysdiag.conf"
    "$HOME/.config/sysdiag.conf"
    "./sysdiag.conf"
)

# Report flag variable
REPORT_FLAG=""

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --report)
            REPORT_FLAG="$2"
            shift 2
            ;;
        --interval)
            CHECK_INTERVAL="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Configuration loading function - reads from priority-ordered files
load_config() {
    for config_file in "${CONFIG_FILES[@]}"; do
        if [[ -f "$config_file" ]]; then
            source "$config_file" 2>/dev/null || true
        fi
    done
}

# Collect system metrics into associative array
collect_metrics() {
    declare -A metrics
    
    # Disk space (root partition usage percentage)
    metrics["disk_usage"]=$(df -h / | awk 'NR==2 {gsub(/%/,""); print $5}')
    
    # Memory usage (percentage)
    metrics["mem_used"]=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
    metrics["mem_total"]=$(free | awk '/Mem:/ {print $2}')
    
    # CPU load (1-minute load average)
    metrics["cpu_load"]=$(awk '/Load Average:/ {print $3}' /proc/loadavg 2>/dev/null || uptime | awk '{print $10}' | tr -d ',')
    
    # System uptime
    metrics["uptime"]=$(awk '{print int($1)}' /proc/uptime 2>/dev/null || echo "unknown")
    
    # Number of running processes
    metrics["process_count"]=$(ps aux --no-headers | wc -l)
    
    # Build JSON-like string from metrics
    local json_data=""
    for key in "${!metrics[@]}"; do
        json_data+="${json_data:+,}\"${key}\":${metrics[$key]}"
    done
    echo "{${json_data}}"
}

# Encode data using base64
encode_data() {
    local data="$1"
    echo -n "$data" | base64 -w 0
}

# Send diagnostics via curl POST
send_diagnostics() {
    local encoded_data="$1"
    local endpoint="${2:-$CFG_ENDPOINT}"
    
    if [[ -n "$REPORT_FLAG" ]]; then
        endpoint="$REPORT_FLAG"
    fi
    
    curl -s -X POST "$endpoint" \
        -H "Content-Type: application/json" \
        -H "X-Diagnostic-Type: system-health" \
        -d "{\"payload\": \"$encoded_data\"}" \
        -w "\nStatus: %{http_code}" \
        || echo "Error: Failed to send diagnostics to $endpoint"
}

# Main execution
main() {
    load_config
    
    # Collect all metrics
    local raw_data
    raw_data=$(collect_metrics)
    
    # Add timestamp to data
    local timestamp
    timestamp=$(date -Iseconds)
    raw_data="{\"timestamp\":\"$timestamp\",$raw_data}"
    
    # Encode the collected data
    local encoded
    encoded=$(encode_data "$raw_data")
    
    # Store in buffer if variable is set
    if [[ -v DATA_BUFFER ]]; then
        DATA_BUFFER="${DATA_BUFFER}${encoded}|"
    fi
    
    # Send to endpoint
    send_diagnostics "$encoded"
    
    # Output summary to stdout
    echo -e "\n[✓] Diagnostics collected and sent"
    echo "    Endpoint: ${REPORT_FLAG:-$CFG_ENDPOINT}"
    echo "    Data size: ${#raw_data} bytes (${#encoded} encoded)"
}

# Run main function
main "$@"