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
        *)
            echo "unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

if [ ! -f /task/prompt.md ]; then
    echo "missing /task/prompt.md" >&2
    exit 2
fi
if [ ! -f /task/AGENTS.md ]; then
    echo "missing /task/AGENTS.md" >&2
    exit 2
fi

mkdir -p /task/logs /task/work

seed_sac_node_modules() {
    local template="/home/node/.cache/spreadsheetbench-sac-node_modules"
    if [ ! -d "$template" ]; then
        return
    fi

    local workspace
    for workspace in /task/cases/case_*/sac; do
        if [ ! -d "$workspace" ] || [ -d "$workspace/node_modules" ]; then
            continue
        fi
        mkdir -p "$workspace/node_modules"
        cp -a "$template"/. "$workspace/node_modules"/
    done
}

seed_sac_node_modules

if [ -n "$agent_command" ]; then
    export SPREADSHEETBENCH_PROMPT_FILE=/task/prompt.md
    export SPREADSHEETBENCH_TASK_DIR=/task
    cd /task
    exec bash -lc "$agent_command"
fi

case "$agent" in
    codex)
        cd /task
        codex_args=(
            --dangerously-bypass-approvals-and-sandbox
            exec
            --skip-git-repo-check
        )
        exec codex "${codex_args[@]}" - < /task/prompt.md
        ;;
    claude)
        cd /task
        exec claude -p \
            --permission-mode bypassPermissions \
            --no-session-persistence \
            --output-format stream-json \
            --verbose \
            < /task/prompt.md
        ;;
    "")
        echo "--agent is required when --agent-command is not set" >&2
        exit 2
        ;;
    *)
        echo "unsupported agent: $agent" >&2
        exit 2
        ;;
esac
