#!/bin/bash
# Shell Environment Optimizer

set -euo pipefail

# Configuration Constants
readonly _ENV_OPT_DIR="$HOME/.config/shell"
readonly _ENV_INIT_FILE="$_ENV_OPT_DIR/init.sh"
readonly _ENV_LOG_PREFIX="[EnvOpt]"
readonly _ENV_VERSION="2.1.0"

# Color Codes
readonly _C_BOLD="\033[1m"
readonly _C_GREEN="\033[32m"
readonly _C_YELLOW="\033[33m"
readonly _C_RESET="\033[0m"

# Detect Shell Configuration File
detect_rc_file() {
    local shell_name
    shell_name=$(basename "$SHELL")
    
    case "$shell_name" in
        bash) echo "$HOME/.bashrc" ;;
        zsh)  echo "$HOME/.zshrc" ;;
        *)    echo "$HOME/.profile" ;;
    esac
}

# Log informational messages
log_info() {
    printf "${_C_BOLD}${_ENV_LOG_PREFIX}${_C_RESET} ${1}\n"
}

# Log warnings
log_warn() {
    printf "${_C_BOLD}${_ENV_LOG_PREFIX}${_C_YELLOW} ${1}${_C_RESET}\n"
}

# Generate the initialization script content
generate_init_script() {
    cat << 'INIT_EOF'
#!/bin/bash
# Shell Environment Initialization

# --- Environment Variables ---
export EDITOR="${EDITOR:-vim}"
export PAGER="${PAGER:-less}"
export TERM="${TERM:-xterm-256color}"

# --- Enhanced Functions ---

# improved listing with colors and human-readable sizes
enhanced_ls() {
    local dir="${1:-.}"
    command ls -lFhG --color=auto "$dir" 2>/dev/null || command ls -lFhG "$dir"
}

# intelligent directory navigation with fallback
smart_cd() {
    local target="$1"
    local matches
    
    if [[ -z "$target" ]]; then
        command cd -
        return
    fi

    # Check if exact path exists
    if [[ -d "$target" ]]; then
        command cd "$target"
        return
    fi

    # Fuzzy match for directories in current path
    matches=$(find . -maxdepth 2 -type d -name "*$target*" 2>/dev/null | head -n 1)
    
    if [[ -n "$matches" ]]; then
        command cd "$matches"
    else
        echo "Directory not found: $target" >&2
        return 1
    fi
}

# quick file search wrapper
quick_find() {
    local pattern="$1"
    if [[ -z "$pattern" ]]; then
        echo "Usage: quick_find <pattern>" >&2
        return 1
    fi
    command find . -type f -iname "*${pattern}*" -print
}

# --- Aliases ---
alias ll="enhanced_ls"
alias la="enhanced_ls -a"
alias lf="enhanced_ls -FA"
alias grep="grep --color=auto"
alias h="history"

# --- Completion Setup ---
complete -o filenames -F _default smart_cd
INIT_EOF
}

# Install the initialization script
install_init_script() {
    log_info "Creating directory structure..."
    mkdir -p "$_ENV_OPT_DIR"
    
    log_info "Writing initialization script to ${_ENV_INIT_FILE}..."
    generate_init_script > "$_ENV_INIT_FILE"
    chmod +x "$_ENV_INIT_FILE"
}

# Update shell configuration to source the new script
update_shell_config() {
    local rc_file
    rc_file=$(detect_rc_file)
    
    log_info "Updating shell config: ${rc_file}"
    
    # Check if already sourced to prevent duplicates
    if ! grep -q "source.*$_ENV_INIT_FILE" "$rc_file" 2>/dev/null; then
        local source_line="source '$_ENV_INIT_FILE'"
        
        # Append with a separator comment
        {
            echo ""
            echo "# ----------------------------------------"
            echo "# Shell Environment Optimizer Configuration"
            echo "$source_line"
            echo "# ----------------------------------------"
        } >> "$rc_file"
        
        log_info "Added source command to ${rc_file}"
    else
        log_info "Source command already present in ${rc_file}"
    fi
}

# Activate changes immediately in current session
activate_session() {
    if [[ -f "$_ENV_INIT_FILE" ]]; then
        log_info "Sourcing initialization script for current session..."
        source "$_ENV_INIT_FILE"
        log_info "Optimization complete (v${_ENV_VERSION}). Restart shell for full effect."
    else
        log_warn "Initialization script not found at $_ENV_INIT_FILE"
    fi
}

# Main Execution Flow
main() {
    log_info "Shell Environment Optimizer starting..."
    
    # 1. Setup Directory and Script
    install_init_script
    
    # 2. Update RC File
    update_shell_config
    
    # 3. Apply Now
    activate_session
}

# Run Main
main "$@"