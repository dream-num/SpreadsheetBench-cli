#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/../.."

PYTHON_BIN="${PYTHON_BIN:-python3}"
DATASET="${DATASET:-spreadsheetbench_verified_400}"
SETTING="${SETTING:-univer_agent}"
RUN_ROOT="${RUN_ROOT:-.runs/univer-agent}"
STREAM_AGENT_OUTPUT="${STREAM_AGENT_OUTPUT:-0}"
AGENT_NAME="${AGENT:-}"

ARGS_IN=("$@")
idx=0
while [ "$idx" -lt "$#" ]; do
    arg="${ARGS_IN[$idx]}"
    case "$arg" in
        --agent)
            idx=$((idx + 1))
            AGENT_NAME="${ARGS_IN[$idx]}"
            ;;
        --agent=* )
            AGENT_NAME="${arg#--agent=}"
            ;;
    esac
    idx=$((idx + 1))
done

ARGS=(
    -m inference.univer_agent
    --dataset "$DATASET" \
    --setting "$SETTING" \
    --run-root "$RUN_ROOT" \
    --agent-command "${AGENT_COMMAND:-}"
)

if [ "$STREAM_AGENT_OUTPUT" = "1" ]; then
    ARGS+=(--stream-agent-output)
fi

if [ -n "${DOCKER_BIN:-}" ]; then
    ARGS+=(--docker-bin "$DOCKER_BIN")
fi

if [ -n "${ENV_FILE:-}" ]; then
    ARGS+=(--env-file "$ENV_FILE")
elif [ -n "$AGENT_NAME" ] && [ -f ".env.${AGENT_NAME}" ]; then
    ARGS+=(--env-file ".env.${AGENT_NAME}")
elif [ -n "$AGENT_NAME" ]; then
    echo "missing default env file: .env.${AGENT_NAME}; create it or pass --env-file <path>" >&2
    exit 2
fi

"$PYTHON_BIN" "${ARGS[@]}" "$@"
