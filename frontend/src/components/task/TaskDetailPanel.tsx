import React, { useEffect, useMemo, useRef, useState } from "react";
import { FileText, Image as ImageIcon } from "lucide-react";
import * as XLSX from "xlsx";
import { jsPDF } from "jspdf";
import { Document, Packer, Paragraph, TextRun } from "docx";
import { saveAs } from "file-saver";

import { cn } from "../../utils/utils";
import type { Task } from "../../models/task";
import { parseOcrResult, type OcrLine } from "../../utils/ocrResult";
import { OCRService } from "../../services/ocr_service";

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

function normalizeRect(location: number[][]) {
  const xs = location.map((p) => p[0]);
  const ys = location.map((p) => p[1]);
  const left = Math.min(...xs);
  const top = Math.min(...ys);
  const right = Math.max(...xs);
  const bottom = Math.max(...ys);
  return { left, top, width: Math.max(1, right - left), height: Math.max(1, bottom - top) };
}

function drawOverlay(
  canvas: HTMLCanvasElement,
  image: HTMLImageElement,
  lines: OcrLine[],
  hovered: number | null,
  selected: number | null,
) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const rect = image.getBoundingClientRect();
  canvas.width = Math.max(1, Math.floor(rect.width));
  canvas.height = Math.max(1, Math.floor(rect.height));
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const scaleX = canvas.width / image.naturalWidth;
  const scaleY = canvas.height / image.naturalHeight;
  lines.forEach((line, index) => {
    if (!line.location || line.location.length === 0) return;
    const r = normalizeRect(line.location);
    const isActive = hovered === index || selected === index;
    ctx.strokeStyle = isActive ? "#ef4444" : "#06b6d4";
    ctx.lineWidth = isActive ? 3 : 2;
    ctx.strokeRect(r.left * scaleX, r.top * scaleY, r.width * scaleX, r.height * scaleY);
  });
}

function lineAtPoint(
  image: HTMLImageElement,
  lines: OcrLine[],
  x: number,
  y: number,
): number | null {
  if (!image.naturalWidth || !image.naturalHeight) return null;
  const rx = x * (image.naturalWidth / image.clientWidth);
  const ry = y * (image.naturalHeight / image.clientHeight);
  for (let i = 0; i < lines.length; i += 1) {
    const box = lines[i].location;
    if (!box || box.length === 0) continue;
    const r = normalizeRect(box);
    if (rx >= r.left && rx <= r.left + r.width && ry >= r.top && ry <= r.top + r.height) {
      return i;
    }
  }
  return null;
}

export const TaskDetailPanel: React.FC<TaskDetailPanelProps> = ({ task }) => {
  const parsed = useMemo(() => parseOcrResult(task?.result ?? null), [task?.result]);
  const [editedLines, setEditedLines] = useState<OcrLine[]>([]);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [hoverPos, setHoverPos] = useState<{ x: number; y: number } | null>(null);
  const [viewMode, setViewMode] = useState<"table" | "markdown">("table");
  const [savingCorrection, setSavingCorrection] = useState(false);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (parsed.type === "lines") {
      setEditedLines(parsed.lines);
    } else {
      setEditedLines([]);
    }
    setHoveredIndex(null);
    setSelectedIndex(null);
    setHoverPos(null);
  }, [task?.id, parsed]);

  useEffect(() => {
    const image = imageRef.current;
    const canvas = canvasRef.current;
    if (!image || !canvas || parsed.type !== "lines") return;
    drawOverlay(canvas, image, editedLines, hoveredIndex, selectedIndex);
  }, [editedLines, hoveredIndex, selectedIndex, parsed.type]);

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
    downloadBlob(`ocr-task-${task.id}.json`, content, "application/json;charset=utf-8");
  };

  const handleExportTxt = () => {
    downloadBlob(`ocr-task-${task.id}.txt`, fullTextForExport, "text/plain;charset=utf-8");
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
            new Paragraph({ children: [new TextRun({ text: `OCR Task #${task.id}`, bold: true })] }),
            new Paragraph({ text: "" }),
            ...editedLines.map(
              (line, idx) =>
                new Paragraph({
                  children: [
                    new TextRun(`${idx + 1}. ${line.words}`),
                    new TextRun(`  (conf=${(line.probability * 100).toFixed(2)}%)`),
                    new TextRun(
                      line.location?.length ? `  box=${JSON.stringify(line.location)}` : "",
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

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
        <h2 className="text-lg font-semibold text-gray-800">任务 #{task.id}</h2>
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
            <div className="relative rounded-xl overflow-hidden border border-gray-200 bg-white p-2 flex justify-center">
              <img
                ref={imageRef}
                src={task.file_url}
                alt="Task"
                className="h-full w-auto object-contain max-h-[250px]"
                onLoad={() => {
                  if (imageRef.current && canvasRef.current && parsed.type === "lines") {
                    drawOverlay(canvasRef.current, imageRef.current, editedLines, hoveredIndex, selectedIndex);
                  }
                }}
              />
              {parsed.type === "lines" && (
                <>
                  <canvas
                    ref={canvasRef}
                    className="absolute pointer-events-auto top-2 left-2 right-2 bottom-2 h-[calc(100%-1rem)] w-[calc(100%-1rem)]"
                    onMouseMove={(e) => {
                      if (!imageRef.current) return;
                      const rect = e.currentTarget.getBoundingClientRect();
                      const idx = lineAtPoint(imageRef.current, editedLines, e.clientX - rect.left, e.clientY - rect.top);
                      setHoveredIndex(idx);
                      setHoverPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
                    }}
                    onMouseLeave={() => {
                      setHoveredIndex(null);
                      setHoverPos(null);
                    }}
                    onClick={(e) => {
                      if (!imageRef.current) return;
                      const rect = e.currentTarget.getBoundingClientRect();
                      const idx = lineAtPoint(imageRef.current, editedLines, e.clientX - rect.left, e.clientY - rect.top);
                      setSelectedIndex(idx);
                    }}
                  />
                  {hoveredIndex !== null && hoverPos && editedLines[hoveredIndex] && (
                    <div
                      className="absolute z-10 max-w-xs rounded-md bg-black/90 border border-cyan-500/30 text-xs p-2 text-gray-100 pointer-events-none"
                      style={{ left: Math.min(hoverPos.x + 12, 320), top: Math.max(hoverPos.y - 8, 0) }}
                    >
                      <div>{editedLines[hoveredIndex].words}</div>
                      <div className="text-cyan-300 mt-1">
                        置信度: {(editedLines[hoveredIndex].probability * 100).toFixed(2)}%
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-gray-200 bg-gray-50 h-64 flex flex-col items-center justify-center text-gray-500 gap-3">
              <ImageIcon className="w-12 h-12 opacity-20" />
              <p className="text-sm">预览图片不可用</p>
            </div>
          )}

          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-3 uppercase tracking-wider">
              结构化识别结果
            </h3>
            <div className="flex flex-wrap gap-2 mb-4">
              <button onClick={handleExportJson} className="px-3 py-1 rounded bg-blue-600/80 hover:bg-blue-600 text-white text-sm">
                导出 JSON
              </button>
              <button onClick={handleExportExcel} className="px-3 py-1 rounded bg-emerald-600/80 hover:bg-emerald-600 text-white text-sm">
                导出 Excel
              </button>
              <button onClick={handleExportTxt} className="px-3 py-1 rounded bg-violet-600/80 hover:bg-violet-600 text-white text-sm">
                导出 TXT
              </button>
              <button onClick={handleExportWord} className="px-3 py-1 rounded bg-amber-600/80 hover:bg-amber-600 text-white text-sm">
                导出 Word
              </button>
              <button onClick={handleExportPdf} className="px-3 py-1 rounded bg-rose-600/80 hover:bg-rose-600 text-white text-sm">
                导出 PDF
              </button>
            </div>
            {parsed.type === "empty" && <div className="text-gray-500 italic">暂无结果...</div>}
            {parsed.type === "error" && <p className="text-red-400">解析结果出错</p>}
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
                      viewMode === "table" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700",
                    )}
                  >
                    表格视图
                  </button>
                  <button
                    onClick={() => setViewMode("markdown")}
                    className={cn(
                      "px-3 py-1 rounded text-sm",
                      viewMode === "markdown" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700",
                    )}
                  >
                    Markdown 视图
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
                        className={cn(
                          "bg-white p-2 rounded border flex justify-between items-start gap-3",
                          selectedIndex === idx ? "border-red-300" : "border-gray-200",
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
                    {editedLines.map((line, idx) => `${idx + 1}. ${line.words}`).join("\n")}
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
