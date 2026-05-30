# Run Log Viewer

Small local viewer for SpreadsheetBench reports and agent run logs.

The Node server only serves JSON APIs and the frontend shell. The browser app uses React + Ant Design from CDN assets and renders report, run, and task pages client-side.

## Start

```bash
npm start
```

Open:

```text
http://127.0.0.1:5177
```

Use `PORT` to choose another port:

```bash
PORT=5180 npm start
```

Use `--root` to inspect another checkout:

```bash
npm start -- --root /path/to/SpreadsheetBench-cli
```

## What It Reads

- `report/*.json`
- `.runs/univer-agent/*/summary.json`
- `.runs/univer-agent/<run-id>/<task-id>/task/prompt.md`
- `.runs/univer-agent/<run-id>/<task-id>/task/logs/codex.events.jsonl`
- `.runs/univer-agent/<run-id>/<task-id>/task/logs/claude.events.jsonl`
- `.runs/univer-agent/<run-id>/<task-id>/task/logs/codex.final.md`
- `.runs/univer-agent/<run-id>/<task-id>/task/logs/docker.timing.json`

## Routes

- `/` - report-first home page, with runs below reports.
- `/reports/<report-file>.json` - report summary and wrong-task list.
- `/runs/<run-id>` - run metadata and task table.
- `/runs/<run-id>/tasks/<task-id>` - task context, prompt summary, agent timeline, commands, final message, and timing.

## APIs

- `/api/home`
- `/api/reports/<report-file>.json`
- `/api/runs/<run-id>`
- `/api/runs/<run-id>/tasks/<task-id>`

## Test

```bash
npm test
```
