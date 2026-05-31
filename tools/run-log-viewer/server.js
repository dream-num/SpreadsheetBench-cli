import http from "node:http";
import { createReadStream } from "node:fs";
import { access, readdir, readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_PORT = 5177;
const EVENT_FILES = [
  { fileName: "codex.events.jsonl", kind: "codex" },
  { fileName: "claude.events.jsonl", kind: "claude" },
];

function repoRootFromHere() {
  return path.resolve(__dirname, "..", "..");
}

function isSafeSegment(value) {
  return typeof value === "string" && value !== "" && !value.includes("/") && !value.includes("\\") && value !== "." && value !== "..";
}

async function pathExists(filePath) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function readJson(filePath) {
  return JSON.parse(await readFile(filePath, "utf8"));
}

async function readTextIfExists(filePath) {
  if (!(await pathExists(filePath))) {
    return null;
  }
  return readFile(filePath, "utf8");
}

async function listFiles(dirPath, predicate = () => true) {
  if (!(await pathExists(dirPath))) {
    return [];
  }
  const entries = await readdir(dirPath, { withFileTypes: true });
  return entries.filter((entry) => entry.isFile() && predicate(entry.name)).map((entry) => entry.name).sort();
}

async function listDirs(dirPath) {
  if (!(await pathExists(dirPath))) {
    return [];
  }
  const entries = await readdir(dirPath, { withFileTypes: true });
  return entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name).sort();
}

function countStatuses(tasks) {
  const counts = {};
  for (const task of tasks || []) {
    const status = String(task.status || "unknown");
    counts[status] = (counts[status] || 0) + 1;
  }
  return counts;
}

function summarizeTasks(tasks) {
  return (tasks || []).map((task) => ({
    id: String(task.id ?? ""),
    status: task.status ?? null,
    durationSeconds: task.duration_seconds ?? null,
    error: task.error ?? null,
  }));
}

function taskSortKey(taskId) {
  return String(taskId)
    .split("-")
    .map((part) => (part.match(/^\d+$/) ? part.padStart(12, "0") : part))
    .join("-");
}

function taskTimedOut(task) {
  return task?.status === "error" && String(task.error || "").toLowerCase().includes("timed out");
}

function statusFromTaskAndEval(task, evalItem) {
  if (taskTimedOut(task)) return "TIMEOUT";
  if (task?.status === "error") return "ERROR";
  if (!evalItem) return "NOT_RUN";
  const results = evalItem.test_case_results || [];
  if (!results.length) return "NOT_RUN";
  return results.every(Boolean) ? "PASS" : "FAIL";
}

function reportRunId(report, fallback) {
  return report.run?.metadata?.run_id || report.run_id || fallback.replace(/\.json$/, "");
}

function compactReportTaskRows(report, reportFile) {
  const runId = reportRunId(report, reportFile);
  const tasksById = new Map((report.run?.tasks || []).map((task) => [String(task.id), task]));
  const evalById = new Map((report.evaluate?.results || []).map((item) => [String(item.id), item]));
  const taskIds = [...new Set([...tasksById.keys(), ...evalById.keys()])].sort((a, b) =>
    taskSortKey(a).localeCompare(taskSortKey(b)),
  );
  return taskIds.map((taskId) => {
    const task = tasksById.get(taskId);
    const evalItem = evalById.get(taskId);
    const status = statusFromTaskAndEval(task, evalItem);
    return {
      taskId,
      status,
      instructionType: evalItem?.instruction_type || null,
      durationSeconds: task?.duration_seconds ?? null,
      error: task?.error || null,
      taskUrl: `/runs/${encodeURIComponent(runId)}/tasks/${encodeURIComponent(taskId)}?report=${encodeURIComponent(reportFile)}`,
    };
  });
}

export async function readReportDetails(root, fileName) {
  const report = await readReport(root, fileName);
  const runId = reportRunId(report, fileName);
  const tasks = compactReportTaskRows(report, fileName);
  return {
    fileName,
    summary: {
      runId,
      agent: report.run?.metadata?.agent || null,
      model: report.run?.metadata?.model || null,
      dataset: report.run?.metadata?.dataset || null,
      accuracy: report.accuracy ?? null,
      correct: report.correct_case_count ?? null,
      error: report.error_case_count ?? null,
      timeout: report.timeout_case_count ?? null,
      total: report.total_case_count ?? null,
      runUrl: `/runs/${encodeURIComponent(runId)}`,
    },
    tasks,
    wrongTasks: tasks.filter((task) => task.status !== "PASS"),
    raw: report,
  };
}

function extractPromptSections(prompt) {
  const sections = {};
  if (!prompt) return sections;
  const lines = prompt.split(/\r?\n/);
  let current = null;
  for (const line of lines) {
    const match = line.match(/^###\s+(.+?)\s*$/);
    if (match) {
      current = match[1].trim();
      sections[current] = "";
      continue;
    }
    if (current) sections[current] += `${line}\n`;
  }
  for (const key of Object.keys(sections)) {
    sections[key] = sections[key].trim();
  }
  return sections;
}

function analysisMarkers(details) {
  const markers = [];
  if (!details.eventLog) markers.push({ level: "warning", text: "未找到 JSONL 事件日志" });
  if (details.timing?.timeout) markers.push({ level: "error", text: "任务超时" });
  if (details.timing?.returncode && details.timing.returncode !== 0) {
    markers.push({ level: "error", text: `Docker 返回码 ${details.timing.returncode}` });
  }
  const failedCommands = details.eventLog?.failedCommandCount || 0;
  if (failedCommands) markers.push({ level: "error", text: `${failedCommands} 个命令失败` });
  const commandText = (details.eventLog?.timeline || [])
    .filter((item) => item.type === "command_execution")
    .map((item) => `${item.command}\n${item.output}`)
    .join("\n");
  for (const pattern of ["Unknown argument", "Sheet not found", "Range is out of bounds", "Missing workbook package file"]) {
    if (commandText.includes(pattern)) markers.push({ level: "warning", text: pattern });
  }
  return markers;
}

export async function scanWorkspace(root = repoRootFromHere()) {
  const reportDir = path.join(root, "report");
  const reportFiles = await listFiles(reportDir, (name) => name.endsWith(".json"));
  const reports = [];
  for (const fileName of reportFiles) {
    try {
      const report = await readJson(path.join(reportDir, fileName));
      const metadata = report.run?.metadata || {};
      reports.push({
        fileName,
        runId: metadata.run_id || report.run_id || fileName.replace(/\.json$/, ""),
        agent: metadata.agent || null,
        model: metadata.model || null,
        dataset: metadata.dataset || null,
        accuracy: report.accuracy ?? null,
        correct: report.correct_case_count ?? null,
        error: report.error_case_count ?? null,
        timeout: report.timeout_case_count ?? null,
        total: report.total_case_count ?? null,
        mtimeMs: (await stat(path.join(reportDir, fileName))).mtimeMs,
      });
    } catch (error) {
      reports.push({ fileName, runId: fileName.replace(/\.json$/, ""), error: error.message });
    }
  }
  reports.sort((a, b) => (b.mtimeMs || 0) - (a.mtimeMs || 0));

  const runsRoot = path.join(root, ".runs", "univer-agent");
  const runIds = await listDirs(runsRoot);
  const runs = [];
  for (const runId of runIds) {
    try {
      const run = await readRunSummary(root, runId);
      runs.push({
        runId,
        metadata: run.metadata,
        totalTasks: run.totalTasks,
        statusCounts: run.statusCounts,
        mtimeMs: run.mtimeMs,
      });
    } catch (error) {
      runs.push({ runId, metadata: {}, totalTasks: 0, statusCounts: {}, tasks: [], error: error.message });
    }
  }
  runs.sort((a, b) => (b.mtimeMs || 0) - (a.mtimeMs || 0));

  return { root, reports, runs };
}

export async function readRunSummary(root, runId) {
  if (!isSafeSegment(runId)) {
    throw Object.assign(new Error("无效运行 ID"), { statusCode: 400 });
  }
  const summaryPath = path.join(root, ".runs", "univer-agent", runId, "summary.json");
  if (!(await pathExists(summaryPath))) {
    throw Object.assign(new Error("未找到运行摘要"), { statusCode: 404 });
  }
  const summary = await readJson(summaryPath);
  const tasks = summarizeTasks(summary.tasks);
  return {
    runId,
    metadata: summary.metadata || {},
    totalTasks: tasks.length,
    statusCounts: countStatuses(summary.tasks),
    tasks,
    mtimeMs: (await stat(summaryPath)).mtimeMs,
  };
}

function parseJsonl(text) {
  const events = [];
  for (const [index, line] of text.split(/\r?\n/).entries()) {
    if (!line.trim()) {
      continue;
    }
    try {
      events.push(JSON.parse(line));
    } catch (error) {
      events.push({ type: "parse.error", line: index + 1, error: error.message, raw: line });
    }
  }
  return events;
}

function collapseItems(events) {
  const byId = new Map();
  const order = [];
  let anonymous = 0;
  for (const event of events) {
    if (!event.item || typeof event.item !== "object") {
      continue;
    }
    const id = String(event.item.id ?? `anonymous-${++anonymous}`);
    if (!byId.has(id)) {
      order.push(id);
      byId.set(id, {});
    }
    Object.assign(byId.get(id), event.item);
  }
  return order.map((id) => byId.get(id));
}

function parseUsage(events) {
  let input = 0;
  let output = 0;
  let seen = false;
  for (const event of events) {
    if (event.type !== "turn.completed" || !event.usage) {
      continue;
    }
    seen = true;
    input += Number(event.usage.input_tokens || 0);
    output += Number(event.usage.output_tokens || 0);
  }
  return seen ? { input, output, total: input + output } : null;
}

function countBy(values) {
  const counts = {};
  for (const value of values) {
    const key = String(value || "unknown");
    counts[key] = (counts[key] || 0) + 1;
  }
  return counts;
}

function summarizeEvents(events, kind) {
  const items = collapseItems(events);
  const timeline = [];
  for (const item of items) {
    if (item.type === "agent_message") {
      timeline.push({
        type: "agent_message",
        text: item.text || "",
      });
    } else if (item.type === "command_execution") {
      timeline.push({
        type: "command_execution",
        command: item.command || "",
        status: item.status ?? null,
        exitCode: item.exit_code ?? null,
        output: item.aggregated_output || "",
        failed: item.exit_code != null && item.exit_code !== 0,
      });
    } else if (item.type === "file_change") {
      timeline.push({
        type: "file_change",
        status: item.status ?? null,
        changes: (item.changes || []).map((change) => ({
          path: change.path || "",
          kind: change.kind || "",
        })),
      });
    }
  }
  const thread = [...events].reverse().find((event) => event.type === "thread.started" && event.thread_id);
  const timelineTypes = new Set(timeline.map((item) => item.type));
  const itemTypes = [...new Set(items.map((item) => item.type || "unknown"))];
  const unhandledItemTypes = itemTypes.filter((type) => !timelineTypes.has(type));
  const nonItemEventTypes = [...new Set(events.filter((event) => !event.item).map((event) => event.type || "unknown"))];
  return {
    kind,
    threadId: thread?.thread_id || null,
    eventCount: events.length,
    eventTypeCounts: countBy(events.map((event) => event.type)),
    itemTypeCounts: countBy(items.map((item) => item.type)),
    nonItemEventTypes,
    unhandledItemTypes,
    messageCount: timeline.filter((item) => item.type === "agent_message").length,
    commandCount: timeline.filter((item) => item.type === "command_execution").length,
    fileChangeCount: timeline.filter((item) => item.type === "file_change").length,
    failedCommandCount: timeline.filter((item) => item.type === "command_execution" && item.failed).length,
    usage: parseUsage(events),
    timeline,
  };
}

async function readEventLog(logsDir) {
  for (const candidate of EVENT_FILES) {
    const filePath = path.join(logsDir, candidate.fileName);
    if (await pathExists(filePath)) {
      const events = parseJsonl(await readFile(filePath, "utf8"));
      return { ...summarizeEvents(events, candidate.kind), fileName: candidate.fileName };
    }
  }
  return null;
}

async function readWorkFiles(taskDir) {
  const workDir = path.join(taskDir, "work");
  const fileNames = await listFiles(workDir);
  const files = [];
  for (const fileName of fileNames) {
    const filePath = path.join(workDir, fileName);
    const fileStat = await stat(filePath);
    files.push({
      name: fileName,
      path: `/task/work/${fileName}`,
      size: fileStat.size,
      content: await readFile(filePath, "utf8"),
    });
  }
  return files;
}

async function readOutputFiles(runId, taskId, taskDir) {
  const outputsDir = path.join(taskDir, "outputs");
  const caseNames = await listDirs(outputsDir);
  const files = [];
  for (const caseName of caseNames) {
    if (!isSafeSegment(caseName)) continue;
    const filePath = path.join(outputsDir, caseName, "output.xlsx");
    if (!(await pathExists(filePath))) continue;
    const fileStat = await stat(filePath);
    files.push({
      caseName,
      name: "output.xlsx",
      path: `/task/outputs/${caseName}/output.xlsx`,
      size: fileStat.size,
      downloadUrl: `/api/runs/${encodeURIComponent(runId)}/tasks/${encodeURIComponent(taskId)}/outputs/${encodeURIComponent(caseName)}/output.xlsx`,
    });
  }
  return files;
}

export async function resolveTaskOutputFile(root, runId, taskId, caseName, fileName) {
  if (!isSafeSegment(runId) || !isSafeSegment(taskId) || !isSafeSegment(caseName) || !isSafeSegment(fileName)) {
    throw Object.assign(new Error("无效运行 ID、任务 ID、case 或文件名"), { statusCode: 400 });
  }
  if (fileName !== "output.xlsx") {
    throw Object.assign(new Error("只允许下载 output.xlsx"), { statusCode: 400 });
  }
  const filePath = path.join(root, ".runs", "univer-agent", runId, taskId, "task", "outputs", caseName, fileName);
  if (!(await pathExists(filePath))) {
    throw Object.assign(new Error("未找到输出文件"), { statusCode: 404 });
  }
  return {
    filePath,
    downloadName: `${runId}-${taskId}-${caseName}-output.xlsx`,
  };
}

export async function readTaskDetails(root, runId, taskId) {
  if (!isSafeSegment(runId) || !isSafeSegment(taskId)) {
    throw Object.assign(new Error("无效运行 ID 或任务 ID"), { statusCode: 400 });
  }
  const taskDir = path.join(root, ".runs", "univer-agent", runId, taskId, "task");
  if (!(await pathExists(taskDir))) {
    throw Object.assign(new Error("未找到任务"), { statusCode: 404 });
  }
  const logsDir = path.join(taskDir, "logs");
  const timing = await readTextIfExists(path.join(logsDir, "docker.timing.json"));
  const details = {
    runId,
    taskId,
    prompt: await readTextIfExists(path.join(taskDir, "prompt.md")),
    timing: timing ? JSON.parse(timing) : null,
    finalMessage: await readTextIfExists(path.join(logsDir, "codex.final.md")),
    eventLog: await readEventLog(logsDir),
    workFiles: await readWorkFiles(taskDir),
    outputFiles: await readOutputFiles(runId, taskId, taskDir),
  };
  details.promptSections = extractPromptSections(details.prompt);
  details.analysisMarkers = analysisMarkers(details);
  return details;
}

async function readReport(root, fileName) {
  if (!isSafeSegment(fileName) || !fileName.endsWith(".json")) {
    throw Object.assign(new Error("无效报告文件"), { statusCode: 400 });
  }
  const reportPath = path.join(root, "report", fileName);
  if (!(await pathExists(reportPath))) {
    throw Object.assign(new Error("未找到报告"), { statusCode: 404 });
  }
  return readJson(reportPath);
}

function sendJson(response, statusCode, value) {
  const body = JSON.stringify(value, null, 2);
  response.writeHead(statusCode, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
  });
  response.end(body);
}

function contentType(filePath) {
  if (filePath.endsWith(".html")) return "text/html; charset=utf-8";
  if (filePath.endsWith(".js")) return "text/javascript; charset=utf-8";
  if (filePath.endsWith(".css")) return "text/css; charset=utf-8";
  if (filePath.endsWith(".xlsx")) return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  return "application/octet-stream";
}

function sendHtml(response, html) {
  response.writeHead(200, { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" });
  response.end(html);
}

export function appShellHtml() {
  return `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>SpreadsheetBench 运行日志查看器</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/antd@5/dist/reset.css" />
    <link rel="stylesheet" href="/styles.css" />
  </head>
  <body>
    <div id="root"></div>
    <script src="https://cdn.jsdelivr.net/npm/react@18/umd/react.production.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/dayjs@1/dayjs.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/antd@5/dist/antd.min.js"></script>
    <script src="/app.js"></script>
  </body>
</html>`;
}

async function serveStatic(response, urlPath) {
  const publicDir = path.join(__dirname, "public");
  const requested = urlPath === "/" ? "index.html" : decodeURIComponent(urlPath.slice(1));
  const filePath = path.normalize(path.join(publicDir, requested));
  if (!filePath.startsWith(publicDir)) {
    sendJson(response, 403, { error: "Forbidden" });
    return;
  }
  if (!(await pathExists(filePath))) {
    sendJson(response, 404, { error: "Not found" });
    return;
  }
  response.writeHead(200, { "content-type": contentType(filePath), "cache-control": "no-store" });
  createReadStream(filePath).pipe(response);
}

async function serveTaskOutput(response, root, runId, taskId, caseName, fileName) {
  const output = await resolveTaskOutputFile(root, runId, taskId, caseName, fileName);
  response.writeHead(200, {
    "content-type": contentType(output.filePath),
    "content-disposition": `attachment; filename="${output.downloadName}"`,
    "cache-control": "no-store",
  });
  createReadStream(output.filePath).pipe(response);
}

export function createServer({ root = repoRootFromHere() } = {}) {
  return http.createServer(async (request, response) => {
    try {
      const url = new URL(request.url, `http://${request.headers.host || "localhost"}`);
      if (request.method !== "GET") {
        sendJson(response, 405, { error: "Method not allowed" });
        return;
      }
      if (url.pathname === "/api/home") {
        sendJson(response, 200, await scanWorkspace(root));
        return;
      }
      const pluralRunMatch = url.pathname.match(/^\/api\/runs\/([^/]+)$/);
      if (pluralRunMatch) {
        sendJson(response, 200, await readRunSummary(root, decodeURIComponent(pluralRunMatch[1])));
        return;
      }
      const pluralReportMatch = url.pathname.match(/^\/api\/reports\/([^/]+)$/);
      if (pluralReportMatch) {
        sendJson(response, 200, await readReportDetails(root, decodeURIComponent(pluralReportMatch[1])));
        return;
      }
      const taskOutputMatch = url.pathname.match(/^\/api\/runs\/([^/]+)\/tasks\/([^/]+)\/outputs\/([^/]+)\/([^/]+)$/);
      if (taskOutputMatch) {
        await serveTaskOutput(
          response,
          root,
          decodeURIComponent(taskOutputMatch[1]),
          decodeURIComponent(taskOutputMatch[2]),
          decodeURIComponent(taskOutputMatch[3]),
          decodeURIComponent(taskOutputMatch[4]),
        );
        return;
      }
      const pluralTaskMatch = url.pathname.match(/^\/api\/runs\/([^/]+)\/tasks\/([^/]+)$/);
      if (pluralTaskMatch) {
        sendJson(
          response,
          200,
          await readTaskDetails(root, decodeURIComponent(pluralTaskMatch[1]), decodeURIComponent(pluralTaskMatch[2])),
        );
        return;
      }
      if (url.pathname === "/" || url.pathname.startsWith("/runs/") || url.pathname.startsWith("/reports/")) {
        sendHtml(response, appShellHtml());
        return;
      }
      await serveStatic(response, url.pathname);
    } catch (error) {
      sendJson(response, error.statusCode || 500, { error: error.message || "Internal error" });
    }
  });
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const port = Number(process.env.PORT || DEFAULT_PORT);
  const rootArgIndex = process.argv.indexOf("--root");
  const root = rootArgIndex >= 0 ? path.resolve(process.argv[rootArgIndex + 1]) : repoRootFromHere();
  const server = createServer({ root });
  server.listen(port, "127.0.0.1", () => {
    console.log(`Run log viewer: http://127.0.0.1:${port}`);
    console.log(`Workspace root: ${root}`);
  });
}
