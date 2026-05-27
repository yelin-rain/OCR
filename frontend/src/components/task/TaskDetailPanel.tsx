import React, { useEffect, useMemo, useState } from "react";
import { Download, FileText, Image as ImageIcon } from "lucide-react";
import * as XLSX from "xlsx";
import { jsPDF } from "jspdf";
import { Document, Packer, Paragraph, TextRun } from "docx";
import { saveAs } from "file-saver";

import { cn } from "../../utils/utils";
import type { Task } from "../../models/task";
import { parseOcrResult, type OcrLine } from "../../utils/ocrResult";
import { normalizeRect } from "../../utils/detectionImage";
import { OCRService } from "../../services/ocr_service";
import { DetectionImageStack } from "./DetectionImageStack";

interface TaskDetailPanelProps {
  task: Task | null;
}

function downloadBlob(filename: string, content: BlobPart, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function buildJsonExport(lines: OcrLine[], fullText: string) {
  return JSON.stringify(
    {
      words_result: lines,
      dt_boxes: lines.map((line) => line.location).filter(Boolean),
      full_text: fullText,
    },
    null,
    2,
  );
}

type ExportOption = {
  id: string;
  label: string;
  hint: string;
  onClick: () => void;
  disabled?: boolean;
};

function ExportDropdown({ items }: { items: ExportOption[] }) {
  const fallbackId =
    items.find((i) => !i.disabled)?.id ?? items[0]?.id ?? "json";
  const [format, setFormat] = useState(fallbackId);

  const resolvedId =
    items.find((i) => i.id === format && !i.disabled)?.id ?? fallbackId;
  const selected = items.find((i) => i.id === resolvedId);

  return (
    <div className="flex items-center gap-2 shrink-0">
      <select
        id="export-format"
        value={resolvedId}
        onChange={(e) => setFormat(e.target.value)}
        className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-800 min-w-[140px] focus:outline-none focus:ring-2 focus:ring-blue-500/30"
        aria-label="导出格式"
      >
        {items.map((item) => (
          <option key={item.id} value={item.id} disabled={item.disabled}>
            {item.label}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={() => selected?.onClick()}
        disabled={!selected || selected.disabled}
        title={selected?.hint}
        className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 disabled:opacity-50 transition-colors"
      >
        <Download className="w-4 h-4 text-gray-500" aria-hidden />
        导出
      </button>
    </div>
  );
}

export const TaskDetailPanel: React.FC<TaskDetailPanelProps> = ({ task }) => {
  const parsed = useMemo(
    () => parseOcrResult(task?.result ?? null),
    [task?.result],
  );
  const [editedLines, setEditedLines] = useState<OcrLine[]>([]);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<"table" | "markdown">("table");
  const [savingCorrection, setSavingCorrection] = useState(false);

  useEffect(() => {
    if (parsed.type === "lines") {
      setEditedLines(parsed.lines);
    } else {
      setEditedLines([]);
    }
    setHoveredIndex(null);
    setSelectedIndex(null);
  }, [task?.id, parsed]);

  const activeLineIndex = hoveredIndex ?? selectedIndex;

  if (!task) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-gray-500 gap-4">
        <FileText className="w-16 h-16 opacity-20" />
        <p>请从左侧列表选择一个任务</p>
      </div>
    );
  }

  const fullTextForExport =
    parsed.type === "lines"
      ? editedLines.map((l) => l.words).join("\n")
      : parsed.type === "text"
        ? parsed.text
        : "";

  const handleExportJson = () => {
    const content =
      parsed.type === "lines"
        ? buildJsonExport(editedLines, fullTextForExport)
        : JSON.stringify({ text: fullTextForExport }, null, 2);
    downloadBlob(
      `ocr-task-${task.id}.json`,
      content,
      "application/json;charset=utf-8",
    );
  };

  const handleExportTxt = () => {
    downloadBlob(
      `ocr-task-${task.id}.txt`,
      fullTextForExport,
      "text/plain;charset=utf-8",
    );
  };

  const handleExportPdf = async () => {
    if (!task.file_url) return;
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = task.file_url;
    await new Promise((resolve, reject) => {
      img.onload = resolve;
      img.onerror = reject;
    });
    const pdf = new jsPDF({
      orientation: img.naturalWidth >= img.naturalHeight ? "l" : "p",
      unit: "pt",
      format: [img.naturalWidth, img.naturalHeight],
    });
    pdf.addImage(img, "JPEG", 0, 0, img.naturalWidth, img.naturalHeight);
    editedLines.forEach((line) => {
      if (!line.location?.length) return;
      const r = normalizeRect(line.location);
      pdf.setDrawColor(6, 182, 212);
      pdf.rect(r.left, r.top, r.width, r.height);
      pdf.setTextColor(239, 68, 68);
      pdf.setFontSize(11);
      pdf.text(line.words, r.left, Math.max(12, r.top - 2));
    });
    pdf.save(`ocr-task-${task.id}-layout.pdf`);
  };

  const handleExportWord = async () => {
    const doc = new Document({
      sections: [
        {
          children: [
            new Paragraph({
              children: [
                new TextRun({ text: `OCR Task #${task.id}`, bold: true }),
              ],
            }),
            new Paragraph({ text: "" }),
            ...editedLines.map(
              (line, idx) =>
                new Paragraph({
                  children: [
                    new TextRun(`${idx + 1}. ${line.words}`),
                    new TextRun(
                      `  (conf=${(line.probability * 100).toFixed(2)}%)`,
                    ),
                    new TextRun(
                      line.location?.length
                        ? `  box=${JSON.stringify(line.location)}`
                        : "",
                    ),
                  ],
                }),
            ),
          ],
        },
      ],
    });
    const blob = await Packer.toBlob(doc);
    saveAs(blob, `ocr-task-${task.id}-layout.docx`);
  };

  const handleExportExcel = () => {
    const rows =
      parsed.type === "lines"
        ? editedLines.map((line, idx) => ({
            index: idx + 1,
            text: line.words,
            confidence: Number(line.probability.toFixed(4)),
            box: line.location ? JSON.stringify(line.location) : "",
          }))
        : [{ index: 1, text: fullTextForExport, confidence: "", box: "" }];
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(rows);
    XLSX.utils.book_append_sheet(wb, ws, "OCR");
    XLSX.writeFile(wb, `ocr-task-${task.id}.xlsx`);
  };

  const handleSaveCorrection = async () => {
    if (!task || parsed.type !== "lines") return;
    const original = parsed.lines;
    const corrections = editedLines
      .map((line, idx) => ({
        index: idx,
        original: original[idx]?.words ?? "",
        corrected: line.words,
      }))
      .filter((item) => item.original !== item.corrected);
    if (!corrections.length) return;
    try {
      setSavingCorrection(true);
      await OCRService.saveCorrection(task.id, corrections);
    } finally {
      setSavingCorrection(false);
    }
  };

  const exportOptions: ExportOption[] = [
    {
      id: "json",
      label: "JSON",
      hint: "结构化数据",
      onClick: handleExportJson,
    },
    {
      id: "excel",
      label: "Excel",
      hint: "表格与置信度",
      onClick: handleExportExcel,
    },
    { id: "txt", label: "TXT", hint: "纯文本", onClick: handleExportTxt },
    { id: "word", label: "Word", hint: "含框坐标", onClick: handleExportWord },
    {
      id: "pdf",
      label: "PDF",
      hint: "原图叠加框",
      onClick: handleExportPdf,
      disabled: !task.file_url,
    },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center gap-3">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold text-gray-800">任务 #{task.id}</h2>
          {task.model_version ? (
            <p className="text-xs text-gray-500 mt-0.5 truncate" title={task.model_version}>
              模型：{task.model_version}
            </p>
          ) : null}
        </div>
        <span
          className={cn(
            "px-3 py-1 rounded-full text-xs font-medium border",
            task.status === "COMPLETED"
              ? "bg-green-100 text-green-700 border-green-200"
              : task.status === "FAILED"
                ? "bg-red-100 text-red-700 border-red-200"
                : "bg-yellow-100 text-yellow-700 border-yellow-200",
          )}
        >
          {task.status}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto p-6">
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {task.file_url ? (
            parsed.type === "lines" ? (
              <DetectionImageStack
                imageUrl={task.file_url}
                lines={editedLines}
                activeIndex={activeLineIndex}
                onActiveIndexChange={(idx) => {
                  setSelectedIndex(idx);
                  setHoveredIndex(null);
                }}
              />
            ) : (
              <div className="rounded-xl border border-gray-200 bg-white p-2 flex justify-center">
                <img
                  src={task.file_url}
                  alt="Task"
                  crossOrigin="anonymous"
                  className="w-full max-h-[280px] object-contain"
                />
              </div>
            )
          ) : (
            <div className="rounded-xl border border-gray-200 bg-gray-50 h-64 flex flex-col items-center justify-center text-gray-500 gap-3">
              <ImageIcon className="w-12 h-12 opacity-20" />
              <p className="text-sm">预览图片不可用</p>
            </div>
          )}

          <div>
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">
                结构化识别结果
              </h3>
              <ExportDropdown key={task.id} items={exportOptions} />
            </div>
            {parsed.type === "empty" && (
              <div className="text-gray-500 italic">暂无结果...</div>
            )}
            {parsed.type === "error" && (
              <p className="text-red-400">解析结果出错</p>
            )}
            {parsed.type === "raw" && (
              <div className="bg-gray-50 p-4 rounded border border-red-100 text-xs text-gray-500 overflow-x-auto">
                <code>{JSON.stringify(parsed.raw, null, 2)}</code>
              </div>
            )}
            {parsed.type === "text" && (
              <div className="bg-gray-50 p-4 rounded border border-gray-200 whitespace-pre-wrap text-gray-700 font-mono text-sm">
                {parsed.text}
              </div>
            )}
            {parsed.type === "lines" && (
              <div className="space-y-3">
                <div className="flex gap-2">
                  <button
                    onClick={() => setViewMode("table")}
                    className={cn(
                      "px-3 py-1 rounded text-sm",
                      viewMode === "table"
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700",
                    )}
                  >
                    识别置信度
                  </button>
                  <button
                    onClick={() => setViewMode("markdown")}
                    className={cn(
                      "px-3 py-1 rounded text-sm",
                      viewMode === "markdown"
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700",
                    )}
                  >
                    识别结果
                  </button>
                  <button
                    onClick={handleSaveCorrection}
                    disabled={savingCorrection}
                    className="px-3 py-1 rounded text-sm bg-red-600/90 hover:bg-red-600 text-white disabled:opacity-60"
                  >
                    {savingCorrection ? "提交中..." : "纠错"}
                  </button>
                </div>
                {viewMode === "table" ? (
                  <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
                    {editedLines.map((line, idx) => (
                      <div
                        key={idx}
                        onClick={() => setSelectedIndex(idx)}
                        onMouseEnter={() => setHoveredIndex(idx)}
                        onMouseLeave={() => setHoveredIndex(null)}
                        className={cn(
                          "bg-white p-2 rounded border flex justify-between items-start gap-3 cursor-pointer",
                          activeLineIndex === idx
                            ? "border-red-300 bg-red-50/30"
                            : "border-gray-200",
                        )}
                      >
                        <input
                          value={line.words}
                          onChange={(e) => {
                            const next = [...editedLines];
                            next[idx] = { ...next[idx], words: e.target.value };
                            setEditedLines(next);
                          }}
                          className="flex-1 bg-white border border-gray-300 rounded px-2 py-1 text-gray-800"
                        />
                        <span className="text-blue-600 text-xs min-w-[80px] text-right">
                          {(line.probability * 100).toFixed(2)}%
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <pre className="bg-gray-50 border border-gray-200 rounded p-3 text-sm text-gray-700 whitespace-pre-wrap max-h-[380px] overflow-y-auto">
                    {editedLines
                      .map((line, idx) => `${idx + 1}. ${line.words}`)
                      .join("\n")}
                  </pre>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
