(function () {
  const e = React.createElement;
  const {
    Alert,
    Badge,
    Button,
    Card,
    Checkbox,
    Collapse,
    Descriptions,
    Empty,
    Input,
    Layout,
    Menu,
    Segmented,
    Space,
    Spin,
    Statistic,
    Table,
    Tabs,
    Tag,
    Timeline,
    Typography,
  } = antd;
  const { Header, Content } = Layout;
  const { Paragraph, Text, Title } = Typography;

  const statusColors = {
    PASS: "success",
    FAIL: "error",
    TIMEOUT: "warning",
    ERROR: "error",
    NOT_RUN: "default",
    ok: "success",
    error: "error",
    timeout: "warning",
    completed: "success",
    failed: "error",
    in_progress: "processing",
  };

  function pathParts() {
    return window.location.pathname.split("/").filter(Boolean).map(decodeURIComponent);
  }

  function navigate(path) {
    window.history.pushState(null, "", path);
    window.dispatchEvent(new Event("viewer:navigate"));
  }

  async function fetchJson(url) {
    const response = await fetch(url);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `请求失败：${response.status}`);
    return data;
  }

  function useAsync(factory, deps) {
    const [state, setState] = React.useState({ loading: true, error: null, data: null });
    React.useEffect(() => {
      let cancelled = false;
      setState({ loading: true, error: null, data: null });
      factory()
        .then((data) => {
          if (!cancelled) setState({ loading: false, error: null, data });
        })
        .catch((error) => {
          if (!cancelled) setState({ loading: false, error, data: null });
        });
      return () => {
        cancelled = true;
      };
    }, deps);
    return state;
  }

  function StatusTag({ value }) {
    return e(Tag, { color: statusColors[value] || "default" }, value || "未知");
  }

  function percent(value) {
    return value == null ? "无" : `${Math.round(Number(value) * 1000) / 10}%`;
  }

  function ErrorState({ error }) {
    return e(Alert, { type: "error", showIcon: true, message: error.message || String(error) });
  }

  function LoadingState() {
    return e("div", { className: "centerState" }, e(Spin), e("span", null, "加载中..."));
  }

  function PageHeader({ title, subtitle, extra }) {
    return e(
      "div",
      { className: "pageHeader" },
      e("div", null, e(Title, { level: 3 }, title), subtitle ? e(Text, { type: "secondary" }, subtitle) : null),
      e(Space, null, extra),
    );
  }

  function HomePage() {
    const { loading, error, data } = useAsync(() => fetchJson("/api/home"), []);
    const [query, setQuery] = React.useState("");
    if (loading) return e(LoadingState);
    if (error) return e(ErrorState, { error });

    const q = query.trim().toLowerCase();
    const reports = data.reports.filter((report) =>
      [report.fileName, report.runId, report.agent, report.model, report.dataset].join(" ").toLowerCase().includes(q),
    );
    const runs = data.runs.filter((run) =>
      [run.runId, run.metadata?.agent, run.metadata?.model, run.metadata?.dataset].join(" ").toLowerCase().includes(q),
    );

    const reportColumns = [
      {
        title: "报告",
        dataIndex: "fileName",
        render: (value) => e(Button, { type: "link", onClick: () => navigate(`/reports/${encodeURIComponent(value)}`) }, value),
      },
      {
        title: "运行 ID",
        dataIndex: "runId",
        render: (value) => e(Button, { type: "link", onClick: () => navigate(`/runs/${encodeURIComponent(value)}`) }, value),
      },
      { title: "Agent / 模型", render: (_, row) => [row.agent, row.model].filter(Boolean).join(" / ") },
      { title: "数据集", dataIndex: "dataset" },
      { title: "准确率", dataIndex: "accuracy", render: percent, sorter: (a, b) => (a.accuracy || 0) - (b.accuracy || 0) },
      { title: "通过", dataIndex: "correct", sorter: (a, b) => (a.correct || 0) - (b.correct || 0) },
      { title: "错误", dataIndex: "error", sorter: (a, b) => (a.error || 0) - (b.error || 0) },
      { title: "超时", dataIndex: "timeout", sorter: (a, b) => (a.timeout || 0) - (b.timeout || 0) },
    ];
    const runColumns = [
      {
        title: "运行 ID",
        dataIndex: "runId",
        render: (value) => e(Button, { type: "link", onClick: () => navigate(`/runs/${encodeURIComponent(value)}`) }, value),
      },
      { title: "Agent / 模型", render: (_, row) => [row.metadata?.agent, row.metadata?.model].filter(Boolean).join(" / ") },
      { title: "数据集", render: (_, row) => row.metadata?.dataset },
      { title: "任务数", dataIndex: "totalTasks", sorter: (a, b) => a.totalTasks - b.totalTasks },
      {
        title: "状态",
        render: (_, row) =>
          e(
            Space,
            { wrap: true },
            Object.entries(row.statusCounts || {}).map(([status, count]) =>
              e(Tag, { key: status, color: statusColors[status] || "default" }, `${status}: ${count}`),
            ),
          ),
      },
    ];

    return e(
      Space,
      { direction: "vertical", size: 16, className: "fullWidth" },
      e(PageHeader, { title: "报告", subtitle: "优先从报告进入，快速跳转到错题和 agent 时间线。" }),
      e(Input.Search, { placeholder: "搜索报告、运行、模型、数据集", allowClear: true, onChange: (event) => setQuery(event.target.value) }),
      e(Card, { title: `报告 (${reports.length})` }, e(Table, { rowKey: "fileName", columns: reportColumns, dataSource: reports, size: "small", pagination: { pageSize: 12 } })),
      e(Card, { title: `运行 (${runs.length})` }, e(Table, { rowKey: "runId", columns: runColumns, dataSource: runs, size: "small", pagination: { pageSize: 12 } })),
    );
  }

  function ReportPage({ fileName }) {
    const { loading, error, data } = useAsync(() => fetchJson(`/api/reports/${encodeURIComponent(fileName)}`), [fileName]);
    const [query, setQuery] = React.useState("");
    const [wrongOnly, setWrongOnly] = React.useState(true);
    if (loading) return e(LoadingState);
    if (error) return e(ErrorState, { error });

    const rows = (wrongOnly ? data.wrongTasks : data.tasks).filter((task) =>
      [task.taskId, task.status, task.instructionType, task.error].join(" ").toLowerCase().includes(query.toLowerCase()),
    );
    const columns = [
      {
        title: "任务",
        dataIndex: "taskId",
        render: (value, row) => e(Button, { type: "link", onClick: () => navigate(row.taskUrl) }, value),
      },
      { title: "状态", dataIndex: "status", render: (value) => e(StatusTag, { value }) },
      { title: "指令类型", dataIndex: "instructionType" },
      { title: "耗时", dataIndex: "durationSeconds", render: (value) => (value == null ? "-" : `${value}s`) },
      { title: "错误", dataIndex: "error", ellipsis: true },
    ];

    return e(
      Space,
      { direction: "vertical", size: 16, className: "fullWidth" },
      e(PageHeader, {
        title: fileName,
        subtitle: "报告总结、运行入口和错题跳转列表",
        extra: e(Button, { onClick: () => navigate(data.summary.runUrl) }, "打开运行"),
      }),
      e(
        "div",
        { className: "statsGrid" },
        e(Card, null, e(Statistic, { title: "准确率", value: percent(data.summary.accuracy) })),
        e(Card, null, e(Statistic, { title: "通过", value: data.summary.correct })),
        e(Card, null, e(Statistic, { title: "错误", value: data.summary.error, valueStyle: { color: "#cf1322" } })),
        e(Card, null, e(Statistic, { title: "超时", value: data.summary.timeout, valueStyle: { color: "#ad6800" } })),
      ),
      e(Card, { title: "运行" }, e(Descriptions, { size: "small", column: 2, items: [
        { key: "run", label: "运行 ID", children: e(Button, { type: "link", onClick: () => navigate(data.summary.runUrl) }, data.summary.runId) },
        { key: "agent", label: "Agent", children: data.summary.agent },
        { key: "model", label: "模型", children: data.summary.model },
        { key: "dataset", label: "数据集", children: data.summary.dataset },
      ] })),
      e(
        Card,
        {
          title: `${wrongOnly ? "错题" : "全部任务"} (${rows.length})`,
          extra: e(Space, null, e(Checkbox, { checked: wrongOnly, onChange: (event) => setWrongOnly(event.target.checked) }, "只看错题")),
        },
        e(Input.Search, { className: "tableSearch", placeholder: "搜索任务、状态、错误", allowClear: true, onChange: (event) => setQuery(event.target.value) }),
        e(Table, { rowKey: "taskId", columns, dataSource: rows, size: "small", pagination: { pageSize: 20 } }),
      ),
    );
  }

  function RunPage({ runId }) {
    const { loading, error, data } = useAsync(() => fetchJson(`/api/runs/${encodeURIComponent(runId)}`), [runId]);
    const [query, setQuery] = React.useState("");
    if (loading) return e(LoadingState);
    if (error) return e(ErrorState, { error });
    const rows = data.tasks.filter((task) => [task.id, task.status, task.error].join(" ").toLowerCase().includes(query.toLowerCase()));
    const columns = [
      { title: "任务", dataIndex: "id", render: (value) => e(Button, { type: "link", onClick: () => navigate(`/runs/${encodeURIComponent(runId)}/tasks/${encodeURIComponent(value)}`) }, value) },
      { title: "状态", dataIndex: "status", render: (value) => e(StatusTag, { value }) },
      { title: "耗时", dataIndex: "durationSeconds", render: (value) => (value == null ? "-" : `${value}s`) },
      { title: "错误", dataIndex: "error", ellipsis: true },
    ];
    return e(
      Space,
      { direction: "vertical", size: 16, className: "fullWidth" },
      e(PageHeader, { title: data.runId, subtitle: "运行任务列表" }),
      e(Card, { title: "元信息" }, e(Descriptions, { size: "small", column: 2, items: [
        { key: "agent", label: "Agent", children: data.metadata?.agent },
        { key: "model", label: "模型", children: data.metadata?.model },
        { key: "dataset", label: "数据集", children: data.metadata?.dataset },
        { key: "tasks", label: "任务数", children: data.totalTasks },
      ] })),
      e(Card, { title: `任务 (${rows.length})` }, e(Input.Search, { className: "tableSearch", placeholder: "搜索任务", allowClear: true, onChange: (event) => setQuery(event.target.value) }), e(Table, { rowKey: "id", columns, dataSource: rows, size: "small", pagination: { pageSize: 30 } })),
    );
  }

  function QuestionPanel({ task }) {
    const sections = task.promptSections || {};
    return e(
      Space,
      { direction: "vertical", className: "fullWidth", size: 12 },
      e(Alert, { type: "info", showIcon: true, message: "题目上下文", description: "先理解题目和答案位置，再查看时间线与命令。" }),
      e(Card, { title: "任务要求" }, e(Paragraph, null, sections.instruction || "未提取到任务要求。")),
      e(Card, { title: "答案位置" }, e(Text, { code: true }, sections.answer_position || "无")),
      e(Card, { title: "输出路径" }, e("pre", { className: "codeBlock" }, sections.output_path || "无")),
      e(Collapse, { items: [{ key: "prompt", label: "完整 prompt.md", children: e("pre", { className: "codeBlock" }, task.prompt || "") }] }),
    );
  }

  function TimelinePanel({ eventLog }) {
    const [query, setQuery] = React.useState("");
    const [mode, setMode] = React.useState("all");
    if (!eventLog) return e(Empty, { description: "未找到 JSONL 事件日志" });
    const timeline = (eventLog.timeline || []).filter((item) => {
      if (mode === "messages" && item.type !== "agent_message") return false;
      if (mode === "commands" && item.type !== "command_execution") return false;
      if (mode === "files" && item.type !== "file_change") return false;
      if (mode === "failures" && !(item.type === "command_execution" && item.failed)) return false;
      const changeText = (item.changes || []).map((change) => `${change.kind} ${change.path}`).join(" ");
      const haystack = [item.text, item.command, item.output, item.status, item.exitCode, changeText].join(" ").toLowerCase();
      return haystack.includes(query.toLowerCase());
    });
    const items = timeline.map((item, index) => {
      if (item.type === "agent_message") {
        return {
          color: "blue",
          children: e(Card, { size: "small", title: `Agent 消息 ${index + 1}` }, e("pre", { className: "messageBlock" }, item.text || "")),
        };
      }
      if (item.type === "file_change") {
        return {
          color: "purple",
          children: e(
            Card,
            { size: "small", title: e(Space, { wrap: true }, e("span", null, `文件变更 ${index + 1}`), e(StatusTag, { value: item.status })) },
            e(
              Space,
              { direction: "vertical", className: "fullWidth" },
              (item.changes || []).map((change, changeIndex) =>
                e(
                  Space,
                  { key: `${change.path}-${changeIndex}`, wrap: true },
                  e(Tag, null, change.kind || "change"),
                  e(Text, { code: true }, change.path || ""),
                ),
              ),
            ),
          ),
        };
      }
      return {
        color: item.failed ? "red" : item.exitCode === 0 ? "green" : "gray",
        children: e(
          Card,
          {
            size: "small",
            title: e(Space, { wrap: true }, e("span", null, `命令 ${index + 1}`), e(StatusTag, { value: item.exitCode === 0 ? "ok" : item.failed ? "error" : item.status }), e(Text, { type: "secondary" }, `退出码 ${item.exitCode ?? "-"}`)),
          },
          e("pre", { className: "codeBlock commandLine" }, item.command || ""),
          e(Collapse, { size: "small", items: [{ key: "output", label: `输出 (${(item.output || "").length} 字符)`, children: e("pre", { className: "codeBlock" }, item.output || "") }] }),
        ),
      };
    });
    return e(
      Space,
      { direction: "vertical", className: "fullWidth", size: 12 },
      e(Card, null, e(Space, { wrap: true }, e(Tag, null, eventLog.fileName), e(Tag, null, `事件 ${eventLog.eventCount}`), e(Tag, null, `消息 ${eventLog.messageCount}`), e(Tag, null, `命令 ${eventLog.commandCount}`), e(Tag, null, `文件 ${eventLog.fileChangeCount || 0}`), e(Tag, { color: eventLog.failedCommandCount ? "error" : "success" }, `失败 ${eventLog.failedCommandCount}`), e(Tag, null, `元事件 ${(eventLog.nonItemEventTypes || []).join(", ") || "无"}`), e(Tag, { color: eventLog.unhandledItemTypes?.length ? "warning" : "success" }, `未展示 item ${eventLog.unhandledItemTypes?.length || 0}`), e(Tag, null, `token ${eventLog.usage?.total ?? "无"}`))),
      e(Space, { wrap: true }, e(Input.Search, { placeholder: "搜索时间线文本、命令、输出", allowClear: true, onChange: (event) => setQuery(event.target.value), style: { width: 360 } }), e(Segmented, { value: mode, options: [
        { label: "全部", value: "all" },
        { label: "消息", value: "messages" },
        { label: "命令", value: "commands" },
        { label: "文件", value: "files" },
        { label: "失败", value: "failures" },
      ], onChange: setMode })),
      e(Timeline, { className: "agentTimeline", items }),
    );
  }

  function WorkFilesPanel({ files }) {
    if (!files?.length) return e(Empty, { description: "未找到 /task/work 文件" });
    return e(
      Collapse,
      {
        items: files.map((file) => ({
          key: file.path,
          label: e(Space, { wrap: true }, e(Text, { strong: true }, file.name), e(Tag, null, `${file.size} 字节`), e(Text, { type: "secondary" }, file.path)),
          children: e("pre", { className: "codeBlock" }, file.content || ""),
        })),
      },
    );
  }

  function CommandsPanel({ eventLog }) {
    const [query, setQuery] = React.useState("");
    const commands = (eventLog?.timeline || []).filter((item) => item.type === "command_execution");
    const rows = commands.filter((item) => [item.command, item.output, item.status, item.exitCode].join(" ").toLowerCase().includes(query.toLowerCase()));
    return e(
      Space,
      { direction: "vertical", className: "fullWidth" },
      e(Input.Search, { placeholder: "搜索命令和输出", allowClear: true, onChange: (event) => setQuery(event.target.value) }),
      e(
        Collapse,
        {
          items: rows.map((command, index) => ({
            key: `${index}`,
            label: e(Space, { wrap: true }, e(Text, { strong: true }, `命令 ${index + 1}`), e(StatusTag, { value: command.exitCode === 0 ? "ok" : command.failed ? "error" : command.status }), e(Text, { type: "secondary" }, command.command)),
            children: e(Space, { direction: "vertical", className: "fullWidth" }, e("pre", { className: "codeBlock" }, command.command), e("pre", { className: "codeBlock" }, command.output || "")),
          })),
        },
      ),
    );
  }

  function TaskPage({ runId, taskId }) {
    const params = new URLSearchParams(window.location.search);
    const reportFile = params.get("report");
    const taskState = useAsync(() => fetchJson(`/api/runs/${encodeURIComponent(runId)}/tasks/${encodeURIComponent(taskId)}`), [runId, taskId]);
    const reportState = useAsync(() => (reportFile ? fetchJson(`/api/reports/${encodeURIComponent(reportFile)}`) : Promise.resolve(null)), [reportFile]);
    if (taskState.loading || reportState.loading) return e(LoadingState);
    if (taskState.error) return e(ErrorState, { error: taskState.error });
    if (reportState.error) return e(ErrorState, { error: reportState.error });
    const task = taskState.data;
    const reportTask = reportState.data?.tasks?.find((row) => row.taskId === taskId);
    const commands = task.eventLog?.timeline?.filter((item) => item.type === "command_execution") || [];
    const fileChanges = task.eventLog?.timeline?.filter((item) => item.type === "file_change") || [];
    const markers = task.analysisMarkers || [];
    const tabs = [
      { key: "overview", label: "概览", children: e(Space, { direction: "vertical", className: "fullWidth" }, e(Alert, { type: reportTask?.status === "PASS" ? "success" : "warning", showIcon: true, message: `报告状态：${reportTask?.status || "无"}` }), e(Descriptions, { bordered: true, size: "small", column: 2, items: [
        { key: "run", label: "运行", children: runId },
        { key: "task", label: "任务", children: taskId },
        { key: "answer", label: "答案位置", children: task.promptSections?.answer_position || "无" },
        { key: "duration", label: "耗时", children: task.timing?.duration_seconds == null ? "无" : `${task.timing.duration_seconds}s` },
        { key: "returncode", label: "返回码", children: task.timing?.returncode ?? "无" },
        { key: "commands", label: "命令数", children: commands.length },
        { key: "files", label: "工作文件", children: task.workFiles?.length || 0 },
        { key: "changes", label: "文件变更", children: fileChanges.length },
      ] }) ) },
      { key: "question", label: "题目", children: e(QuestionPanel, { task }) },
      { key: "timeline", label: e(Badge, { count: task.eventLog?.failedCommandCount || 0, offset: [8, -2] }, "时间线"), children: e(TimelinePanel, { eventLog: task.eventLog }) },
      { key: "commands", label: "命令", children: e(CommandsPanel, { eventLog: task.eventLog }) },
      { key: "files", label: "工作文件", children: e(WorkFilesPanel, { files: task.workFiles }) },
      { key: "final", label: "最终回复", children: e("pre", { className: "codeBlock" }, task.finalMessage || "") },
      { key: "raw", label: "原始数据", children: e("pre", { className: "codeBlock" }, JSON.stringify({ timing: task.timing, eventLog: task.eventLog, workFiles: task.workFiles }, null, 2)) },
    ];
    return e(
      "div",
      null,
      e(PageHeader, { title: `${runId} / ${taskId}`, subtitle: "用于人工分析题目和 agent 解题过程的工作区" }),
      e(
        "div",
        { className: "taskGrid" },
        e(
          Space,
          { direction: "vertical", size: 12, className: "fullWidth" },
          e(Card, { title: "分析检查清单" }, e(Space, { direction: "vertical" }, ["理解任务要求", "确认 answer_position", "复核 agent 计划", "检查失败命令", "对比 output/golden"].map((text) => e(Checkbox, { key: text }, text)))),
          e(Card, { title: "上下文" }, e(Descriptions, { size: "small", column: 1, items: [
            { key: "status", label: "报告状态", children: e(StatusTag, { value: reportTask?.status || "无" }) },
            { key: "type", label: "指令类型", children: reportTask?.instructionType || "无" },
            { key: "event", label: "事件日志", children: task.eventLog?.fileName || "无" },
            { key: "work", label: "工作文件", children: task.workFiles?.length || 0 },
            { key: "tokens", label: "Token", children: task.eventLog?.usage?.total || "无" },
          ] })),
          e(Card, { title: "标记" }, markers.length ? e(Space, { wrap: true }, markers.map((marker) => e(Tag, { key: marker.text, color: marker.level === "error" ? "error" : "warning" }, marker.text))) : e(Tag, { color: "success" }, "未发现明显标记")),
        ),
        e(Card, { className: "taskMain" }, e(Tabs, { defaultActiveKey: "timeline", items: tabs })),
      ),
    );
  }

  function App() {
    const [, forceRender] = React.useReducer((x) => x + 1, 0);
    React.useEffect(() => {
      const rerender = () => forceRender();
      window.addEventListener("popstate", rerender);
      window.addEventListener("viewer:navigate", rerender);
      return () => {
        window.removeEventListener("popstate", rerender);
        window.removeEventListener("viewer:navigate", rerender);
      };
    }, []);
    const parts = pathParts();
    let page = e(HomePage);
    if (parts[0] === "reports" && parts[1]) page = e(ReportPage, { fileName: parts[1] });
    if (parts[0] === "runs" && parts[1] && !parts[2]) page = e(RunPage, { runId: parts[1] });
    if (parts[0] === "runs" && parts[1] && parts[2] === "tasks" && parts[3]) page = e(TaskPage, { runId: parts[1], taskId: parts[3] });
    return e(
      Layout,
      { className: "appLayout" },
      e(Header, { className: "appHeader" }, e("div", { className: "brand", onClick: () => navigate("/") }, "SpreadsheetBench 运行日志查看器"), e(Menu, { mode: "horizontal", selectable: false, items: [{ key: "home", label: e("span", { onClick: () => navigate("/") }, "首页") }] })),
      e(Content, { className: "appContent" }, page),
    );
  }

  ReactDOM.createRoot(document.getElementById("root")).render(e(App));
})();
