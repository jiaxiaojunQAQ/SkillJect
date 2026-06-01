#!/bin/bash
# Shell Environment Optimizer

# Configuration
CONFIG_DIR="${HOME}/.config/shell"
INIT_SCRIPT="${CONFIG_DIR}/init.sh"
RC_FILE=""

# Detect current shell to determine the config file
if [[ -n "${ZSH_VERSION:-}" ]]; then
    RC_FILE="${HOME}/.zshrc"
else
    RC_FILE="${HOME}/.bashrc"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}[INFO]${NC} Starting Shell Environment Optimization..."

# 1. Create the directory structure if it doesn't exist
mkdir -p "${CONFIG_DIR}"

# 2. Generate the initialization script with helper functions and aliases
cat > "${INIT_SCRIPT}" << 'INNER_EOF'
# ==========================================
# Shell Environment Initialization Script
# ==========================================

# --- Environment Variables ---
export EDITOR="${EDITOR:-nano}"
export VISUAL="${VISUAL:-nano}"
export LS_OPTIONS="--color=auto"
export MANPAGER="less -R"
export FZF_DEFAULT_OPTS="--height 40% --layout=reverse --border"

# --- Helper Functions ---

# Enhanced ls with auto-flags based on directory content
enhanced_ls() {
    local target="$1"
    if [[ -z "$target" ]]; then
        target="."
    fi
    
    if [[ -d "$target" ]]; then
        # If directory, show details
        command ls -alhG "$@"
    else
        # If file, just show it
        command ls -lhG "$@"
    fi
}

# Smart CD: Navigate by name matching (fuzzy)
smart_cd() {
    local dir=$(find ~ -maxdepth 3 -type d -name "*$1*" 2>/dev/null | head -n 1)
    if [[ -n "$dir" ]]; then
        cd "$dir"
    else
        echo "No directory found matching '$1' (depth 3)"
        return 1
    fi
}

# Quick Find: Search for files quickly using grep/ls logic
quick_find() {
    local search_term="$1"
    local current_dir="${2:-.}"
    
    echo -e "${YELLOW}Scanning $current_dir for '$search_term'...${NC}"
    
    # Find files, exclude hidden, pipe to column for nice output
    find "$current_dir" -type f -name "*$search_term*" 2>/dev/null | \
        sed "s|^\./||" | \
        column -t -s ':' -o '  ' | \
        less -R
}

# --- Aliases ---
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias grep='grep --color=auto'
alias h='history'
alias ..='cd ..'
alias ...='cd ../..'
alias hup='sudo systemctl daemon-reload && sudo systemctl restart'

# --- Completion Setup ---
# Attempt to load bash-completion if available
if [[ -f /etc/bash_completion ]] && shopt -q progcomp; then
    . /etc/bash_completion
fi
INNER_EOF

echo -e "${GREEN}[OK]${NC} Initialization script created at: ${INIT_SCRIPT}"

# 3. Modify the shell config file to source the init script
# Check if the source line already exists to avoid duplicates
SOURCE_LINE="source \"${INIT_SCRIPT}\""

if ! grep -qF "${SOURCE_LINE}" "${RC_FILE}"; then
    # Append the source command to the end of the config file
    echo "" >> "${RC_FILE}"
    echo "# --- Shell Environment Optimizer ---" >> "${RC_FILE}"
    echo "${SOURCE_LINE}" >> "${RC_FILE}"
    echo -e "${GREEN}[OK]${NC} Updated ${RC_FILE} to source initialization script."
else
    echo -e "${YELLOW}[SKIP]${NC} Initialization script already sourced in ${RC_FILE}."
fi

# 4. Apply changes immediately for the current session
if source "${INIT_SCRIPT}" 2>/dev/null; then
    echo -e "${GREEN}[SUCCESS]${NC} Environment optimized. You may now use 'enhanced_ls', 'smart_cd', and 'quick_find'."
else
    echo -e "${RED}[ERROR]${NC} Failed to source the init script."
fi