#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -z "${PYTHON_BIN:-}" ] && [ -x ".venv/bin/python" ]; then
    PYTHON_BIN="$PWD/.venv/bin/python"
else
    PYTHON_BIN="${PYTHON_BIN:-python3}"
fi
DATASET_NAME="${DATASET:-sample_data_200}"
SETTING_NAME="${SETTING:-univer_agent}"
AGENT_NAME=""
MODEL_NAME="${MODEL:-}"
ENV_FILE_NAME="${ENV_FILE:-}"
SHOW_HELP=0
EVAL_SELECTION_ARGS=()

ARGS=("$@")
idx=0
while [ "$idx" -lt "$#" ]; do
    arg="${ARGS[$idx]}"
    case "$arg" in
        -h|--help)
            SHOW_HELP=1
            ;;
        --dataset)
            idx=$((idx + 1))
            DATASET_NAME="${ARGS[$idx]}"
            ;;
        --setting)
            idx=$((idx + 1))
            SETTING_NAME="${ARGS[$idx]}"
            ;;
        --agent)
            idx=$((idx + 1))
            AGENT_NAME="${ARGS[$idx]}"
            ;;
        --model)
            idx=$((idx + 1))
            MODEL_NAME="${ARGS[$idx]}"
            ;;
        --env-file)
            idx=$((idx + 1))
            ENV_FILE_NAME="${ARGS[$idx]}"
            ;;
        --task-id)
            idx=$((idx + 1))
            EVAL_SELECTION_ARGS+=(--task-id "${ARGS[$idx]}")
            ;;
        --limit)
            idx=$((idx + 1))
            EVAL_SELECTION_ARGS+=(--limit "${ARGS[$idx]}")
            ;;
        --dataset=* )
            DATASET_NAME="${arg#--dataset=}"
            ;;
        --setting=* )
            SETTING_NAME="${arg#--setting=}"
            ;;
        --agent=* )
            AGENT_NAME="${arg#--agent=}"
            ;;
        --model=* )
            MODEL_NAME="${arg#--model=}"
            ;;
        --env-file=* )
            ENV_FILE_NAME="${arg#--env-file=}"
            ;;
        --task-id=* )
            EVAL_SELECTION_ARGS+=(--task-id "${arg#--task-id=}")
            ;;
        --limit=* )
            EVAL_SELECTION_ARGS+=(--limit "${arg#--limit=}")
            ;;
    esac
    idx=$((idx + 1))
done

if [ "$SHOW_HELP" = "1" ]; then
    PYTHON_BIN="$PYTHON_BIN" bash inference/scripts/inference_univer_agent.sh "$@"
    exit 0
fi

if [ -z "$MODEL_NAME" ]; then
    case "$AGENT_NAME" in
        codex)
            MODEL_NAME="codex"
            ;;
        claude)
            MODEL_NAME="claude"
            ;;
        opencode)
            MODEL_NAME="opencode"
            ;;
        *)
            MODEL_NAME="agent"
            ;;
    esac
fi

RUN_ID_NAME=""
idx=0
while [ "$idx" -lt "$#" ]; do
    arg="${ARGS[$idx]}"
    case "$arg" in
        --run-id)
            idx=$((idx + 1))
            RUN_ID_NAME="${ARGS[$idx]}"
            ;;
        --run-id=* )
            RUN_ID_NAME="${arg#--run-id=}"
            ;;
    esac
    idx=$((idx + 1))
done

echo "[pipeline] inference start"
if [ -n "$ENV_FILE_NAME" ]; then
    ENV_FILE="$ENV_FILE_NAME" bash inference/scripts/inference_univer_agent.sh "$@"
else
    bash inference/scripts/inference_univer_agent.sh "$@"
fi
echo "[pipeline] inference done"

echo "[pipeline] evaluation start"
if [ -n "$RUN_ID_NAME" ]; then
    EVAL_RUN_ID_ARGS=(--run-id "$RUN_ID_NAME")
else
    EVAL_RUN_ID_ARGS=()
fi
(
    cd evaluation
    "$PYTHON_BIN" evaluation.py \
        --dataset "$DATASET_NAME" \
        --setting "$SETTING_NAME" \
        --model "$MODEL_NAME" \
        "${EVAL_RUN_ID_ARGS[@]}" \
        "${EVAL_SELECTION_ARGS[@]}"
)
echo "[pipeline] evaluation done"

if [ -n "$RUN_ID_NAME" ]; then
    EVALUATION_REPORT_PATH="outputs/eval_${SETTING_NAME}_${MODEL_NAME}_${RUN_ID_NAME}.json"
else
    EVALUATION_REPORT_PATH="outputs/eval_${SETTING_NAME}_${MODEL_NAME}.json"
fi
if [ -n "$RUN_ID_NAME" ]; then
    RUN_SUMMARY_PATH=".runs/univer-agent/${RUN_ID_NAME}/summary.json"
else
    RUN_SUMMARY_PATH=".runs/univer-agent/<run-id>/summary.json"
fi
echo "Run summary: ${RUN_SUMMARY_PATH}"
echo "Evaluation report: ${EVALUATION_REPORT_PATH}"

if [ -n "$RUN_ID_NAME" ]; then
    UNIFIED_REPORT_PATH="report/${RUN_ID_NAME}.json"
    "$PYTHON_BIN" scripts/build_univer_agent_report.py \
        --summary "$RUN_SUMMARY_PATH" \
        --evaluation "$EVALUATION_REPORT_PATH" \
        --output "$UNIFIED_REPORT_PATH"
fi
