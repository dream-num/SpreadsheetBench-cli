#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -z "${PYTHON_BIN:-}" ] && [ -x ".venv/bin/python" ]; then
    PYTHON_BIN="$PWD/.venv/bin/python"
else
    PYTHON_BIN="${PYTHON_BIN:-python3}"
fi
DATASET_NAME="${DATASET:-spreadsheetbench_verified_400}"
SETTING_NAME="${SETTING:-univer_agent}"
AGENT_NAME=""
MODEL_NAME=""
ENV_FILE_NAME="${ENV_FILE:-}"
SHOW_HELP=0
EVAL_SELECTION_ARGS=()
TASK_IDS=()
LIMIT_VALUE=""

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
        --env-file)
            idx=$((idx + 1))
            ENV_FILE_NAME="${ARGS[$idx]}"
            ;;
        --task-id)
            idx=$((idx + 1))
            EVAL_SELECTION_ARGS+=(--task-id "${ARGS[$idx]}")
            TASK_IDS+=("${ARGS[$idx]}")
            ;;
        --limit)
            idx=$((idx + 1))
            EVAL_SELECTION_ARGS+=(--limit "${ARGS[$idx]}")
            LIMIT_VALUE="${ARGS[$idx]}"
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
        --env-file=* )
            ENV_FILE_NAME="${arg#--env-file=}"
            ;;
        --task-id=* )
            EVAL_SELECTION_ARGS+=(--task-id "${arg#--task-id=}")
            TASK_IDS+=("${arg#--task-id=}")
            ;;
        --limit=* )
            EVAL_SELECTION_ARGS+=(--limit "${arg#--limit=}")
            LIMIT_VALUE="${arg#--limit=}"
            ;;
    esac
    idx=$((idx + 1))
done

if [ "$SHOW_HELP" = "1" ]; then
    PYTHON_BIN="$PYTHON_BIN" bash inference/scripts/inference_univer_agent.sh "$@"
    exit 0
fi

if [ -z "$ENV_FILE_NAME" ] && [ -f ".env.agent" ]; then
    ENV_FILE_NAME=".env.agent"
fi

env_file_value() {
    if [ -z "$ENV_FILE_NAME" ] || [ ! -f "$ENV_FILE_NAME" ]; then
        return
    fi
    awk -F= -v key="$1" '
        $0 !~ /^[[:space:]]*#/ && $1 == key {
            value = substr($0, index($0, "=") + 1)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
            gsub(/^["'\'']|["'\'']$/, "", value)
            print value
            exit
        }
    ' "$ENV_FILE_NAME"
}

if [ "$AGENT_NAME" = "codex" ]; then
    MODEL_NAME="$(env_file_value CODEX_MODEL)"
elif [ "$AGENT_NAME" = "claude" ]; then
    MODEL_NAME="$(env_file_value ANTHROPIC_MODEL)"
fi
if [ -z "$MODEL_NAME" ]; then
    MODEL_NAME="${AGENT_NAME:-agent}"
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

run_id_dataset_label() {
    case "$1" in
        spreadsheetbench_verified_400)
            echo "verified400"
            ;;
        sample_data_200)
            echo "sample200"
            ;;
        all_data_912_v0.1)
            echo "all912"
            ;;
        *)
            echo "$1" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-'
            ;;
    esac
}

run_id_safe_label() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-*//; s/-*$//'
}

run_id_scope_label() {
    if [ -n "$LIMIT_VALUE" ]; then
        echo "first${LIMIT_VALUE}"
        return
    fi
    if [ "${#TASK_IDS[@]}" -eq 1 ]; then
        echo "task${TASK_IDS[0]}" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-'
        return
    fi
    if [ "${#TASK_IDS[@]}" -gt 1 ]; then
        echo "tasks${#TASK_IDS[@]}"
        return
    fi
    echo "all"
}

if [ -z "$RUN_ID_NAME" ]; then
    RUN_ID_AGENT_LABEL="$(run_id_safe_label "${AGENT_NAME:-agent}")"
    RUN_ID_MODEL_LABEL="$(run_id_safe_label "${MODEL_NAME:-agent}")"
    RUN_ID_DATASET_LABEL="$(run_id_dataset_label "$DATASET_NAME")"
    RUN_ID_SCOPE_LABEL="$(run_id_scope_label)"
    RUN_ID_TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
    RUN_ID_NAME="${RUN_ID_AGENT_LABEL}-${RUN_ID_MODEL_LABEL}-${RUN_ID_DATASET_LABEL}-${RUN_ID_SCOPE_LABEL}-${RUN_ID_TIMESTAMP}"
    ARGS+=(--run-id "$RUN_ID_NAME")
fi

echo "[pipeline] inference start"
if [ -n "$ENV_FILE_NAME" ]; then
    ENV_FILE="$ENV_FILE_NAME" bash inference/scripts/inference_univer_agent.sh "${ARGS[@]}"
else
    bash inference/scripts/inference_univer_agent.sh "${ARGS[@]}"
fi
echo "[pipeline] inference done"

echo "[pipeline] evaluation start"
EVAL_RUN_ID_ARGS=(--run-id "$RUN_ID_NAME")
(
    cd evaluation
    EVALUATION_MODEL="$MODEL_NAME" "$PYTHON_BIN" evaluation.py \
        --dataset "$DATASET_NAME" \
        --setting "$SETTING_NAME" \
        "${EVAL_RUN_ID_ARGS[@]}" \
        "${EVAL_SELECTION_ARGS[@]}"
)
echo "[pipeline] evaluation done"

EVALUATION_REPORT_PATH="outputs/eval_${SETTING_NAME}_${MODEL_NAME}_${RUN_ID_NAME}.json"
RUN_SUMMARY_PATH=".runs/univer-agent/${RUN_ID_NAME}/summary.json"
echo "Run summary: ${RUN_SUMMARY_PATH}"
echo "Evaluation report: ${EVALUATION_REPORT_PATH}"

UNIFIED_REPORT_PATH="report/${RUN_ID_NAME}.json"
"$PYTHON_BIN" scripts/build_univer_agent_report.py \
    --summary "$RUN_SUMMARY_PATH" \
    --evaluation "$EVALUATION_REPORT_PATH" \
    --output "$UNIFIED_REPORT_PATH"
