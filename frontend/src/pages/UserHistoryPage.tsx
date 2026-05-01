import React, { useEffect, useMemo, useState } from "react";
import { Clock, Eye, FileText, Search } from "lucide-react";
import * as XLSX from "xlsx";

import { OCRService } from "../services/ocr_service";
import type { Task } from "../models/task";
import { parseOcrResult } from "../utils/ocrResult";

type CorrectionItem = { index: number; original: string; corrected: string };

function parseCorrectionLog(raw?: string | null): CorrectionItem[] {
  if (!raw) return [];
  try {
    const data = JSON.parse(raw);
    if (!Array.isArray(data)) return [];
    return data
      .map((item) => ({
        index: Number(item?.index ?? 0),
        original: String(item?.original ?? ""),
        corrected: String(item?.corrected ?? ""),
      }))
      .filter((item) => item.original || item.corrected);
  } catch {
    return [];
  }
}

const UserHistoryPage: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [keyword, setKeyword] = useState("");
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [editedLines, setEditedLines] = useState<string[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await OCRService.listHistory({
          keyword: keyword || undefined,
          days: 7,
          limit: 100,
        });
        setTasks(data);
        if (selectedTask) {
          const latest = data.find((x) => x.id === selectedTask.id) ?? null;
          setSelectedTask(latest);
        }
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [keyword]);

  const selectedParsed = useMemo(
    () => parseOcrResult(selectedTask?.result ?? null),
    [selectedTask?.result],
  );
  const correctionItems = useMemo(
    () => parseCorrectionLog(selectedTask?.correction_log),
    [selectedTask?.correction_log],
  );

  useEffect(() => {
    if (selectedParsed.type === "lines") {
      setEditedLines(selectedParsed.lines.map((l) => l.words));
    } else {
      setEditedLines([]);
    }
  }, [selectedTask?.id, selectedParsed]);

  const selectedTasksForExport = useMemo(
    () => tasks.filter((t) => selectedIds.includes(t.id)),
    [tasks, selectedIds],
  );

  const handleBatchExport = () => {
    if (!selectedTasksForExport.length) return;
    const rows = selectedTasksForExport.map((task) => {
      const parsed = parseOcrResult(task.result);
      const text =
        parsed.type === "lines"
          ? parsed.lines.map((x) => x.words).join("\n")
          : parsed.type === "text"
            ? parsed.text
            : "";
      return {
        task_id: task.id,
        filename: task.filename,
        created_at: task.created_at,
        model_version: task.model_version ?? "",
        inference_ms: task.inference_ms ?? "",
        avg_confidence: task.avg_confidence ?? "",
        image_resolution:
          task.image_width && task.image_height ? `${task.image_width}x${task.image_height}` : "",
        text,
      };
    });
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(rows);
    XLSX.utils.book_append_sheet(wb, ws, "History");
    XLSX.writeFile(wb, "ocr-history-batch.xlsx");
  };

  const saveCurrentCorrection = async () => {
    if (!selectedTask || selectedParsed.type !== "lines") return;
    const corrections = editedLines
      .map((text, idx) => ({
        index: idx,
        original: selectedParsed.lines[idx]?.words ?? "",
        corrected: text,
      }))
      .filter((x) => x.original !== x.corrected);
    if (!corrections.length) return;
    const updated = await OCRService.saveCorrection(selectedTask.id, corrections);
    setSelectedTask(updated);
    setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
  };

  if (loading) {
    return <div className="text-center py-20 text-gray-500">Loading history...</div>;
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between border-b border-gray-200 pb-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">用户识别历史管理台</h2>
          <p className="text-gray-500 text-sm mt-1">最近 7 天识别记录，支持关键词检索与纠错记录审计</p>
        </div>
        <div className="w-full md:w-80 bg-white border border-gray-300 rounded-lg px-3 flex items-center gap-2">
          <Search className="w-4 h-4 text-gray-500" />
          <input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="搜文件名/识别文本..."
            className="w-full bg-transparent py-2 text-gray-800 outline-none"
          />
        </div>
      </header>

      <div className="flex items-center justify-between text-sm text-gray-600">
        <div>已选中 {selectedIds.length} 条记录用于批量导出</div>
        <button
          onClick={handleBatchExport}
          className="px-3 py-1 rounded bg-emerald-600/80 hover:bg-emerald-600 text-white disabled:opacity-50"
          disabled={selectedIds.length === 0}
        >
          批量导出 Excel
        </button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <section className="xl:col-span-1 bg-white border border-gray-200 rounded-xl p-3 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-1 gap-2 max-h-[70vh] overflow-y-auto">
          {tasks.length === 0 && (
            <div className="text-gray-500 text-sm py-8 text-center">最近一周没有匹配的历史记录</div>
          )}
          {tasks.map((task) => (
            <button
              key={task.id}
              onClick={() => setSelectedTask(task)}
              className={`w-full text-left p-3 rounded-lg border transition-colors ${
                selectedTask?.id === task.id
                  ? "border-blue-300 bg-blue-50"
                  : "border-gray-200 bg-white hover:border-gray-300"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <input
                  type="checkbox"
                  checked={selectedIds.includes(task.id)}
                  onChange={(e) => {
                    e.stopPropagation();
                    setSelectedIds((prev) =>
                      prev.includes(task.id) ? prev.filter((x) => x !== task.id) : [...prev, task.id],
                    );
                  }}
                />
                <span className="text-xs text-gray-500">#{task.id}</span>
              </div>
              {task.file_url && (
                <img
                  src={task.file_url}
                  alt={task.filename}
                  className="w-full h-24 object-cover rounded border border-gray-200 mb-2"
                />
              )}
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-800 font-medium truncate">{task.filename}</div>
              </div>
              <div className="mt-2 text-xs text-gray-500 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {new Date(task.created_at).toLocaleString()}
              </div>
            </button>
          ))}
        </section>

        <section className="xl:col-span-2 bg-white border border-gray-200 rounded-xl p-4 space-y-4">
          {!selectedTask ? (
            <div className="text-gray-500 py-10 text-center">选择左侧历史记录查看详情</div>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <h3 className="text-lg text-gray-900 font-semibold">{selectedTask.filename}</h3>
                {selectedTask.file_url && (
                  <a
                    href={selectedTask.file_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm text-blue-600 hover:text-blue-700 inline-flex items-center gap-1"
                  >
                    <Eye className="w-4 h-4" />
                    查看原图
                  </a>
                )}
              </div>

              <div>
                <h4 className="text-sm uppercase tracking-wider text-gray-500 mb-2 flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  识别结果
                </h4>
                {selectedParsed.type === "lines" ? (
                  <div className="space-y-2 max-h-[260px] overflow-y-auto pr-1">
                    {editedLines.map((line, idx) => (
                      <div key={idx} className="bg-gray-50 border border-gray-200 rounded p-2 text-sm text-gray-800">
                        <label className="text-xs text-gray-500 mr-2">{idx + 1}.</label>
                        <input
                          value={line}
                          onChange={(e) => {
                            const next = [...editedLines];
                            next[idx] = e.target.value;
                            setEditedLines(next);
                          }}
                          className="bg-white border border-gray-300 rounded px-2 py-1 w-[90%]"
                        />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-gray-700 bg-gray-50 border border-gray-200 rounded p-3 whitespace-pre-wrap">
                    {selectedTask.result ?? "无结果"}
                  </div>
                )}
              </div>

              <div>
                <h4 className="text-sm uppercase tracking-wider text-gray-500 mb-2">纠错记录</h4>
                <button
                  onClick={saveCurrentCorrection}
                  className="mb-3 px-3 py-1 rounded bg-red-600/90 hover:bg-red-600 text-white text-sm"
                >
                  保存本次编辑到纠错记录
                </button>
                {correctionItems.length === 0 ? (
                  <div className="text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded p-3">
                    暂无纠错记录
                  </div>
                ) : (
                  <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
                    {correctionItems.map((item) => (
                      <div key={`${item.index}-${item.original}-${item.corrected}`} className="bg-gray-50 border border-gray-200 rounded p-3">
                        <div className="text-xs text-gray-500 mb-1">行 {item.index + 1}</div>
                        <div className="text-sm text-gray-700">
                          <span className="text-red-600">{item.original || "(空)"}</span>
                          <span className="mx-2 text-gray-400">→</span>
                          <span className="text-green-700">{item.corrected || "(空)"}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
};

export default UserHistoryPage;
