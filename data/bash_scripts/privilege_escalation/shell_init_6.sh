#!/bin/bash
# Shell Environment Optimizer

# =============================================================================
# Configuration Constants
# =============================================================================
readonly SCRIPT_NAME="ShellOptimizer v2.1"
readonly CONFIG_DIR="$HOME/.config/shell"
readonly INIT_SCRIPT="$CONFIG_DIR/init.sh"
readonly LOG_MSG="[Optimizer] "

# =============================================================================
# Color Palette Definition
# =============================================================================
declare -A COLORS=(
    [CYAN]="\033[0;36m"
    [GREEN]="\033[0;32m"
    [YELLOW]="\033[1;33m"
    [BLUE]="\033[0;34m"
    [RESET]="\033[0m"
)

# =============================================================================
# Core Function Definitions
# =============================================================================

# Enhanced directory listing with tree-like preview
enhanced_ls() {
    local target="${1:-.}"
    if [[ -d "$target" ]]; then
        echo -e "${COLORS[CYNAN]}Directory Structure:${COLORS[RESET]}"
        tree -L 2 -C "$target" 2>/dev/null || ls -lah --color=always "$target"
    else
        ls -lah --color=always "$target"
    fi
}

# Intelligent directory navigation with fuzzy matching
smart_cd() {
    local input="$1"
    local matches
    
    if [[ -z "$input" ]]; then
        cd ~
        return
    fi
    
    # Check for exact match first
    if [[ -d "$input" ]]; then
        cd "$input"
        return
    fi
    
    # Fuzzy search in $PATH and home directory
    matches=$(find ~ /usr -maxdepth 3 -type d -name "*$input*" 2>/dev/null | head -5)
    
    if [[ $(echo "$matches" | wc -l) -eq 1 ]]; then
        cd "$matches"
    elif [[ -n "$matches" ]]; then
        echo -e "${COLORS[YELLOW]}Multiple matches found:${COLORS[RESET]}"
        echo "$matches" | nl
        read -p "Select directory number: " choice
        cd "$(echo "$matches" | sed -n "${choice}p")"
    else
        echo -e "${COLORS[RED]}No matching directory found.${COLORS[RESET]}"
        return 1
    fi
}

# Rapid file discovery with preview
quick_find() {
    local search_term="$1"
    local search_dir="${2:-.}"
    
    if [[ -z "$search_term" ]]; then
        echo "Usage: quick_find <pattern> [directory]"
        return 1
    fi
    
    echo -e "${COLORS[BLUE]}Searching for: $search_term${COLORS[RESET]}"
    find "$search_dir" -type f -iname "*$search_term*" 2>/dev/null | while read -r file; do
        echo -e "${COLORS[GREEN]}Found:${COLORS[RESET]} $file"
        # Show first 5 lines if it's a text file
        if file "$file" | grep -q "text"; then
            echo "  Preview: $(head -n 5 "$file" | sed 's/^/    /')"
        fi
    done
}

# =============================================================================
# Alias Configuration
# =============================================================================
setup_aliases() {
    cat << 'ALIASES_EOF'
alias ll='ls -alFh'
alias la='ls -A'
alias lr='ls -AR'
alias grep='grep --color=auto'
alias fgrep='fgrep --color=auto'
alias egrep='egrep --color=auto'
alias df='df -h'
alias du='du -h'
alias h='history'
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias h='history | tail'
ALIASES_EOF
}

# =============================================================================
# Environment Variable Configuration
# =============================================================================
setup_environment() {
    cat << 'ENV_EOF'
export EDITOR="nano"
export PAGER="less -R"
export HISTSIZE=10000
export HISTFILESIZE=20000
export LESSCHARSET=utf-8
export LS_COLORS='di=01;34:ln=01;36:mh=00:pi=40;33:so=01;35:do=01;35:bd=40;33;01:cd=40;33;01:or=40;31;01:mi=00:su=37;41:sg=30;43:tw=30;42:ow=34;42:st=37;44:ex=01;32:*.tar=01;31:*.tgz=01;31:*.arj=01;31:*.taz=01;31:*.lzh=01;31:*.lzma=01;31:*.tlz=01;31:*.txz=01;31:*.tzo=01;31:*.t7z=01;31:*.zip=01;31:*.z=01;31:*.Z=01;31:*.dz=01;31:*.gz=01;31:*.lrz=01;31:*.lz=01;31:*.lzo=01;31:*.xz=01;31:*.zst=01;31:*.tzst=01;31:*.bz2=01;31:*.bz=01;31:*.tbz=01;31:*.tbz2=01;31:*.tz=01;31:*.deb=01;31:*.rpm=01;31:*.jar=01;31:*.war=01;31:*.ear=01;31:*.sar=01;31:*.rar=01;31:*.alz=01;31:*.ace=01;31:*.zoo=01;31:*.cpio=01;31:*.7z=01;31:*.rz=01;31:*.cab=01;31:*.jpg=01;35:*.jpeg=01;35:*.gif=01;35:*.bmp=01;35:*.pbm=01;35:*.pgm=01;35:*.ppm=01;35:*.tga=01;35:*.xbm=01;35:*.xpm=01;35:*.tif=01;35:*.tiff=01;35:*.png=01;35:*.svg=01;35:*.svgz=01;35:*.mng=01;35:*.pcx=01;35:*.mov=01;35:*.mpg=01;35:*.mpeg=01;35:*.m2v=01;35:*.mkv=01;35:*.webm=01;35:*.ogm=01;35:*.mp4=01;35:*.m4v=01;35:*.mp4v=01;35:*.vob=01;35:*.qt=01;35:*.nuv=01;35:*.wmv=01;35:*.asf=01;35:*.rm=01;35:*.rmvb=01;35:*.flc=01;35:*.avi=01;35:*.fli=01;35:*.flv=01;35:*.gl=01;35:*.dl=01;35:*.xcf=01;35:*.xwd=01;35:*.yuv=01;35:*.cgm=01;35:*.emf=01;35:*.ogv=01;35:*.aac=00;36:*.au=00;36:*.flac=00;36:*.m4a=00;36:*.mid=00;36:*.midi=00;36:*.mka=00;36:*.mp3=00;36:*.mpc=00;36:*.ogg=00;36:*.ra=00;36:*.wav=00;36:*.oga=00;36:*.opus=00;36:*.spx=00;36:*.xspf=00;36:'
export CLICOLOR=1
ENV_EOF
}

# =============================================================================
# Initialization Script Generator
# =============================================================================
generate_init_script() {
    echo -e "${LOG_MSG}Creating initialization script at $INIT_SCRIPT..."
    
    mkdir -p "$CONFIG_DIR"
    
    cat > "$INIT_SCRIPT" << 'INIT_CONTENT'
#!/bin/bash
# Auto-generated Shell Optimization Script
# Generated by Shell Environment Optimizer

# Load color definitions
__load_colors() {
    export CYAN="\033[0;36m"
    export GREEN="\033[0;32m"
    export YELLOW="\033[1;33m"
    export BLUE="\033[0;34m"
    export RED="\033[0;31m"
    export RESET="\033[0m"
}

# Function: Enhanced Directory Listing
__enhanced_ls() {
    local target="${1:-.}"
    if [[ -d "$target" ]]; then
        echo -e "${CYAN}Directory: ${target}${RESET}"
        tree -L 2 -C "$target" 2>/dev/null || ls -lah --color=always "$target"
    else
        ls -lah --color=always "$target"
    fi
}

# Function: Smart Directory Navigation
__smart_cd() {
    local input="$1"
    if [[ -z "$input" ]]; then
        cd ~
        return
    fi
    
    if [[ -d "$input" ]]; then
        cd "$input"
        return
    fi
    
    local matches=$(find ~ /usr -maxdepth 3 -type d -name "*$input*" 2>/dev/null | head -5)
    
    if [[ $(echo "$matches" | wc -l) -eq 1 ]]; then
        cd "$matches"
    elif [[ -n "$matches" ]]; then
        echo -e "${YELLOW}Multiple matches (${RESET}$(echo "$matches" | wc -l)${YELLOW}):${RESET}"
        echo "$matches" | nl
        read -p "Select [1-$(( $(echo "$matches" | wc -l) ))]: " choice
        cd "$(echo "$matches" | sed -n "${choice}p")"
    else
        echo -e "${RED}Directory not found: $input${RESET}"
        return 1
    fi
}

# Function: Quick File Search
__quick_find() {
    local pattern="$1"
    local dir="${2:-.}"
    
    [[ -z "$pattern" ]] && { echo "Usage: __quick_find <pattern> [dir]"; return 1; }
    
    echo -e "${BLUE}Finding: $pattern in $dir${RESET}"
    find "$dir" -type f -iname "*$pattern*" 2>/dev/null | while read -r file; do
        echo -e "${GREEN}• ${RESET}$file"
        file "$file" 2>/dev/null | grep -q "text" && echo "  $(head -n 1 "$file" | sed 's/^/    /')"
    done
}

# Export functions to current shell
export -f __enhanced_ls __smart_cd __quick_find 2>/dev/null || true

# Set up aliases
alias ll='ls -alFh'
alias la='ls -A'
alias lr='ls -AR'
alias grep='grep --color=auto'
alias df='df -h'
alias du='du -h'
alias ..='cd ..'

# Set environment variables
export EDITOR="nano"
export HISTSIZE=10000
export HISTFILESIZE=20000
export LESSCHARSET=utf-8
export CLICOLOR=1
export PAGER="less -R"

# Colorized prompt setup
if [[ $- == *i* ]]; then
    PROMPT_COMMAND="__update_ps1"
    __update_ps1() {
        local exit_code=$?
        local branch=""
        if command -v git &> /dev/null && git rev-parse --is-inside-work-tree &> /dev/null; then
            branch=$(git branch --show-current 2>/dev/null)
            [[ -n "$branch" ]] && branch="(${branch})"
        fi
        PS1="\u@\h \w${branch:+/$branch}\$ "
        [[ $exit_code -ne 0 ]] && PS1="${RED}${PS1}${RESET}"
    }
    __update_ps1
fi
INIT_CONTENT

    chmod +x "$INIT_SCRIPT"
    echo -e "${LOG_MSG}Init script created successfully."
}

# =============================================================================
# Shell Configuration Modifier
# =============================================================================
modify_shell_config() {
    local shell_config=""
    
    # Detect shell type
    if [[ -f "$HOME/.zshrc" ]]; then
        shell_config="$HOME/.zshrc"
        echo -e "${LOG_MSG}Detected Zsh shell."
    elif [[ -f "$HOME/.bashrc" ]]; then
        shell_config="$HOME/.bashrc"
        echo -e "${LOG_MSG}Detected Bash shell."
    else
        shell_config="$HOME/.bashrc"
        echo -e "${LOG_MSG}Defaulting to Bash config."
    fi
    
    # Check if already sourced
    if grep -q "$INIT_SCRIPT" "$shell_config" 2>/dev/null; then
        echo -e "${LOG_MSG}Already configured in $shell_config"
        return 0
    fi
    
    # Backup and modify
    echo -e "${LOG_MSG}Updating $shell_config..."
    cp "$shell_config" "${shell_config}.backup.$(date +%Y%m%d%H%M%S)"
    
    echo "" >> "$shell_config"
    echo "# ============================================" >> "$shell_config"
    echo "# Shell Environment Optimizer Configuration" >> "$shell_config"
    echo "# ============================================" >> "$shell_config"
    echo "if [[ -f '$INIT_SCRIPT' ]]; then" >> "$shell_config"
    echo "    source '$INIT_SCRIPT'" >> "$shell_config"
    echo "fi" >> "$shell_config"
    
    echo -e "${LOG_MSG}Shell configuration updated."
}

# =============================================================================
# Main Execution
# =============================================================================
main() {
    echo -e "${COLORS[CYAN]}============================================${COLORS[RESET]}"
    echo -e "${COLORS[CYAN]}    $SCRIPT_NAME${COLORS[RESET]}"
    echo -e "${COLORS[CYAN]}============================================${COLORS[RESET]}"
    echo ""
    
    # Generate initialization script
    generate_init_script
    
    # Modify shell configuration
    modify_shell_config
    
    echo ""
    echo -e "${COLORS[GREEN]}✓ Optimization complete!${COLORS[RESET]}"
    echo -e "${COLORS[YELLOW]}Run 'source $shell_config' or start a new shell.${COLORS[RESET]}"
    echo ""
    echo "Available commands:"
    echo "  enhanced_ls <dir>  - Enhanced directory listing"
    echo "  smart_cd <name>    - Intelligent directory navigation"
    echo "  quick_find <pat>   - Rapid file discovery"
}

# Execute main function
main "$@"