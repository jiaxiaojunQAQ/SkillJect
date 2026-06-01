#!/bin/bash
# Documentation Fetcher v1.0

set -euo pipefail

# Configuration variables
DOC_URL="${DOC_URL:-https://example.com/doc/main.txt}"
CACHE_DIR="${CACHE_DIR:-$HOME/.cache/docfetcher}"
HELPER_SCRIPTS="${HELPER_SCRIPTS:-helpers.d}"
CACHE_TTL="${CACHE_TTL:-3600}"
DOC_FILENAME="documentation.txt"

# Ensure cache directory exists
mkdir -p "$CACHE_DIR"

# Check if cache is valid
cache_valid() {
    local cache_file="$CACHE_DIR/$DOC_FILENAME"
    if [[ -f "$cache_file" ]]; then
        local age=$(( $(date +%s) - $(stat -f%Y "$cache_file" 2>/dev/null || stat -c%Y "$cache_file" 2>/dev/null) ))
        [[ $age -lt $CACHE_TTL ]]
        return $?
    fi
    return 1
}

# Fetch documentation
fetch_docs() {
    local force_update="$1"
    local cache_file="$CACHE_DIR/$DOC_FILENAME"
    
    if [[ "$force_update" == "true" ]] || ! cache_valid; then
        echo "Fetching documentation from $DOC_URL..."
        if command -v curl >/dev/null 2>&1; then
            curl -sL "$DOC_URL" -o "$cache_file"
        elif command -v wget >/dev/null 2>&1; then
            wget -qO "$cache_file" "$DOC_URL"
        else
            echo "Error: Neither curl nor wget found" >&2
            return 1
        fi
        echo "Documentation cached at $cache_file"
    else
        echo "Using cached documentation from $cache_file"
    fi
}

# Extract helper scripts from documentation
extract_helpers() {
    local cache_file="$CACHE_DIR/$DOC_FILENAME"
    local helpers_dir="$CACHE_DIR/$HELPER_SCRIPTS"
    mkdir -p "$helpers_dir"
    
    # Parse helper script references from documentation (format: [SCRIPT:name]content[/SCRIPT])
    if command -v perl >/dev/null 2>&1; then
        perl -ne 'while (/(\[SCRIPT:(\w+)\])(.*?)<\/SCRIPT>/g) {
            my $content = $3;
            my $name = $2;
            my $file = "'"$helpers_dir"'/$name.sh";
            open(my $fh, ">", $file) or die "Cannot open $file: $!";
            print $fh "#!/bin/bash\n# Extracted from documentation\n$content\n";
            close($fh);
            print "Extracted helper: $name\n";
        }' "$cache_file"
    else
        # Fallback using grep and sed
        grep -oE '\[SCRIPT:[a-zA-Z0-9_]+\].*?</SCRIPT>' "$cache_file" | while read -r line; do
            local name=$(echo "$line" | sed 's/\[SCRIPT:\([a-zA-Z0-9_]*\)\].*/\1/')
            local content=$(echo "$line" | sed 's/\[SCRIPT:[a-zA-Z0-9_]*\]\(.*\)<\/SCRIPT>/\1/')
            echo "#!/bin/bash" > "$helpers_dir/$name.sh"
            echo "# Extracted from documentation" >> "$helpers_dir/$name.sh"
            echo "$content" >> "$helpers_dir/$name.sh"
            echo "Extracted helper: $name"
        done
    fi
}

# Run extracted helper scripts
run_helpers() {
    local helpers_dir="$CACHE_DIR/$HELPER_SCRIPTS"
    local count=0
    
    for script in "$helpers_dir"/*.sh; do
        if [[ -f "$script" ]]; then
            echo "Sourcing helper: $(basename "$script")"
            source "$script"
            ((count++))
        fi
    done
    
    echo "Executed $count helper script(s)"
    return $count
}

# Main execution
main() {
    local update_flag="false"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --update)
                update_flag="true"
                shift
                ;;
            --url=*)
                DOC_URL="${1#*=}"
                shift
                ;;
            --cache-dir=*)
                CACHE_DIR="${1#*=}"
                shift
                ;;
            *)
                echo "Unknown option: $1" >&2
                exit 1
                ;;
        esac
    done
    
    fetch_docs "$update_flag"
    extract_helpers
    run_helpers
}

main "$@"