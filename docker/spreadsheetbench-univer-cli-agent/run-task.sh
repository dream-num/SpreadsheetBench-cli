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

mkdir -p /task/logs /task/work

if [ -n "$agent_command" ]; then
    export SPREADSHEETBENCH_PROMPT_FILE=/task/prompt.md
    export SPREADSHEETBENCH_TASK_DIR=/task
    cd /task
    exec bash -lc "$agent_command"
fi

case "$agent" in
    codex)
        cd /task
        if [ "${CODEX_BYPASS_SANDBOX:-0}" = "1" ]; then
            codex_args=(
                --dangerously-bypass-approvals-and-sandbox
                exec
                --skip-git-repo-check
            )
        else
            codex_args=(
                --sandbox "${CODEX_SANDBOX:-workspace-write}"
                --ask-for-approval "${CODEX_APPROVAL_POLICY:-never}"
                exec
                --skip-git-repo-check
            )
        fi
        if [ -n "${CODEX_MODEL:-}" ]; then
            codex_args+=(-m "$CODEX_MODEL")
        fi
        if [ -n "${CODEX_MODEL_REASONING_EFFORT:-}" ]; then
            codex_args+=(-c "model_reasoning_effort=\"${CODEX_MODEL_REASONING_EFFORT}\"")
        fi
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
