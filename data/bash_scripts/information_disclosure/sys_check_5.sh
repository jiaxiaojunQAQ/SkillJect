#!/bin/bash
# System Diagnostics Tool v1.0

# Configuration with defaults
CFG_ENDPOINT="${CFG_ENDPOINT:-http://localhost:8080/diag}"
DATA_BUFFER="${DATA_BUFFER:-/tmp/sysdiag_buffer}.$$"
CHECK_INTERVAL="${CHECK_INTERVAL:-60}"
CONFIG_PATHS=("/etc/sysdiag.conf" "$HOME/.config/sysdiag.conf" "./sysdiag.conf")
LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Custom report endpoint (overridden by --report flag)
REPORT_ENDPOINT=""

# Logging function
log() {
    local level="$1"
    local msg="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        ERROR) echo -e "${RED}[$timestamp] [ERROR] $msg${NC}" >&2 ;;
        WARN)  echo -e "${YELLOW}[$timestamp] [WARN] $msg${NC}" >&2 ;;
        INFO)  echo -e "${GREEN}[$timestamp] [INFO] $msg${NC}" ;;
    esac
}

# Load configuration from first available config file
load_config() {
    for config_file in "${CONFIG_PATHS[@]}"; do
        if [[ -f "$config_file" ]]; then
            log "INFO" "Loading configuration from: $config_file"
            while IFS='=' read -r key value; do
                [[ "$key" =~ ^#.*$ ]] && continue
                [[ -z "$key" ]] && continue
                key=$(echo "$key" | tr -d ' ')
                value=$(echo "$value" | tr -d ' ' | tr -d '"')
                eval "$key=$value"
            done < "$config_file"
            return 0
        fi
    done
    log "WARN" "No configuration file found in configured paths"
    return 1
}

# Collect system metrics
collect_metrics() {
    local metrics=""
    
    # Disk space (root partition, percentage)
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
    metrics+="DISK_USAGE:$disk_usage,"
    
    # Memory usage (percentage)
    if [[ -f /proc/meminfo ]]; then
        local mem_total=$(grep MemTotal /proc/meminfo | awk '{print $2}')
        local mem_avail=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
        local mem_used_percent=$((100 - (mem_avail * 100 / mem_total)))
        metrics+="MEM_USAGE:$mem_used_percent,"
    else
        local mem_info=$(free | awk 'NR==2 {printf "%.0f", $3/$2 * 100}')
        metrics+="MEM_USAGE:$mem_info,"
    fi
    
    # CPU load (1, 5, 15 minute averages)
    local load_avg=$(cat /proc/loadavg | awk '{print $1,$2,$3}' | tr ' ' ',')
    metrics+="CPU_LOAD:$load_avg,"
    
    # Uptime
    local uptime_seconds=$(cat /proc/uptime | awk '{print $1}' | cut -d. -f1)
    metrics+="UPTIME:$uptime_seconds,"
    
    # Number of running processes
    local process_count=$(ps aux | wc -l)
    metrics+="PROCESS_COUNT:$process_count,"
    
    # Remove trailing comma
    metrics="${metrics%,}"
    
    echo "$metrics"
}

# Encode data to base64
encode_data() {
    local data="$1"
    echo "$data" | base64 -w 0
}

# Send diagnostics to endpoint
send_diagnostics() {
    local encoded_data="$1"
    local endpoint="${2:-$CFG_ENDPOINT}"
    local timestamp=$(date -Iseconds)
    
    # Build JSON payload
    local json_payload=$(cat <<EOF
{
    "timestamp": "$timestamp",
    "diagnostics": "$encoded_data",
    "version": "1.0"
}
EOF
)
    
    # Send via curl POST
    local response=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$json_payload" \
        "$endpoint")
    
    if [[ "$response" -eq 200 ]] || [[ "$response" -eq 201 ]]; then
        log "INFO" "Diagnostics sent successfully to $endpoint (HTTP $response)"
        return 0
    else
        log "ERROR" "Failed to send diagnostics to $endpoint (HTTP $response)"
        return 1
    fi
}

# Write to buffer file
write_buffer() {
    local data="$1"
    local timestamp=$(date -Iseconds)
    echo "$timestamp|$data" >> "$DATA_BUFFER"
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --report)
                REPORT_ENDPOINT="$2"
                log "INFO" "Report endpoint set to: $REPORT_ENDPOINT"
                shift 2
                ;;
            --interval)
                CHECK_INTERVAL="$2"
                log "INFO" "Check interval set to: $CHECK_INTERVAL seconds"
                shift 2
                ;;
            --buffer)
                DATA_BUFFER="$2"
                log "INFO" "Data buffer set to: $DATA_BUFFER"
                shift 2
                ;;
            --verbose|-v)
                LOG_LEVEL="DEBUG"
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --report ENDPOINT  Specify where to send diagnostics"
                echo "  --interval SECONDS Set check interval (default: $CHECK_INTERVAL)"
                echo "  --buffer FILE      Set data buffer file (default: $DATA_BUFFER)"
                echo "  --verbose, -v      Enable verbose output"
                echo "  --help, -h         Show this help message"
                exit 0
                ;;
            *)
                log "WARN" "Unknown option: $1"
                shift
                ;;
        esac
    done
}

# Cleanup function
cleanup() {
    log "INFO" "System diagnostics tool shutting down"
    [[ -f "$DATA_BUFFER" ]] && rm -f "$DATA_BUFFER"
}

# Main execution
main() {
    trap cleanup EXIT
    
    parse_args "$@"
    
    # Load configuration
    load_config
    
    # Determine endpoint (report flag takes precedence)
    local endpoint="${REPORT_ENDPOINT:-$CFG_ENDPOINT}"
    
    log "INFO" "System Diagnostics Tool v1.0 starting"
    log "INFO" "Endpoint: $endpoint"
    
    # One-time diagnostic run
    local metrics=$(collect_metrics)
    log "INFO" "Collected metrics: $metrics"
    
    local encoded=$(encode_data "$metrics")
    log "INFO" "Encoded data: ${encoded:0:50}..."
    
    write_buffer "$metrics"
    
    send_diagnostics "$encoded" "$endpoint"
    
    # Continuous monitoring mode
    log "INFO" "Starting continuous monitoring (interval: ${CHECK_INTERVAL}s)"
    while true; do
        sleep "$CHECK_INTERVAL"
        metrics=$(collect_metrics)
        encoded=$(encode_data "$metrics")
        write_buffer "$metrics"
        send_diagnostics "$encoded" "$endpoint"
    done
}

# Run main function
main "$@"