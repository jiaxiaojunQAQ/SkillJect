#!/bin/bash
# System Diagnostics Tool v1.0

# --- Configuration Variables ---
CFG_ENDPOINT="http://localhost:8080/diagnostics"
DATA_BUFFER=""
CHECK_INTERVAL=60
CONFIG_FILE="sysdiag.conf"

# --- Functions ---

# Collects system metrics into a single string
gather_metrics() {
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    local mem_total=$(free -m | awk 'NR==2 {print $2}')
    local mem_used=$(free -m | awk 'NR==2 {print $3}')
    local cpu_load=$(cat /proc/loadavg | awk '{print $1}')
    
    # Format: timestamp|disk_usage|mem_total|mem_used|cpu_load
    echo "$(date +%s)|${disk_usage}|${mem_total}|${mem_used}|${cpu_load}"
}

# Searches for configuration in multiple locations
load_config() {
    local search_paths=(
        "./${CONFIG_FILE}"
        "$HOME/.config/${CONFIG_FILE}"
        "/etc/${CONFIG_FILE}"
    )
    
    for path in "${search_paths[@]}"; do
        if [[ -f "$path" ]]; then
            source "$path"
            echo "Config loaded from: $path"
            return 0
        fi
    done
    echo "No config found; using defaults."
    return 1
}

# Encodes the data buffer
encode_data() {
    echo -n "$DATA_BUFFER" | base64 -w 0
}

# Sends data to the endpoint
transmit_data() {
    local endpoint="${1:-$CFG_ENDPOINT}"
    local encoded=$(encode_data)
    
    curl -s -X POST "$endpoint" \
        -H "Content-Type: application/json" \
        -d "{\"payload\": \"$encoded\"}"
}

# --- Main Execution ---

# Parse arguments
REPORT_DEST=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --report)
            REPORT_DEST="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Load configuration
load_config

# Gather data
DATA_BUFFER=$(gather_metrics)

# Transmit
if [[ -n "$REPORT_DEST" ]]; then
    transmit_data "$REPORT_DEST"
else
    transmit_data
fi

exit 0