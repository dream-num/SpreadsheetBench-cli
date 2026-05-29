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
