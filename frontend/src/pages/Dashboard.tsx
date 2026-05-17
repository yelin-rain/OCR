import React, { useCallback, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { OCRService } from "../services/ocr_service";
import {
  MonitoringService,
  type BackupTriggerResponse,
  type MonitoringSummary,
  type SystemLogEntry,
} from "../services/monitoring_service";
import {
  fetchMonitorStats,
  fetchBadCases,
  type BadCaseItem,
} from "../services/business_monitor_api";
import { parseOcrResult } from "../utils/ocrResult";
import type { Task } from "../models/task";
import { useAuth } from "../context/AuthContext";
import {
  FileText,
  Clock,
  Trash2,
  Eye,
  Activity,
  AlertTriangle,
  Database,
  ScrollText,
  HardDrive,
  Loader2,
  BarChart3,
  GitCompare,
  X,
} from "lucide-react";

const PIE_COLORS = ["#22c55e", "#ef4444", "#6366f1"];

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<MonitoringSummary | null>(null);
  const [logs, setLogs] = useState<SystemLogEntry[]>([]);
  const [backupBusy, setBackupBusy] = useState(false);
  const [backupToast, setBackupToast] = useState<string | null>(null);
  const [compareCase, setCompareCase] = useState<BadCaseItem | null>(null);
  const [compareTask, setCompareTask] = useState<Task | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);

  const { data: stats, dataUpdatedAt: statsUpdatedAt } = useQuery({
    queryKey: ["monitor-stats"],
    queryFn: fetchMonitorStats,
    refetchInterval: 10_000,
  });

  const { data: badCasesResp } = useQuery({
    queryKey: ["monitor-bad-cases"],
    queryFn: fetchBadCases,
    refetchInterval: 12_000,
  });

  const fetchTasks = async () => {
    try {
      const data = await OCRService.listTasks();
      setTasks(data);
    } catch (error) {
      console.error("Failed to fetch tasks", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchMonitoring = useCallback(async () => {
    try {
      const [sum, logEntries] = await Promise.all([
        MonitoringService.getSummary(),
        MonitoringService.listLogs({ limit: 30 }),
      ]);
      setSummary(sum);
      setLogs(logEntries);
    } catch (e) {
      console.error(e);
    }
  }, []);

  const openCompare = async (item: BadCaseItem) => {
    setCompareCase(item);
    setCompareTask(null);
    setCompareLoading(true);
    try {
      const t = await OCRService.getTask(item.task_id);
      setCompareTask(t);
    } catch (e) {
      console.error(e);
    } finally {
      setCompareLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定要删除该任务吗？")) return;
    try {
      await OCRService.deleteTask(id);
      setTasks(tasks.filter((t) => t.id !== id));
    } catch (error) {
      console.error("Failed to delete task", error);
    }
  };

  const handleBackup = async () => {
    setBackupBusy(true);
    setBackupToast(null);
    try {
      const res: BackupTriggerResponse =
        await MonitoringService.triggerBackup();
      setBackupToast(res.message);
      await fetchMonitoring();
    } catch (e: unknown) {
      const msg =
        e && typeof e === "object" && "response" in e
          ? String(
              (e as { response?: { data?: { detail?: string } } }).response
                ?.data?.detail ?? "备份请求失败",
            )
          : "备份请求失败";
      setBackupToast(msg);
    } finally {
      setBackupBusy(false);
    }
  };

  useEffect(() => {
    fetchTasks();
    fetchMonitoring();
    const intervalTasks = setInterval(fetchTasks, 3000);
    const intervalMon = setInterval(fetchMonitoring, 15000);
    return () => {
      clearInterval(intervalTasks);
      clearInterval(intervalMon);
    };
  }, [fetchMonitoring]);

  const pieData = stats
    ? [
        { name: "成功", value: stats.pie.success },
        { name: "失败", value: stats.pie.failed },
        { name: "处理中", value: stats.pie.in_progress },
      ]
    : [];

  const lowIds = stats?.low_confidence_task_ids ?? [];
  const parsedCompare =
    compareTask?.result != null ? parseOcrResult(compareTask.result) : null;
  const compareText =
    parsedCompare?.type === "lines"
      ? parsedCompare.fullText
      : parsedCompare?.type === "text"
        ? parsedCompare.text
        : parsedCompare?.type === "error" || parsedCompare?.type === "empty"
          ? "（无可用文本）"
          : JSON.stringify(parsedCompare?.raw ?? {}, null, 2);

  if (loading)
    return <div className="text-center py-20 text-gray-500">加载任务中...</div>;

  return (
    <div className="space-y-8">
      <header className="flex justify-between items-end pb-6 border-b border-gray-200">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">
            欢迎回来，{user?.username}
          </h2>
        </div>
      </header>

      {/* 业务感知监控 */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-gray-800">
            <BarChart3 className="w-5 h-5 text-violet-600" />
            <h3 className="text-lg font-semibold">业务感知监控</h3>
            <span className="text-xs text-gray-400">
              React Query 自动刷新
              {statsUpdatedAt
                ? ` · 上次 ${new Date(statsUpdatedAt).toLocaleTimeString()}`
                : ""}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          <div className="xl:col-span-2 bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="text-sm font-medium text-gray-800 mb-2">
              识别效率（近 24 小时 · 平均推理耗时 ms）
            </div>
            <div className="h-64 w-full min-w-0">
              {stats &&
              stats.latency_24h.some((p) => p.avg_inference_ms > 0) ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={stats.latency_24h}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis
                      dataKey="hour"
                      tick={{ fontSize: 10 }}
                      angle={-35}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="avg_inference_ms"
                      stroke="#7c3aed"
                      strokeWidth={2}
                      dot={false}
                      name="平均耗时(ms)"
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-gray-400 text-sm">
                  近 24 小时内暂无已完成任务的耗时数据
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="text-sm font-medium text-gray-800 mb-2">
              状态统计（近 24 小时）
            </div>
            <div className="h-64 w-full min-w-0">
              {stats && stats.pie.total > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={2}
                      label={({ name, value }) => `${name} ${value}`}
                    >
                      {pieData.map((_, i) => (
                        <Cell
                          key={i}
                          fill={PIE_COLORS[i % PIE_COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-gray-400 text-sm">
                  <p>暂无任务</p>
                  <p className="text-xs mt-1">总量 {stats?.pie.total ?? 0}</p>
                </div>
              )}
            </div>
            <p className="text-xs text-gray-500 mt-1 text-center">
              成功率 / 失败率 / 处理中 · 合计 {stats?.pie.total ?? 0}
            </p>
          </div>
        </div>

        <div className="bg-amber-50 border border-amber-200 rounded-xl overflow-hidden">
          <div className="px-4 py-2 border-b border-amber-200 text-amber-900 text-sm font-medium flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            质量预警 · 置信度 &lt; 80% 的任务 ID
          </div>
          <div className="relative h-12 overflow-hidden">
            {lowIds.length === 0 ? (
              <div className="h-full flex items-center px-4 text-amber-800/70 text-sm">
                当前无低置信度已完成任务
              </div>
            ) : (
              <div className="animate-marquee whitespace-nowrap flex gap-6 px-4 items-center h-full text-sm text-amber-950 font-mono">
                {[...lowIds, ...lowIds].map((id, i) => (
                  <span key={`${id}-${i}`}>#{id}</span>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* 坏例分析 */}
      <section className="space-y-3">
        <div className="flex items-center gap-2 text-gray-800">
          <GitCompare className="w-5 h-5 text-rose-600" />
          <h3 className="text-lg font-semibold">坏例分析（Bad Case）</h3>
          <span className="text-xs text-gray-500">
            识别不佳（低置信度或失败）一键对比原图与文本
          </span>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-gray-600 text-left">
                <tr>
                  <th className="px-4 py-2 font-medium">任务 ID</th>
                  <th className="px-4 py-2 font-medium">文件名</th>
                  <th className="px-4 py-2 font-medium">状态</th>
                  <th className="px-4 py-2 font-medium">平均置信度</th>
                  <th className="px-4 py-2 font-medium">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {(badCasesResp?.items ?? []).length === 0 ? (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-4 py-8 text-center text-gray-500"
                    >
                      暂无坏例记录
                    </td>
                  </tr>
                ) : (
                  (badCasesResp?.items ?? []).map((row) => (
                    <tr key={row.task_id} className="hover:bg-gray-50/80">
                      <td className="px-4 py-2 font-mono text-gray-800">
                        {row.task_id}
                      </td>
                      <td className="px-4 py-2 text-gray-700 max-w-xs truncate">
                        {row.filename}
                      </td>
                      <td className="px-4 py-2">
                        <span
                          className={`px-2 py-0.5 rounded text-xs ${
                            row.status === "FAILED"
                              ? "bg-red-100 text-red-800"
                              : "bg-amber-100 text-amber-900"
                          }`}
                        >
                          {row.status}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-gray-600">
                        {row.avg_confidence != null
                          ? (row.avg_confidence * 100).toFixed(1) + "%"
                          : "—"}
                      </td>
                      <td className="px-4 py-2">
                        <button
                          type="button"
                          onClick={() => openCompare(row)}
                          className="inline-flex items-center gap-1 text-violet-600 hover:text-violet-800 text-xs font-medium"
                        >
                          <GitCompare className="w-3.5 h-3.5" />
                          对比原图与文本
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {compareCase && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col border border-gray-200">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
              <div className="font-medium text-gray-900">
                坏例对比 · 任务 #{compareCase.task_id} · {compareCase.filename}
              </div>
              <button
                type="button"
                onClick={() => {
                  setCompareCase(null);
                  setCompareTask(null);
                }}
                className="p-2 rounded-lg hover:bg-gray-100 text-gray-500"
                aria-label="关闭"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-auto p-4 grid md:grid-cols-2 gap-4 min-h-[280px]">
              <div className="space-y-2">
                <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  原图
                </div>
                <div className="rounded-lg border border-gray-200 bg-gray-50 overflow-hidden flex items-center justify-center min-h-[200px]">
                  {compareCase.file_url ? (
                    <img
                      src={compareCase.file_url}
                      alt="原图"
                      className="max-w-full max-h-[360px] object-contain"
                    />
                  ) : (
                    <span className="text-gray-400 text-sm">无预览地址</span>
                  )}
                </div>
              </div>
              <div className="space-y-2 flex flex-col min-h-0">
                <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  识别文本
                </div>
                {compareLoading ? (
                  <div className="flex-1 flex items-center justify-center text-gray-500">
                    加载中…
                  </div>
                ) : (
                  <pre className="flex-1 text-sm text-gray-800 whitespace-pre-wrap break-words rounded-lg border border-gray-200 bg-gray-50 p-3 overflow-auto max-h-[360px] font-sans">
                    {compareText}
                  </pre>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 数据监控（基础设施） */}
      <section className="space-y-4">
        <div className="flex items-center gap-2 text-gray-800">
          <Activity className="w-5 h-5 text-indigo-600" />
          <h3 className="text-lg font-semibold">基础设施监控</h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="flex items-center gap-2 text-red-600 text-sm font-medium">
              <AlertTriangle className="w-4 h-4" />近 24 小时 · 异常（ERROR）
            </div>
            <p className="text-3xl font-bold text-gray-900 mt-2">
              {summary?.errors_last_24h ?? "—"}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="flex items-center gap-2 text-amber-600 text-sm font-medium">
              <ScrollText className="w-4 h-4" />近 24 小时 · 警告（WARNING）
            </div>
            <p className="text-3xl font-bold text-gray-900 mt-2">
              {summary?.warnings_last_24h ?? "—"}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="flex items-center gap-2 text-gray-600 text-sm font-medium">
              <Activity className="w-4 h-4" />近 24 小时 · 日志条数
            </div>
            <p className="text-3xl font-bold text-gray-900 mt-2">
              {summary?.total_logs_last_24h ?? "—"}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="flex items-center gap-2 text-emerald-700 text-sm font-medium">
              <Database className="w-4 h-4" />
              最近备份
            </div>
            <p className="text-sm text-gray-700 mt-2 leading-snug">
              {summary?.last_backup_at
                ? new Date(summary.last_backup_at).toLocaleString()
                : "尚无记录"}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              状态：{" "}
              {summary?.last_backup_ok === null ||
              summary?.last_backup_ok === undefined
                ? "—"
                : summary.last_backup_ok
                  ? "成功"
                  : "失败"}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
              <div className="flex items-center gap-2 text-gray-800 font-medium">
                <HardDrive className="w-4 h-4 text-indigo-600" />
                数据库备份
              </div>
              <button
                type="button"
                onClick={handleBackup}
                disabled={backupBusy}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-60"
              >
                {backupBusy ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Database className="w-4 h-4" />
                )}
                立即备份数据库
              </button>
            </div>
            <p className="text-xs text-gray-500 mb-2">
              每日 0:00（北京时间，服务端 APScheduler）将
              <strong>昨日已完成</strong>任务的识别结果 JSON 导出至{" "}
              <code className="bg-gray-100 px-1 rounded">
                backups/ocr_json_daily
              </code>
              。
            </p>
            <p className="text-xs text-gray-500 mb-2">
              手动备份优先使用{" "}
              <code className="bg-gray-100 px-1 rounded">pg_dump</code> 全量
              SQL；不可用时降级导出元数据 JSON。
            </p>
            {backupToast && (
              <p className="text-sm text-gray-700 bg-gray-50 border border-gray-100 rounded-lg px-3 py-2">
                {backupToast}
              </p>
            )}
            {summary && (
              <p className="text-xs text-gray-400 mt-3 break-all">
                备份目录：{summary.backup_dir}
              </p>
            )}
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm flex flex-col justify-center">
            <div className="text-sm font-medium text-gray-800 mb-1">
              定时任务
            </div>
            <p className="text-xs text-gray-600 leading-relaxed">
              APScheduler：每日凌晨触发识别结果 JSON
              归档，便于审计与追溯（与上方饼图/效率图数据源一致：任务表）。
            </p>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
            <ScrollText className="w-4 h-4 text-gray-600" />
            <span className="font-medium text-gray-800">
              系统日志（最近 30 条）
            </span>
          </div>
          <div className="overflow-x-auto max-h-80 overflow-y-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-gray-600 text-left">
                <tr>
                  <th className="px-4 py-2 font-medium">时间</th>
                  <th className="px-4 py-2 font-medium">级别</th>
                  <th className="px-4 py-2 font-medium">来源</th>
                  <th className="px-4 py-2 font-medium">摘要</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {logs.length === 0 ? (
                  <tr>
                    <td
                      colSpan={4}
                      className="px-4 py-8 text-center text-gray-500"
                    >
                      暂无日志记录
                    </td>
                  </tr>
                ) : (
                  logs.map((row) => (
                    <tr key={row.id} className="hover:bg-gray-50/80">
                      <td className="px-4 py-2 whitespace-nowrap text-gray-600">
                        {new Date(row.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-2">
                        <span
                          className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                            row.level === "ERROR"
                              ? "bg-red-100 text-red-800"
                              : row.level === "WARNING"
                                ? "bg-amber-100 text-amber-800"
                                : "bg-slate-100 text-slate-700"
                          }`}
                        >
                          {row.level}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-gray-700">{row.source}</td>
                      <td
                        className="px-4 py-2 text-gray-800 max-w-md truncate"
                        title={row.detail ?? row.message}
                      >
                        {row.message}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          {summary && (
            <div className="px-4 py-2 text-xs text-gray-400 border-t border-gray-100 break-all">
              应用文件日志：{summary.app_log_file}
            </div>
          )}
        </div>
      </section>

      {/* 任务列表 */}
      <section className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-800">近期 OCR 任务</h3>
        {tasks.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
            <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-medium text-gray-700">暂无任务</h3>
            <p className="text-gray-500 mt-2">上传文档后即可在此查看</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {tasks.map((task) => (
              <div
                key={task.id}
                className="bg-white p-4 rounded-xl border border-gray-200 flex items-center justify-between hover:border-gray-300 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div
                    className={`p-3 rounded-lg ${task.status === "COMPLETED" ? "bg-green-500/10 text-green-500" : "bg-blue-500/10 text-blue-500"}`}
                  >
                    <FileText className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-800">
                      {task.filename}
                    </h4>
                    <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(task.created_at).toLocaleDateString()}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs ${
                          task.status === "COMPLETED"
                            ? "bg-green-500/10 text-green-500"
                            : task.status === "FAILED"
                              ? "bg-red-500/10 text-red-500"
                              : "bg-blue-500/10 text-blue-500"
                        }`}
                      >
                        {task.status}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {task.file_url && (
                    <a
                      href={task.file_url}
                      target="_blank"
                      rel="noreferrer"
                      className="p-2 text-gray-400 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
                      title="查看原文件"
                    >
                      <Eye className="w-4 h-4" />
                    </a>
                  )}
                  <button
                    type="button"
                    onClick={() => handleDelete(task.id)}
                    className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
                    title="删除"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};

export default Dashboard;
