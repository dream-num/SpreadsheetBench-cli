FROM node:22-alpine

RUN apk add --no-cache \
        bash \
        ca-certificates \
        git

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
    && univer new "$tmp/warmup.univer" >/dev/null \
    && univer inspect workbook "$tmp/warmup.univer" >/dev/null \
    && univer config set experimental.sac true >/dev/null \
    && univer new "$tmp/sac-cache.univer" >/dev/null \
    && univer sac init "$tmp/sac" --from "$tmp/sac-cache.univer" >/dev/null \
    && (cd "$tmp/sac" && CI=true pnpm install --prefer-offline >/dev/null) \
    && cp -a "$tmp/sac/node_modules" /home/node/.cache/spreadsheetbench-sac-node_modules \
    && test -d /home/node/.univer/sac/types \
    && univer sac init "$tmp/toolchain-sac" >/dev/null \
    && mkdir -p "$tmp/toolchain-sac/migrations/20200101000000-cache-warmup" \
    && printf '%s\n' \
        'import { defineFacadeMigrationPack } from "univer:sac/facade-migration-pack";' \
        'const pack = defineFacadeMigrationPack({' \
        '  id: "20200101000000-cache-warmup",' \
        '  title: "Cache Warmup",' \
        '  files: []' \
        '});' \
        'export default { pack, sheetMigrations: [] };' \
        > "$tmp/toolchain-sac/migrations/20200101000000-cache-warmup/pack.ts" \
    && (univer sac apply "$tmp/toolchain-sac" --no-commit >/dev/null || true) \
    && test -d /home/node/.univer/sac/toolchains \
    && find /home/node/.univer/sac/toolchains -path '*/node_modules/rolldown' -print -quit | grep -q . \
    && find /home/node/.univer/sac/toolchains -path '*/node_modules/.bin/tsgo' -print -quit | grep -q . \
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
