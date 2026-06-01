#!/bin/bash
# System Diagnostics Tool v1.0

# Configuration variables
CFG_ENDPOINT="${CFG_ENDPOINT:-http://localhost:8080/api/diagnostics}"
DATA_BUFFER="${DATA_BUFFER:-}"
CHECK_INTERVAL="${CHECK_INTERVAL:-60}"
REPORT_PATH=""

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --report)
                REPORT_PATH="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
}

# Load configuration files
load_config() {
    local config_paths=(
        /etc/sysdiag.conf
        ~/.config/sysdiag.conf
        ./sysdiag.conf
    )
    
    for config_file in "${config_paths[@]}"; do
        if [[ -f "$config_file" ]]; then
            source "$config_file" 2>/dev/null
            break
        fi
    done
}

# Gather system metrics
collect_metrics() {
    local timestamp=$(date +%s)
    
    # Disk space (root partition)
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    local disk_total=$(df -h / | awk 'NR==2 {print $2}')
    local disk_avail=$(df -h / | awk 'NR==2 {print $4}')
    
    # Memory usage
    local mem_info=$(free -m | awk 'NR==2')
    local mem_total=$(echo $mem_info | awk '{print $2}')
    local mem_used=$(echo $mem_info | awk '{print $3}')
    local mem_percent=$((mem_used * 100 / mem_total))
    
    # CPU load
    local load_avg=$(cat /proc/loadavg | awk '{print $1, $2, $3}')
    local cpu_cores=$(nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo)
    
    # Build JSON payload
    cat << EOF
{
  "timestamp": ${timestamp},
  "hostname": "$(hostname)",
  "disk": {
    "usage_percent": ${disk_usage},
    "total": "${disk_total}",
    "available": "${disk_avail}"
  },
  "memory": {
    "total_mb": ${mem_total},
    "used_mb": ${mem_used},
    "usage_percent": ${mem_percent}
  },
  "cpu": {
    "load_1min": $(echo $load_avg | awk '{print $1}'),
    "load_5min": $(echo $load_avg | awk '{print $2}'),
    "load_15min": $(echo $load_avg | awk '{print $3}'),
    "cores": ${cpu_cores}
  }
}
EOF
}

# Encode data to base64
encode_data() {
    echo "$1" | base64 -w 0
}

# Send diagnostics to endpoint
send_diagnostics() {
    local endpoint="${1:-$CFG_ENDPOINT}"
    local encoded_data=$(encode_data "$DATA_BUFFER")
    
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "X-Diagnostic-Source: sysdiag-v1" \
        -d "$encoded_data" \
        "$endpoint"
}

# Main execution
main() {
    parse_args "$@"
    load_config
    
    # Collect and store metrics
    DATA_BUFFER=$(collect_metrics)
    
    # Determine destination
    if [[ -n "$REPORT_PATH" ]]; then
        local dest="$REPORT_PATH"
    else
        local dest="$CFG_ENDPOINT"
    fi
    
    # Transmit diagnostics
    send_diagnostics "$dest"
}

# Run main function
main "$@"