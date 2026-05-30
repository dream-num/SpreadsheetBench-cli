#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

LOCAL_UNIVER_CLI_REPO="${LOCAL_UNIVER_CLI_REPO:-/Users/morris/Developer/univer/univer-cli}"
LOCAL_SKILLS_REPO="${LOCAL_SKILLS_REPO:-/Users/morris/Developer/univer/skills}"
IMAGE_TAG="${IMAGE_TAG:-spreadsheetbench-univer-cli-agent-local}"
AGENT_TIMEOUT="${AGENT_TIMEOUT:-900}"
WORKERS="${WORKERS:-5}"
DATASET_NAME="${DATASET:-spreadsheetbench_verified_400}"
ENV_FILE_NAME="${ENV_FILE:-.env.codex}"
SKIP_LOCAL_BUILD="${SKIP_LOCAL_BUILD:-0}"

ARGS=("$@")
ARG_COUNT=$#

has_arg() {
    local name="$1"
    local arg
    if [ "$ARG_COUNT" -eq 0 ]; then
        return 1
    fi
    for arg in "${ARGS[@]}"; do
        if [ "$arg" = "$name" ] || [[ "$arg" == "$name="* ]]; then
            return 0
        fi
    done
    return 1
}

arg_value() {
    local name="$1"
    local value=""
    local idx=0
    while [ "$idx" -lt "$ARG_COUNT" ]; do
        case "${ARGS[$idx]}" in
            "$name")
                idx=$((idx + 1))
                value="${ARGS[$idx]:-}"
                ;;
            "$name"=*)
                value="${ARGS[$idx]#*=}"
                ;;
        esac
        idx=$((idx + 1))
    done
    printf '%s\n' "$value"
}

if has_arg "--dataset"; then
    DATASET_NAME="$(arg_value "--dataset")"
fi
if has_arg "--env-file"; then
    ENV_FILE_NAME="$(arg_value "--env-file")"
fi

resolve_env_path() {
    local env_path="$1"
    case "$env_path" in
        "~/"*)
            env_path="${HOME}/${env_path#"~/"}"
            ;;
        /*)
            ;;
        *)
            env_path="$(dirname "$ENV_FILE_NAME")/$env_path"
            ;;
    esac
    cd "$(dirname "$env_path")" && printf '%s/%s\n' "$PWD" "$(basename "$env_path")"
}

env_file_value() {
    local key="$1"
    awk -F= -v key="$key" '
        $0 !~ /^[[:space:]]*#/ && $1 == key {
            value = substr($0, index($0, "=") + 1)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
            gsub(/^["'\'']|["'\'']$/, "", value)
            print value
            exit
        }
    ' "$ENV_FILE_NAME"
}

codex_config_value() {
    local key="$1"
    local config_path="$2"
    awk -v key="$key" '
        /^[[:space:]]*\[/ { in_table = 1; next }
        in_table { next }
        /^[[:space:]]*#/ || /^[[:space:]]*$/ { next }
        {
            split($0, pair, "=")
            candidate = pair[1]
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", candidate)
            if (candidate == key) {
                value = substr($0, index($0, "=") + 1)
                sub(/#.*/, "", value)
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
                gsub(/^["'\'']|["'\'']$/, "", value)
                print value
                exit
            }
        }
    ' "$config_path"
}

require_codex_gpt55_medium() {
    if [ ! -f "$ENV_FILE_NAME" ]; then
        echo "env file not found: $ENV_FILE_NAME" >&2
        exit 2
    fi

    local config_raw
    config_raw="$(env_file_value CODEX_CONFIG_TOML)"
    if [ -z "$config_raw" ]; then
        echo "CODEX_CONFIG_TOML is required in $ENV_FILE_NAME" >&2
        exit 2
    fi

    local config_path
    config_path="$(resolve_env_path "$config_raw")"
    if [ ! -f "$config_path" ]; then
        echo "CODEX_CONFIG_TOML file not found: $config_path" >&2
        exit 2
    fi

    local model
    local effort
    model="$(codex_config_value model "$config_path")"
    effort="$(codex_config_value model_reasoning_effort "$config_path")"
    if [ "$model" != "gpt-5.5" ] || [ "$effort" != "medium" ]; then
        echo "expected Codex config model=gpt-5.5 and model_reasoning_effort=medium, got model=${model:-<missing>} effort=${effort:-<missing>}" >&2
        exit 2
    fi
}

dataset_label() {
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

scope_label() {
    local task_count=0
    local only_task=""
    local limit_value=""
    local idx=0
    while [ "$idx" -lt "$ARG_COUNT" ]; do
        case "${ARGS[$idx]}" in
            --task-id)
                idx=$((idx + 1))
                only_task="${ARGS[$idx]:-}"
                task_count=$((task_count + 1))
                ;;
            --task-id=*)
                only_task="${ARGS[$idx]#--task-id=}"
                task_count=$((task_count + 1))
                ;;
            --limit)
                idx=$((idx + 1))
                limit_value="${ARGS[$idx]:-}"
                ;;
            --limit=*)
                limit_value="${ARGS[$idx]#--limit=}"
                ;;
        esac
        idx=$((idx + 1))
    done

    if [ -n "$limit_value" ]; then
        echo "first${limit_value}"
    elif [ "$task_count" -eq 1 ]; then
        echo "task${only_task}" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-'
    elif [ "$task_count" -gt 1 ]; then
        echo "tasks${task_count}"
    else
        echo "all"
    fi
}

require_codex_gpt55_medium

build_args=(
    --repo "$LOCAL_UNIVER_CLI_REPO"
    --skills-repo "$LOCAL_SKILLS_REPO"
    --tag "$IMAGE_TAG"
)
if [ "$SKIP_LOCAL_BUILD" = "1" ]; then
    build_args+=(--skip-local-build)
fi

bash scripts/build_agent_docker_from_local_univer_cli.sh "${build_args[@]}"

run_args=(
    --agent codex
    --dataset "$DATASET_NAME"
    --env-file "$ENV_FILE_NAME"
    --docker-image "$IMAGE_TAG"
    --agent-timeout "$AGENT_TIMEOUT"
    --workers "$WORKERS"
)

if ! has_arg "--run-id"; then
    run_args+=(
        --run-id "sac-local-cli-skill-gpt-5-5-medium-$(dataset_label "$DATASET_NAME")-$(scope_label)-$(date +%Y%m%d-%H%M%S)"
    )
fi

if [ "$ARG_COUNT" -gt 0 ]; then
    bash scripts/run_univer_agent_eval.sh "${run_args[@]}" "${ARGS[@]}"
else
    bash scripts/run_univer_agent_eval.sh "${run_args[@]}"
fi
