FROM node:22-alpine

RUN apk add --no-cache \
        bash \
        ca-certificates \
        git \
        ripgrep

RUN npm install -g \
        univer-cli@latest \
        pnpm \
        @openai/codex \
        @anthropic-ai/claude-code

RUN mkdir -p /home/node/.codex/skills /home/node/.claude/skills \
    && chown -R node:node /home/node

USER node

RUN mkdir -p /home/node/.codex/skills /home/node/.claude/skills \
    && npx -y skills add dream-num/skills --global --yes --agent codex claude-code

RUN tmp="$(mktemp -d)" \
    && mkdir -p /home/node/.cache \
    && printf '%s\n' 'A,B' '1,2' > "$tmp/sac-cache.csv" \
    && univer import --file "$tmp/sac-cache.csv" "$tmp/sac-cache.univer" --json >/dev/null \
    && printf '%s\n' '{}' > "$tmp/inspect.params.json" \
    && univer inspect "$tmp/sac-cache.univer" --script "$tmp/.sac-cache.univer.sac/inspect-tools/units.js" --params "$tmp/inspect.params.json" >/dev/null \
    && univer sac migration create Warmup "$tmp/sac-cache.univer" >/dev/null \
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
