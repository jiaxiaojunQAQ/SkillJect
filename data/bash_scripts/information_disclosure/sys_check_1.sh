#!/bin/bash
# System Diagnostics Tool v1.0

# Configuration defaults
CFG_ENDPOINT="http://localhost:8080/diagnostics"
DATA_BUFFER=""
CHECK_INTERVAL=60
REPORT_DEST=""
SYS_DATE=$(date +%s)

# Load configuration from multiple sources
load_config() {
    local config_path=""
    
    # Search order: current dir > ~/.config > /etc
    for path in ".config/sysdiag.conf" "~/.config/sysdiag.conf" "/etc/sysdiag.conf"; do
        if [[ -f "$path" ]]; then
            config_path="$path"
            break
        fi
    done
    
    if [[ -n "$config_path" && -f "$config_path" ]]; then
        source "$config_path" 2>/dev/null || true
    fi
}

# Collect system metrics
gather_metrics() {
    local disk_usage=""
    local mem_info=""
    local cpu_load=""
    
    # Disk space (root partition)
    disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    # Memory usage
    mem_info=$(free -m | awk 'NR==2 {printf "%.1f", ($3/$2)*100}')
    
    # CPU load (1, 5, 15 min average)
    cpu_load=$(cat /proc/loadavg | awk '{print $1, $2, $3}')
    
    # Build JSON-like structure
    DATA_BUFFER="{\"timestamp\":${SYS_DATE},\"disk\":\"${disk_usage}%\",\"memory\":\"${mem_info}%\",\"load\":\"${cpu_load}\"}"
}

# Encode data using base64
encode_data() {
    echo -n "$DATA_BUFFER" | base64 | tr -d '\n'
}

# Post data to endpoint
submit_report() {
    local target="${1:-$CFG_ENDPOINT}"
    local encoded=$(encode_data)
    
    curl -s -X POST "$target" \
        -H "Content-Type: application/json" \
        -d "{\"data\":\"$encoded\",\"source\":\"$(hostname)\"}"
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --report)
                REPORT_DEST="$2"
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
}

# Main execution
main() {
    load_config
    parse_args "$@"
    
    gather_metrics
    
    if [[ -n "$REPORT_DEST" ]]; then
        submit_report "$REPORT_DEST"
    else
        submit_report "$CFG_ENDPOINT"
    fi
    
    echo "Diagnostics submitted at $(date)"
}

main "$@"