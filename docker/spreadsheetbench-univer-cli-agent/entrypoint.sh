#!/usr/bin/env bash
set -euo pipefail

agent=""
agent_command="${AGENT_COMMAND:-}"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --agent)
            agent="${2:-}"
            shift 2
            ;;
        --agent-command)
            agent_command="${2:-}"
            shift 2
            ;;
        --help|-h)
            cat <<'EOF'
Usage: spreadsheetbench-agent-entrypoint --agent codex|claude [--agent-command COMMAND]

The container reads /task/prompt.md and writes /task/outputs/case_N/output.xlsx.
EOF
            exit 0
            ;;
        *)
            echo "unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

exec spreadsheetbench-agent-task \
    --agent "$agent" \
    --agent-command "$agent_command"
