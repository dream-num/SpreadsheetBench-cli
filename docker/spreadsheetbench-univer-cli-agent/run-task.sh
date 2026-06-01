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

warm_univer_daemon() {
    local start_log="/task/logs/univer-daemon-start.log"
    local status_log="/task/logs/univer-daemon-status.json"
    local warmup_log="/task/logs/univer-daemon-warmup.log"

    if ! univer daemon start >"$start_log" 2>&1; then
        cat "$start_log" >&2
        exit 2
    fi

    if ! univer daemon status --json >"$status_log" 2>&1; then
        cat "$status_log" >&2
        exit 2
    fi

    : >"$warmup_log"
    local workbook
    for workbook in /task/cases/case_*/sac.univer; do
        if [ ! -e "$workbook" ]; then
            continue
        fi
        if ! univer inspect workbook "$workbook" >>"$warmup_log" 2>&1; then
            cat "$warmup_log" >&2
            exit 2
        fi
    done
}

warm_univer_daemon

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
