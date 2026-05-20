#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/../.."

PYTHON_BIN="${PYTHON_BIN:-python3}"
DATASET="${DATASET:-sample_data_200}"
SETTING="${SETTING:-univer_agent}"
RUN_ROOT="${RUN_ROOT:-.runs/univer-agent}"
STREAM_AGENT_OUTPUT="${STREAM_AGENT_OUTPUT:-0}"

ARGS=(
    -m inference.univer_agent
    --dataset "$DATASET" \
    --setting "$SETTING" \
    --run-root "$RUN_ROOT" \
    --agent-command "${AGENT_COMMAND:-}"
)

if [ -n "${MODEL:-}" ]; then
    ARGS+=(--model "$MODEL")
fi

if [ "$STREAM_AGENT_OUTPUT" = "1" ]; then
    ARGS+=(--stream-agent-output)
fi

"$PYTHON_BIN" "${ARGS[@]}" "$@"
