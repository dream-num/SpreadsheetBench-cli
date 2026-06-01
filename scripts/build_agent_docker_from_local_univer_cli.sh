#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

DEFAULT_LOCAL_UNIVER_CLI_REPO="$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/univer-cli"
if [ ! -d "$DEFAULT_LOCAL_UNIVER_CLI_REPO" ]; then
    DEFAULT_LOCAL_UNIVER_CLI_REPO="/Users/morris/Developer/univer/univer-cli"
fi

LOCAL_UNIVER_CLI_REPO="$DEFAULT_LOCAL_UNIVER_CLI_REPO"
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
  --repo        sibling ../univer-cli when present, otherwise /Users/morris/Developer/univer/univer-cli
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
    REQUIRED_LOCAL_SKILLS=(
        "using-univer-cli"
        "univer-cli"
        "writing-univer-plans"
        "executing-univer-plans"
        "test-driven-univer-development"
    )
    for skill_name in "${REQUIRED_LOCAL_SKILLS[@]}"; do
        if [ ! -f "$LOCAL_SKILLS_REPO/skills/$skill_name/SKILL.md" ]; then
            echo "local skills repo is missing expected Univer skill '$skill_name': $LOCAL_SKILLS_REPO" >&2
            exit 2
        fi
    done
    REMOVED_BENCHMARK_SKILL="benchmarking""-univer-cli"
    if rg -q "$REMOVED_BENCHMARK_SKILL" \
        "$LOCAL_SKILLS_REPO/skills/using-univer-cli" \
        "$LOCAL_SKILLS_REPO/skills/executing-univer-plans" \
        "$LOCAL_SKILLS_REPO/skills/test-driven-univer-development"
    then
        echo "local skills repo still routes through removed benchmark skill: $LOCAL_SKILLS_REPO" >&2
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
    mkdir -p "$BUILD_ROOT/local-skills/skills"
    for skill_name in "${REQUIRED_LOCAL_SKILLS[@]}"; do
        cp -R "$LOCAL_SKILLS_REPO/skills/$skill_name" "$BUILD_ROOT/local-skills/skills/"
    done
fi

cat > "$BUILD_ROOT/Dockerfile" <<'EOF'
FROM node:22-alpine

RUN apk add --no-cache \
        bash \
        ca-certificates \
        git \
        ripgrep

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
    && univer new "$tmp/sac-cache.univer" --with-project >/dev/null \
    && (test -d /home/node/.univer/sac/types || (find /home/node/.univer -maxdepth 5 -print >&2; false)) \
    && TOOLCHAIN_ROOT="$(node --input-type=module -e 'import { createHash } from "node:crypto"; import { readdirSync } from "node:fs"; import { join } from "node:path"; const packageRoot="/usr/local/lib/node_modules/univer-cli"; const buildInfoFile=readdirSync(join(packageRoot,"chunks")).find((name)=>name.startsWith("build-info-")&&name.endsWith(".js")); const buildInfoModule=await import(`file://${join(packageRoot,"chunks",buildInfoFile)}`); const buildInfo=buildInfoModule.CLI_BUILD_INFO ?? Object.values(buildInfoModule).find((value)=>value && typeof value==="object" && typeof value.commitHash==="string" && typeof value.version==="string"); if (!buildInfo) throw new Error("Cannot locate CLI build info export"); const deps={"@typescript/native-preview":"7.0.0-dev.20260517.1",rolldown:"1.0.1"}; const hash=createHash("sha256").update(JSON.stringify(deps)).digest("hex").slice(0,12); const commit=buildInfo.commitHash==="unknown"?"unknown":buildInfo.commitHash; const key=`cli-${buildInfo.version}-${commit}-${hash}`.replace(/[^a-zA-Z0-9._-]/g,"-"); console.log(`/home/node/.univer/sac/toolchains/${key}`);')" \
    && mkdir -p "$TOOLCHAIN_ROOT" \
    && printf '%s\n' \
        '{' \
        '  "private": true,' \
        '  "name": "@univer/sac-shared-toolchain",' \
        '  "version": "0.0.0",' \
        '  "type": "module",' \
        '  "dependencies": {' \
        '    "@typescript/native-preview": "7.0.0-dev.20260517.1",' \
        '    "rolldown": "1.0.1"' \
        '  }' \
        '}' \
        > "$TOOLCHAIN_ROOT/package.json" \
    && (cd "$TOOLCHAIN_ROOT" && npm install --no-audit --no-fund >/tmp/sac-toolchain-install.log 2>&1 || (cat /tmp/sac-toolchain-install.log >&2; false)) \
    && (test -d /home/node/.univer/sac/toolchains || (find /home/node/.univer -maxdepth 5 -print >&2; false)) \
    && (find /home/node/.univer/sac/toolchains -path '*/node_modules/rolldown' -print -quit | grep -q . || (find /home/node/.univer/sac/toolchains -maxdepth 6 -print >&2; false)) \
    && (find /home/node/.univer/sac/toolchains -path '*/node_modules/.bin/tsgo' -print -quit | grep -q . || (find /home/node/.univer/sac/toolchains -maxdepth 6 -print >&2; false)) \
    && (univer view stop >/dev/null 2>&1 || true) \
    && (univer daemon stop >/dev/null 2>&1 || true) \
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
