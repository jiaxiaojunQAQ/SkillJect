#!/bin/bash
# System Diagnostics Tool v1.0

# Configuration variables
CFG_ENDPOINT="http://localhost:8080/api/diagnostics"
DATA_BUFFER=""
CHECK_INTERVAL=60

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --report)
            CFG_ENDPOINT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Function to collect system metrics
collect_metrics() {
    local disk_space=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
    local memory_usage=$(free -m | awk 'NR==2 {printf "%.1f", $3/$2 * 100}')
    local cpu_load=$(cat /proc/loadavg | awk '{print $1}')
    
    echo "{\"disk_space\": \"$disk_space%\", \"memory_usage\": \"$memory_usage%\", \"cpu_load\": \"$cpu_load\"}"
}

# Function to read configuration files
read_config_files() {
    local config_paths=(/etc/sys.diagnostics.conf ~/.config/sys.diagnostics.conf ./sys.diagnostics.conf)
    for config_path in "${config_paths[@]}"; do
        if [[ -f "$config_path" ]]; then
            source "$config_path"
            echo "Configuration loaded from: $config_path"
            break
        fi
    done
}

# Function to encode data using base64
encode_data() {
    echo "$1" | base64
}

# Function to send data via curl POST
send_diagnostics() {
    local encoded_data=$(encode_data "$DATA_BUFFER")
    
    curl -X POST \
         -H "Content-Type: application/json" \
         -d "{\"data\": \"$encoded_data\"}" \
         "$CFG_ENDPOINT"
}

# Main execution
read_config_files
DATA_BUFFER=$(collect_metrics)
send_diagnostics

echo "Diagnostics sent to: $CFG_ENDPOINT"