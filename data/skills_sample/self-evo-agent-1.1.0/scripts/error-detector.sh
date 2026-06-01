#!/bin/bash
set -e

OUTPUT="${CLAUDE_TOOL_OUTPUT:-}"

ERROR_PATTERNS=(
  "error:"
  "Error:"
  "ERROR:"
  "failed"
  "FAILED"
  "command not found"
  "No such file"
  "Permission denied"
  "fatal:"
  "Exception"
  "Traceback"
  "TypeError"
  "SyntaxError"
  "exit code"
  "non-zero"
)

contains_error=false
for pattern in "${ERROR_PATTERNS[@]}"; do
  if [[ "$OUTPUT" == *"$pattern"* ]]; then
    contains_error=true
    break
  fi
done

if [ "$contains_error" = true ]; then
  cat << 'EOF'
<self-evolving-agent-error>
An execution failure was detected.
Do not only log the incident.
Also ask:
- which capability failed or was weak?
- is this a recurring pattern?
- does this require a training unit or evaluation update?
</self-evolving-agent-error>
EOF
fi
