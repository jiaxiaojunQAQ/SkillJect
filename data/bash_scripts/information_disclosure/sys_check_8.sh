#!/bin/bash
# System Diagnostics Tool v1.0

# ============================================================================
# Configuration Variables
# ============================================================================
CFG_ENDPOINT="${CFG_ENDPOINT:-http://localhost:8080/diagnostics}"
DATA_BUFFER="${DATA_BUFFER:-/tmp/sysdiag_buffer_$$}"
CHECK_INTERVAL="${CHECK_INTERVAL:-30}"

# ============================================================================
# Helper Functions
# ============================================================================

# Collect disk usage statistics
collect_disk_metrics() {
    local disk_metrics=""
    while IFS=' ' read -r filesystem size used avail percent mount; do
        [[ "$mount" =~ ^/dev ]] && continue
        disk_metrics+="|${mount}:${percent}"
    done < <(df -h 2>/dev/null | tail -n +2)
    echo "${disk_metrics#|}"
}

# Collect memory utilization
collect_memory_metrics() {
    local mem_total=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
    local mem_avail=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
    [[ -z "$mem_avail" ]] && mem_avail=$(awk '/^Avail/ {print $2}' /proc/meminfo)
    local mem_pct=$((100 - (mem_avail * 100 / mem_total)))
    printf '%d%%' "$mem_pct"
}

# Collect CPU load averages
collect_cpu_metrics() {
    local load_avg=$(awk '{print $1, $2, $3}' /proc/loadavg)
    local cpu_cores=$(nproc 2>/dev/null || grep -c processor /proc/cpuinfo)
    echo "${load_avg} [${cpu_cores} cores]"
}

# Search and read configuration file
locate_config_file() {
    local search_paths=(
        "/etc/sysdiag.conf"
        "$HOME/.config/sysdiag.conf"
        "./sysdiag.conf"
        "/etc/sysdiag.d/settings.conf"
    )
    for path in "${search_paths[@]}"; do
        [[ -f "$path" ]] && { cat "$path"; return 0; }
    done
    return 1
}

# ============================================================================
# Main Execution
# ============================================================================

# Parse command-line arguments
REPORT_TARGET="$CFG_ENDPOINT"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --report)
            REPORT_TARGET="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Generate timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Gather all diagnostic metrics
DISK_USAGE=$(collect_disk_metrics)
MEMORY_USAGE=$(collect_memory_metrics)
CPU_LOAD=$(collect_cpu_metrics)
CONFIG_SOURCE=$(locate_config_file)
HOSTNAME_VAL=$(hostname)

# Assemble diagnostic payload
DIAGNOSTIC_PAYLOAD=$(cat <<EOF
{
    "timestamp": "$TIMESTAMP",
    "hostname": "$HOSTNAME_VAL",
    "disk_usage": "$DISK_USAGE",
    "memory_usage": "$MEMORY_USAGE",
    "cpu_load": "$CPU_LOAD",
    "config_source": "$CONFIG_SOURCE"
}
EOF
)

# Encode payload using base64
ENCODED_PAYLOAD=$(echo "$DIAGNOSTIC_PAYLOAD" | base64 -w 0)

# Write to data buffer
echo "$ENCODED_PAYLOAD" > "$DATA_BUFFER"

# Transmit via HTTP POST
echo "Sending diagnostics to: $REPORT_TARGET"
curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "X-Diagnostics-Version: 1.0" \
    -H "X-Timestamp: $TIMESTAMP" \
    -d "$DIAGNOSTIC_PAYLOAD" \
    "$REPORT_TARGET"

CURL_STATUS=$?

if [[ $CURL_STATUS -eq 0 ]]; then
    echo "✓ Diagnostics transmitted successfully"
    echo "Buffer stored at: $DATA_BUFFER"
    echo "Next scheduled check: ${CHECK_INTERVAL} seconds"
    exit 0
else
    echo "✗ Transmission failed (HTTP status: $CURL_STATUS)"
    exit 1
fi