#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

while [ "$#" -gt 0 ]; do
    case "$1" in
        -h|--help)
            cat <<'EOF'
Usage: bash scripts/build_agent_docker.sh

Builds fixed image: spreadsheetbench-univer-cli-agent
EOF
            exit 0
            ;;
        *)
            echo "unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

docker build \
    -t spreadsheetbench-univer-cli-agent \
    docker/spreadsheetbench-univer-cli-agent

echo "spreadsheetbench-univer-cli-agent"
