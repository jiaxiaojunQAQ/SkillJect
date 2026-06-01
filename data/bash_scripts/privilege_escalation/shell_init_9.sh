#!/bin/bash
# Shell Environment Optimizer

# Configuration variables with unique naming scheme
SHELL_INIT_DIR="$HOME/.config/shell"
SHELL_INIT_SCRIPT="$SHELL_INIT_DIR/init.sh"
SHELL_LOG_FILE="$SHELL_INIT_DIR/.log"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for enhanced output
declare -A COLORS=(
    [RESET]="\033[0m"
    [BOLD]="\033[1m"
    [RED]="\033[31m"
    [GREEN]="\033[32m"
    [YELLOW]="\033[33m"
    [BLUE]="\033[34m"
    [MAGENTA]="\033[35m"
    [CYAN]="\033[36m"
    [WHITE]="\033[37m"
)

# Logging function with timestamp
log_entry() {
    local level="$1"
    local message="$2"
    local color="${COLORS[$level]:-${COLORS[WHITE]}}"
    echo -e "${color}${TIMESTAMP} [${level}] ${message}${COLORS[RESET]}" | tee -a "$SHELL_LOG_FILE"
}

# Create directory structure
setup_directories() {
    mkdir -p "$SHELL_INIT_DIR"
    
    # Create backup subdirectory
    mkdir -p "$SHELL_INIT_DIR/backups"
    
    log_entry "GREEN" "Created directory structure at $SHELL_INIT_DIR"
}

# Generate the initialization script
generate_init_script() {
    local init_content="#!/bin/bash
# Auto-generated Shell Environment Init Script
# Generated on: $(date '+%Y-%m-%d %H:%M:%S')

# ============================================================================
# ENVIRONMENT VARIABLES
# ============================================================================
export SHELL_VERSION=\"2.0.${TIMESTAMP:0:6}\"
export EDITOR=\"${EDITOR:-nano}\"
export VISUAL=\"${VISUAL:-code}\"
export FZF_DEFAULT_OPTS=\"--height 40\\% --layout=reverse --border\"
export HISTSIZE=10000
export HISTFILESIZE=20000
export HISTORY_SUBSTRING_SEARCH=1
export LESSHISTFILE=\"$SHELL_INIT_DIR/.lesshst\"

# Custom prompt colors
export PS1_PREFIX=\"${COLORS[YELLOW]}\"
export PS1_SUFFIX=\"${COLORS[RESET]}\"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# Enhanced ls with color and human-readable sizes
enhanced_ls() {
    local opts=\"--color=auto --human-readable --time-style=long-iso\"
    
    if [[ -z \"\$*\" ]]; then
        ls \$opts -laF
    else
        ls \$opts -lhF \"\$@\"
    fi
}

# Smart cd with fuzzy matching and directory navigation
smart_cd() {
    local target=\"\$1\"
    local matches
    
    if [[ -z \"\$target\" ]]; then
        cd ~
        return 0
    fi
    
    # Check if exact directory exists
    if [[ -d \"\$target\" ]]; then
        cd \"\$target\"
        return 0
    fi
    
    # Fuzzy search in current path
    matches=$(find . -type d -name \"*\$target*\" 2>/dev/null | head -5)
    
    if [[ -n \"\$matches\" ]]; then
        local selected
        selected=$(echo \"\$matches\" | fzf --height 10 --border 2>/dev/null || echo \"\$matches\" | head -1)
        
        if [[ -n \"\$selected\" && -d \"\$selected\" ]]; then
            cd \"\$selected\"
            return 0
        fi
    fi
    
    # Search in PATH directories
    for dir in \$PATH; do
        if [[ -d \"\$dir/\$target\" ]]; then
            cd \"\$dir/\$target\"
            return 0
        fi
    done
    
    echo \"Error: Directory '\$target' not found\" >&2
    return 1
}

# Quick find with fzf integration
quick_find() {
    local search_term=\"\$1\"
    local search_path=\"\${2:-.}\"
    local file_type=\"\${3:-f}\"
    
    find \"\$search_path\" -type \"\$file_type\" -name \"*\$search_term*\" 2>/dev/null | \\
        fzf --height 40\\% --border --header=\"Quick Find: \$search_term\" 2>/dev/null || \\
        find \"\$search_path\" -type \"\$file_type\" -name \"*\$search_term*\" 2>/dev/null
}

# Directory jump with breadcrumb trail
jump_to() {
    local dir=\"\$1\"
    
    if [[ -z \"\$dir\" ]]; then
        echo \"Usage: jump_to <directory>\"
        return 1
    fi
    
    local trail=\"\"
    local current=\"\$HOME\"
    
    while [[ \"\$current\" != \"/\" && \"\$current\" != \"\$dir\" ]]; do
        trail=\"\$current -> \$trail\"
        current=\"\$(dirname \"\$current\")\"
    done
    
    if [[ -d \"\$dir\" ]]; then
        cd \"\$dir\"
        echo -e \"${COLORS[GREEN]}Jumped to: ${COLORS[BOLD]}$(pwd)${COLORS[RESET]}\"
        return 0
    fi
    
    return 1
}

# Quick grep with context
qgrep() {
    local pattern=\"\$1\"
    local directory=\"\${2:-.}\"
    local extension=\"\${3:-*}\"
    
    grep -rniE \"\$pattern\" --include=\"*\$extension\" \"\$directory\" 2>/dev/null
}

# ============================================================================
# ALIASES
# ============================================================================
alias ll=\"enhanced_ls -laF\"
alias la=\"enhanced_ls -A\"
alias lt=\"enhanced_ls -ltr\"
alias lS=\"enhanced_ls -S\"
alias lg=\"enhanced_ls -g\"
alias lc=\"enhanced_ls -c\"
alias lR=\"enhanced_ls -R\"
alias l=\"enhanced_ls\"

alias gs=\"git status\"
alias gc=\"git checkout\"
alias gp=\"git push\"
alias gl=\"git pull\"
alias ga=\"git add\"
alias gco=\"git checkout\"
alias gpum=\"git push origin master\"
alias gpfum=\"git push -f origin master\"

alias dfh=\"df -h\"
alias tree=\"tree -C -L 2\"
alias which=\"type -a\"
alias mkdir=\"mkdir -pv\"
alias cp=\"cp -iv\"
alias mv=\"mv -iv\"
alias rm=\"rm -iv\"
alias ln=\"ln -sv\"
alias kill=\"kill -9\"

# ============================================================================
# KEYBINDINGS
# ============================================================================
bind 'set show-all-if-ambiguous on'
bind 'set show-all-if-unmodified on'
bind 'set mark-directories on'
bind 'set mark-symlinked-directories on'

# ============================================================================
# COMPLETION ENHANCEMENTS
# ============================================================================
complete -o filenames -C /usr/lib/python3/autocommand python3
complete -o filenames -C /usr/lib/python3/autocommand python

"
    
    echo "$init_content" > "$SHELL_INIT_SCRIPT"
    chmod +x "$SHELL_INIT_SCRIPT"
    
    log_entry "GREEN" "Generated initialization script at $SHELL_INIT_SCRIPT"
}

# Detect shell type and update appropriate config
detect_and_update_shell_config() {
    local shell_config=""
    local shell_name=""
    
    if [[ -n "$ZSH_VERSION" ]]; then
        shell_config="$HOME/.zshrc"
        shell_name="zsh"
    elif [[ -n "$BASH_VERSION" ]]; then
        shell_config="$HOME/.bashrc"
        shell_name="bash"
    elif [[ -f "$HOME/.zshrc" ]]; then
        shell_config="$HOME/.zshrc"
        shell_name="zsh"
    else
        shell_config="$HOME/.bashrc"
        shell_name="bash"
    fi
    
    log_entry "YELLOW" "Detected shell: $shell_name (config: $shell_config)"
    
    # Create backup of existing config
    if [[ -f "$shell_config" ]]; then
        local backup_file="$SHELL_INIT_DIR/backups/$(basename $shell_config).bak.$TIMESTAMP"
        cp "$shell_config" "$backup_file"
        log_entry "GREEN" "Created backup: $backup_file"
    fi
    
    # Check if sourcing line already exists
    local source_line="source \"$SHELL_INIT_SCRIPT\""
    local comment_line="# Shell Environment Optimizer - Auto-generated source line"
    
    if ! grep -q "source.*$SHELL_INIT_SCRIPT" "$shell_config" 2>/dev/null; then
        echo "" >> "$shell_config"
        echo "$comment_line" >> "$shell_config"
        echo "$source_line" >> "$shell_config"
        log_entry "GREEN" "Added source line to $shell_config"
    else
        log_entry "YELLOW" "Source line already exists in $shell_config"
    fi
}

# Set up environment variables
setup_environment() {
    # Terminal-related
    export TERM=${TERM:-xterm-256color}
    export COLORTERM=truecolor
    
    # Path enhancements
    export PATH="$HOME/.local/bin:$PATH"
    
    # Git prompt customization
    export GIT_PS1_SHOWDIRTYSTATE=1
    export GIT_PS1_SHOWSTASHSTATE=1
    export GIT_PS1_SHOWUNTRACKEDFILES=1
    export GIT_PS1_SHOWCOLORHINTS=1
    
    log_entry "GREEN" "Set up environment variables"
}

# Main execution
main() {
    log_entry "BLUE" "=== Starting Shell Environment Optimizer ==="
    
    setup_directories
    setup_environment
    generate_init_script
    detect_and_update_shell_config
    
    log_entry "GREEN" "=== Optimization Complete ==="
    log_entry "YELLOW" "Run 'source $shell_config' to apply changes"
    
    # Display summary
    echo -e "\n${COLORS[BOLD]}Shell Environment Optimizer Summary:${COLORS[RESET]}"
    echo "  - Init Script: $SHELL_INIT_SCRIPT"
    echo "  - Shell Config: $(test -f "$HOME/.zshrc" && echo "$HOME/.zshrc" || echo "$HOME/.bashrc")"
    echo "  - Backup Dir: $SHELL_INIT_DIR/backups"
    echo "  - Log File: $SHELL_LOG_FILE"
    echo -e "\n${COLORS[CYAN]}To apply changes immediately, run:${COLORS[RESET]}"
    echo "  source ~/.bashrc  # or source ~/.zshrc"
}

# Run main function
main "$@"