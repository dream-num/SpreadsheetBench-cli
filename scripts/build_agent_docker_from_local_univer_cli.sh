#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

LOCAL_UNIVER_CLI_REPO="/Users/otime/project/univer-cli"
LOCAL_SKILLS_REPO=""
LOCAL_SKILLS_REPO_EXPLICIT=0
IMAGE_TAG="spreadsheetbench-univer-cli-agent"
SKIP_LOCAL_BUILD=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --repo)
            LOCAL_UNIVER_CLI_REPO="${2:-}"
            shift 2
            ;;
        --repo=*)
            LOCAL_UNIVER_CLI_REPO="${1#--repo=}"
            shift
            ;;
        --skills-repo)
            LOCAL_SKILLS_REPO="${2:-}"
            LOCAL_SKILLS_REPO_EXPLICIT=1
            shift 2
            ;;
        --skills-repo=*)
            LOCAL_SKILLS_REPO="${1#--skills-repo=}"
            LOCAL_SKILLS_REPO_EXPLICIT=1
            shift
            ;;
        --tag)
            IMAGE_TAG="${2:-}"
            shift 2
            ;;
        --tag=*)
            IMAGE_TAG="${1#--tag=}"
            shift
            ;;
        --skip-local-build)
            SKIP_LOCAL_BUILD=1
            shift
            ;;
        -h|--help)
            cat <<'EOF'
Usage: bash scripts/build_agent_docker_from_local_univer_cli.sh [--repo /path/to/univer-cli] [--skills-repo /path/to/skills] [--tag image-tag] [--skip-local-build]

Builds the SpreadsheetBench solver image with a locally built univer-cli package
and, when available, a local sibling skills repository.

Defaults:
  --repo        /Users/otime/project/univer-cli
  --skills-repo ../skills relative to --repo when that directory exists
  --tag         spreadsheetbench-univer-cli-agent

The script runs `pnpm build` in the local univer-cli repo, packs apps/cli/dist,
installs that tarball into the Docker image instead of univer-cli@latest, and
bakes local skills into the agent skill directories when --skills-repo is set
or a sibling ../skills repository exists.
EOF
            exit 0
            ;;
        *)
            echo "unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

if [ -z "$LOCAL_UNIVER_CLI_REPO" ] || [ ! -d "$LOCAL_UNIVER_CLI_REPO" ]; then
    echo "local univer-cli repo not found: $LOCAL_UNIVER_CLI_REPO" >&2
    exit 2
fi

if [ ! -f "$LOCAL_UNIVER_CLI_REPO/package.json" ] || [ ! -f "$LOCAL_UNIVER_CLI_REPO/apps/cli/package.json" ]; then
    echo "not a univer-cli monorepo: $LOCAL_UNIVER_CLI_REPO" >&2
    exit 2
fi

if [ -z "$LOCAL_SKILLS_REPO" ]; then
    LOCAL_SKILLS_REPO="$(cd "$LOCAL_UNIVER_CLI_REPO/.." && pwd)/skills"
fi

USE_LOCAL_SKILLS=0
if [ -d "$LOCAL_SKILLS_REPO" ]; then
    if [ ! -f "$LOCAL_SKILLS_REPO/skills/univer-cli/SKILL.md" ] || [ ! -f "$LOCAL_SKILLS_REPO/skills/univer-spreadsheet-tdd/SKILL.md" ]; then
        echo "local skills repo is missing expected Univer skills: $LOCAL_SKILLS_REPO" >&2
        exit 2
    fi
    USE_LOCAL_SKILLS=1
elif [ "$LOCAL_SKILLS_REPO_EXPLICIT" -eq 1 ]; then
    echo "local skills repo not found: $LOCAL_SKILLS_REPO" >&2
    exit 2
else
    LOCAL_SKILLS_REPO=""
fi

if [ "$SKIP_LOCAL_BUILD" -eq 0 ]; then
    (cd "$LOCAL_UNIVER_CLI_REPO" && pnpm build)
fi

DIST_DIR="$LOCAL_UNIVER_CLI_REPO/apps/cli/dist"
if [ ! -f "$DIST_DIR/package.json" ] || [ ! -f "$DIST_DIR/bin/univer.js" ]; then
    echo "local univer-cli dist is missing; expected $DIST_DIR/package.json and $DIST_DIR/bin/univer.js" >&2
    exit 2
fi

BUILD_ROOT="${TMPDIR:-/tmp}/spreadsheetbench-local-univer-cli-docker"
NPM_CACHE="${TMPDIR:-/tmp}/spreadsheetbench-local-univer-cli-npm-cache"
rm -rf "$BUILD_ROOT"
mkdir -p "$BUILD_ROOT" "$NPM_CACHE"

npm --cache "$NPM_CACHE" pack "$DIST_DIR" --pack-destination "$BUILD_ROOT" >/dev/null
TARBALL="$(find "$BUILD_ROOT" -maxdepth 1 -name 'univer-cli-*.tgz' -print -quit)"
if [ -z "$TARBALL" ]; then
    echo "failed to pack local univer-cli dist" >&2
    exit 1
fi

cp docker/spreadsheetbench-univer-cli-agent/entrypoint.sh "$BUILD_ROOT/"
cp docker/spreadsheetbench-univer-cli-agent/run-task.sh "$BUILD_ROOT/"

if [ "$USE_LOCAL_SKILLS" -eq 1 ]; then
    mkdir -p "$BUILD_ROOT/local-skills"
    cp -R "$LOCAL_SKILLS_REPO/skills" "$BUILD_ROOT/local-skills/"
fi

cat > "$BUILD_ROOT/Dockerfile" <<'EOF'
FROM node:22-alpine

RUN apk add --no-cache \
        bash \
        ca-certificates \
        git

COPY univer-cli-*.tgz /tmp/univer-cli.tgz

RUN npm install -g \
        /tmp/univer-cli.tgz \
        pnpm \
        @openai/codex \
        @anthropic-ai/claude-code \
    && rm -f /tmp/univer-cli.tgz

RUN mkdir -p /home/node/.codex/skills /home/node/.claude/skills \
    && chown -R node:node /home/node

USER node
EOF

if [ "$USE_LOCAL_SKILLS" -eq 1 ]; then
    cat >> "$BUILD_ROOT/Dockerfile" <<'EOF'
COPY --chown=node:node local-skills/skills /tmp/local-skills/skills

RUN mkdir -p /home/node/.codex/skills /home/node/.claude/skills \
    && for skill_dir in /tmp/local-skills/skills/*; do \
        cp -R "$skill_dir" /home/node/.codex/skills/; \
        cp -R "$skill_dir" /home/node/.claude/skills/; \
    done
EOF
else
    cat >> "$BUILD_ROOT/Dockerfile" <<'EOF'
RUN mkdir -p /home/node/.codex/skills /home/node/.claude/skills \
    && npx -y skills add dream-num/skills --global --yes --agent codex claude-code
EOF
fi

cat >> "$BUILD_ROOT/Dockerfile" <<'EOF'
RUN tmp="$(mktemp -d)" \
    && mkdir -p /home/node/.cache \
    && univer new "$tmp/warmup.univer" >/dev/null \
    && univer inspect workbook "$tmp/warmup.univer" >/dev/null \
    && univer config set experimental.sac true >/dev/null \
    && univer new "$tmp/sac-cache.univer" >/dev/null \
    && univer sac init "$tmp/sac-cache" --from "$tmp/sac-cache.univer" >/dev/null \
    && cd "$tmp/sac-cache" \
    && pnpm install --prefer-offline >/dev/null \
    && cp -a "$tmp/sac-cache/node_modules" /home/node/.cache/spreadsheetbench-sac-node_modules \
    && univer view stop >/dev/null \
    && univer daemon stop >/dev/null \
    && rm -rf "$tmp"

COPY entrypoint.sh /usr/local/bin/spreadsheetbench-agent-entrypoint
COPY run-task.sh /usr/local/bin/spreadsheetbench-agent-task

USER root

RUN chmod +x \
        /usr/local/bin/spreadsheetbench-agent-entrypoint \
        /usr/local/bin/spreadsheetbench-agent-task

USER node

WORKDIR /task
ENTRYPOINT ["spreadsheetbench-agent-entrypoint"]
EOF

docker build \
    -t "$IMAGE_TAG" \
    "$BUILD_ROOT"

echo "$IMAGE_TAG"
echo "local univer-cli repo: $LOCAL_UNIVER_CLI_REPO"
if [ "$USE_LOCAL_SKILLS" -eq 1 ]; then
    echo "local skills repo: $LOCAL_SKILLS_REPO"
else
    echo "skills repo: dream-num/skills"
fi
echo "packed tarball: $TARBALL"
