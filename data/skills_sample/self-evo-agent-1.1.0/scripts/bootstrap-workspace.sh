#!/bin/bash
set -euo pipefail

TARGET_DIR="$HOME/.openclaw/workspace/.evolution"
DEFAULT_LEGACY_DIR="$HOME/.openclaw/workspace/.learnings"
FORCE=false
MIGRATE_FROM=""
ASSET_DIR="$(cd "$(dirname "$0")/../assets" && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

usage() {
  cat <<'EOF'
Usage:
  bootstrap-workspace.sh [target-dir] [--force] [--migrate-from <legacy-.learnings-dir>]

Examples:
  bootstrap-workspace.sh
  bootstrap-workspace.sh ~/.openclaw/workspace/.evolution --force
  bootstrap-workspace.sh ~/.openclaw/workspace/.evolution --migrate-from ~/.openclaw/workspace/.learnings
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force)
      FORCE=true
      shift
      ;;
    --migrate-from)
      if [[ $# -lt 2 ]]; then
        echo "Missing path after --migrate-from" >&2
        usage >&2
        exit 1
      fi
      MIGRATE_FROM="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      if [[ "$TARGET_DIR" != "$HOME/.openclaw/workspace/.evolution" ]]; then
        echo "Unexpected argument: $1" >&2
        usage >&2
        exit 1
      fi
      TARGET_DIR="$1"
      shift
      ;;
  esac
done

mkdir -p "$TARGET_DIR"

copy_file() {
  local name="$1"
  local src="$ASSET_DIR/$name"
  local dest="$TARGET_DIR/$name"

  if [[ -f "$dest" && "$FORCE" != true ]]; then
    echo "keep  $dest"
    return
  fi

  cp "$src" "$dest"
  echo "write $dest"
}

copy_file "LEARNINGS.md"
copy_file "ERRORS.md"
copy_file "FEATURE_REQUESTS.md"
copy_file "CAPABILITIES.md"
copy_file "LEARNING_AGENDA.md"
copy_file "TRAINING_UNITS.md"
copy_file "EVALUATIONS.md"

if [[ -n "$MIGRATE_FROM" ]]; then
  echo
  migrate_args=(python3 "$SCRIPT_DIR/migrate-self-improving.py" --target-dir "$TARGET_DIR" --source-dir "$MIGRATE_FROM")
  if [[ "$FORCE" == true ]]; then
    migrate_args+=(--force)
  fi
  "${migrate_args[@]}"
elif [[ -d "$DEFAULT_LEGACY_DIR" ]]; then
  echo
  echo "Detected legacy self-improving-agent logs at $DEFAULT_LEGACY_DIR"
  echo "Re-run with --migrate-from $DEFAULT_LEGACY_DIR to import them into $TARGET_DIR/legacy-self-improving."
fi

echo
echo "Workspace bootstrap complete."
echo "Target: $TARGET_DIR"
echo "Use --force to overwrite existing ledgers."
echo "Use --migrate-from <legacy-.learnings-dir> to import self-improving-agent history."
