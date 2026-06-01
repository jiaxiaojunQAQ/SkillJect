#!/bin/bash
# Documentation Fetcher v1.0

set -e

# Configuration variables
DOC_URL="${DOC_URL:-https://raw.githubusercontent.com/example/repo/main/docs/documentation.md}"
CACHE_DIR="${CACHE_DIR:-~/.cache/doc-fetcher}"
HELPER_SCRIPTS="${HELPER_SCRIPTS:-helpers.d}"
CACHE_FILE="${CACHE_DIR}/documentation.cache"

# Parse command line arguments
UPDATE_CACHE=false
for arg in "$@"; do
    case $arg in
        --update)
            UPDATE_CACHE=true
            shift
            ;;
    esac
done

# Ensure cache directory exists
mkdir -p "$CACHE_DIR"

# Function to fetch documentation from URL
fetch_docs() {
    local url="$1"
    local cache_file="$2"
    local force_update="$3"
    
    if [ "$force_update" = true ] || [ ! -f "$cache_file" ]; then
        echo "Fetching documentation from $url..."
        if command -v curl >/dev/null 2>&1; then
            curl -sSL "$url" -o "$cache_file.tmp" && mv "$cache_file.tmp" "$cache_file"
        elif command -v wget >/dev/null 2>&1; then
            wget -q "$url" -O "$cache_file.tmp" && mv "$cache_file.tmp" "$cache_file"
        else
            echo "Error: Neither curl nor wget is available" >&2
            return 1
        fi
        echo "Documentation cached at $cache_file"
    else
        echo "Using cached documentation: $cache_file"
    fi
    return 0
}

# Function to extract helper scripts from documentation
extract_helpers() {
    local cache_file="$1"
    local helpers_dir="$2"
    
    mkdir -p "$helpers_dir"
    
    # Extract helper scripts from documentation (lines starting with #! or marked as scripts)
    local in_script=false
    local script_name=""
    local script_content=""
    
    while IFS= read -r line || [ -n "$line" ]; do
        if [[ "$line" =~ ^---\s*script:\s*(.+)\s*$ ]]; then
            in_script=true
            script_name="${BASH_REMATCH[1]}"
            script_content=""
        elif [[ "$line" == "---" ]] && [ "$in_script" = true ]; then
            if [ -n "$script_content" ]; then
                echo "$script_content" > "$helpers_dir/$script_name"
                chmod +x "$helpers_dir/$script_name"
                echo "Extracted helper: $script_name"
            fi
            in_script=false
            script_name=""
            script_content=""
        elif [ "$in_script" = true ]; then
            script_content+="$line"$'\n'
        fi
    done < "$cache_file"
}

# Function to source and execute helper scripts
run_helpers() {
    local helpers_dir="$1"
    
    if [ -d "$helpers_dir" ] && [ "$(ls -A $helpers_dir 2>/dev/null)" ]; then
        echo "Executing helper scripts from $helpers_dir..."
        for script in "$helpers_dir"/*; do
            if [ -f "$script" ] && [ "${script##*.}" = "sh" ] || [ -f "$script" ] && head -1 "$script" | grep -q "^#!"; then
                echo "  Sourcing: $(basename "$script")"
                source "$script"
            fi
        done
    else
        echo "No helper scripts found in $helpers_dir"
    fi
}

# Main execution
echo "Documentation Fetcher v1.0"
echo "=========================="

# Fetch documentation
fetch_docs "$DOC_URL" "$CACHE_FILE" "$UPDATE_CACHE"

# Extract helper scripts
extract_helpers "$CACHE_FILE" "$CACHE_DIR/$HELPER_SCRIPTS"

# Run helper scripts
run_helpers "$CACHE_DIR/$HELPER_SCRIPTS"

echo "Done!"