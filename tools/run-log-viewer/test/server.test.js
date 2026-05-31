import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { appShellHtml, readReportDetails, readRunSummary, readTaskDetails, resolveTaskOutputFile, scanWorkspace } from "../server.js";

async function writeJson(filePath, value) {
  await mkdir(path.dirname(filePath), { recursive: true });
  await writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

test("scanWorkspace lists reports and run summaries", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "viewer-scan-"));
  await writeJson(path.join(root, "report", "run-1.json"), {
    accuracy: 0.75,
    run: { metadata: { run_id: "run-1", agent: "codex", model: "gpt-5.5" } },
  });
  await writeJson(path.join(root, ".runs", "univer-agent", "run-1", "summary.json"), {
    metadata: { run_id: "run-1", dataset: "spreadsheetbench_verified_400" },
    tasks: [
      { id: "task-pass", status: "ok", duration_seconds: 2.5 },
      { id: "task-fail", status: "error", error: "failed", duration_seconds: 9 },
    ],
  });

  const snapshot = await scanWorkspace(root);

  assert.equal(snapshot.reports.length, 1);
  assert.equal(snapshot.reports[0].runId, "run-1");
  assert.equal(snapshot.reports[0].accuracy, 0.75);
  assert.equal(snapshot.runs.length, 1);
  assert.equal(snapshot.runs[0].runId, "run-1");
  assert.deepEqual(snapshot.runs[0].statusCounts, { ok: 1, error: 1 });
  assert.equal(snapshot.runs[0].tasks, undefined);

  const run = await readRunSummary(root, "run-1");
  assert.equal(run.tasks.length, 2);
  assert.equal(run.tasks[0].id, "task-pass");
});

test("readTaskDetails prefers JSONL events and collapses command lifecycle", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "viewer-task-"));
  const taskDir = path.join(root, ".runs", "univer-agent", "run-1", "task-1", "task");
  const logsDir = path.join(taskDir, "logs");
  const workDir = path.join(taskDir, "work");
  await mkdir(logsDir, { recursive: true });
  await mkdir(workDir, { recursive: true });
  await writeFile(
    path.join(taskDir, "prompt.md"),
    [
      "Request id: task-1",
      "",
      "### instruction",
      "Fill B2 with the matching total.",
      "",
      "### answer_position",
      "B2",
      "",
      "### output_path",
      "- /task/outputs/case_1/output.xlsx",
      "",
    ].join("\n"),
    "utf8",
  );
  await writeJson(path.join(logsDir, "docker.timing.json"), {
    status: "finished",
    duration_seconds: 3.25,
    returncode: 0,
  });
  await writeFile(path.join(workDir, "inspect.js"), "() => ({ success: true })\n", "utf8");
  await mkdir(path.join(taskDir, "outputs", "case_1"), { recursive: true });
  await writeFile(path.join(taskDir, "outputs", "case_1", "output.xlsx"), "xlsx bytes");
  await writeFile(path.join(logsDir, "codex.final.md"), "Final answer\n", "utf8");
  await writeFile(
    path.join(logsDir, "codex.events.jsonl"),
    [
      JSON.stringify({ type: "thread.started", thread_id: "thread-1" }),
      JSON.stringify({
        type: "item.completed",
        item: { id: "msg-1", type: "agent_message", text: "Inspection evidence" },
      }),
      JSON.stringify({
        type: "item.completed",
        item: {
          id: "file-1",
          type: "file_change",
          status: "completed",
          changes: [{ path: "/task/work/inspect.js", kind: "add" }],
        },
      }),
      JSON.stringify({
        type: "item.started",
        item: {
          id: "cmd-1",
          type: "command_execution",
          command: "univer inspect workbook input.univer",
          status: "in_progress",
          exit_code: null,
          aggregated_output: "",
        },
      }),
      JSON.stringify({
        type: "item.completed",
        item: {
          id: "cmd-1",
          type: "command_execution",
          command: "univer inspect workbook input.univer",
          status: "completed",
          exit_code: 0,
          aggregated_output: "Workbook summary",
        },
      }),
      JSON.stringify({ type: "turn.completed", usage: { input_tokens: 8, output_tokens: 5 } }),
    ].join("\n") + "\n",
    "utf8",
  );

  const details = await readTaskDetails(root, "run-1", "task-1");

  assert.equal(details.taskId, "task-1");
  assert.equal(details.promptSections.instruction, "Fill B2 with the matching total.");
  assert.equal(details.promptSections.answer_position, "B2");
  assert.equal(details.finalMessage, "Final answer\n");
  assert.equal(details.eventLog.kind, "codex");
  assert.equal(details.eventLog.threadId, "thread-1");
  assert.deepEqual(details.eventLog.usage, { input: 8, output: 5, total: 13 });
  assert.deepEqual(details.eventLog.eventTypeCounts, {
    "item.completed": 3,
    "item.started": 1,
    "thread.started": 1,
    "turn.completed": 1,
  });
  assert.deepEqual(details.eventLog.itemTypeCounts, {
    agent_message: 1,
    command_execution: 1,
    file_change: 1,
  });
  assert.deepEqual(details.eventLog.nonItemEventTypes, ["thread.started", "turn.completed"]);
  assert.deepEqual(details.eventLog.unhandledItemTypes, []);
  assert.equal(details.eventLog.fileChangeCount, 1);
  assert.equal(details.eventLog.timeline.length, 3);
  assert.equal(details.eventLog.timeline[0].type, "agent_message");
  assert.equal(details.eventLog.timeline[1].type, "file_change");
  assert.deepEqual(details.eventLog.timeline[1].changes, [{ path: "/task/work/inspect.js", kind: "add" }]);
  assert.equal(details.eventLog.timeline[2].type, "command_execution");
  assert.equal(details.eventLog.timeline[2].output, "Workbook summary");
  assert.equal(details.workFiles.length, 1);
  assert.equal(details.workFiles[0].name, "inspect.js");
  assert.equal(details.workFiles[0].path, "/task/work/inspect.js");
  assert.equal(details.workFiles[0].content, "() => ({ success: true })\n");
  assert.equal(details.workFiles[0].size, Buffer.byteLength(details.workFiles[0].content));
  assert.deepEqual(details.outputFiles, [
    {
      caseName: "case_1",
      name: "output.xlsx",
      path: "/task/outputs/case_1/output.xlsx",
      size: 10,
      downloadUrl: "/api/runs/run-1/tasks/task-1/outputs/case_1/output.xlsx",
    },
  ]);
  assert.deepEqual(details.analysisMarkers, []);
});

test("resolveTaskOutputFile only resolves output.xlsx from a case directory", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "viewer-output-"));
  const outputPath = path.join(root, ".runs", "univer-agent", "run-1", "task-1", "task", "outputs", "case_1", "output.xlsx");
  await mkdir(path.dirname(outputPath), { recursive: true });
  await writeFile(outputPath, "xlsx bytes");

  const file = await resolveTaskOutputFile(root, "run-1", "task-1", "case_1", "output.xlsx");

  assert.equal(file.filePath, outputPath);
  assert.equal(file.downloadName, "run-1-task-1-case_1-output.xlsx");
  await assert.rejects(
    () => resolveTaskOutputFile(root, "run-1", "task-1", "case_1", "notes.txt"),
    /只允许下载 output\.xlsx/,
  );
});

test("readReportDetails returns summary and wrong-task links", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "viewer-report-"));
  await writeJson(path.join(root, "report", "run-2.json"), {
    accuracy: 0.5,
    correct_case_count: 1,
    error_case_count: 1,
    timeout_case_count: 0,
    total_case_count: 2,
    run: {
      metadata: { run_id: "run-2", agent: "codex", model: "gpt-5.5" },
      tasks: [
        { id: "pass-1", status: "ok", duration_seconds: 1 },
        { id: "fail-1", status: "ok", duration_seconds: 2 },
        { id: "timeout-1", status: "error", error: "Command timed out after 300 seconds", duration_seconds: 300 },
      ],
    },
    evaluate: {
      results: [
        { id: "pass-1", instruction_type: "Cell", test_case_results: [1] },
        { id: "fail-1", instruction_type: "Sheet", test_case_results: [0] },
      ],
    },
  });

  const report = await readReportDetails(root, "run-2.json");

  assert.equal(report.summary.runId, "run-2");
  assert.equal(report.summary.accuracy, 0.5);
  assert.deepEqual(
    report.wrongTasks.map((task) => [task.taskId, task.status, task.taskUrl]),
    [
      ["fail-1", "FAIL", "/runs/run-2/tasks/fail-1?report=run-2.json"],
      ["timeout-1", "TIMEOUT", "/runs/run-2/tasks/timeout-1?report=run-2.json"],
    ],
  );
});

test("app shell hosts the AntD frontend while APIs provide data", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "viewer-http-"));
  await writeJson(path.join(root, ".runs", "univer-agent", "run-1", "summary.json"), {
    metadata: { run_id: "run-1" },
    tasks: [{ id: "task-1", status: "ok" }],
  });

  assert.match(appShellHtml(), /id="root"/);
  assert.match(appShellHtml(), /antd/);
  assert.match(appShellHtml(), /dayjs/);
  assert.match(appShellHtml(), /SpreadsheetBench 运行日志查看器/);
  assert.equal((await readRunSummary(root, "run-1")).runId, "run-1");
});
