import React from "react";
import { FileText, Image as ImageIcon } from "lucide-react";

import { cn } from "../../utils/utils";
import type { Task } from "../../models/task";
import { parseOcrResult } from "../../utils/ocrResult";

interface TaskDetailPanelProps {
  task: Task | null;
}

function renderResult(resultStr: string | null) {
  const parsed = parseOcrResult(resultStr);
  switch (parsed.type) {
    case "empty":
      return <div className="text-gray-500 italic">暂无结果...</div>;
    case "words":
      return (
        <div className="space-y-2">
          {parsed.words.map((word, idx) => (
            <div
              key={idx}
              className="bg-gray-800/50 p-2 rounded border border-gray-700 flex justify-between items-start"
            >
              <span className="text-gray-200">{word}</span>
            </div>
          ))}
        </div>
      );
    case "text":
      return (
        <div className="bg-gray-800/50 p-4 rounded border border-gray-700 whitespace-pre-wrap text-gray-200 font-mono text-sm">
          {parsed.text}
        </div>
      );
    case "raw":
      return (
        <div className="bg-gray-900 p-4 rounded border border-red-500/20 text-xs text-gray-500 overflow-x-auto">
          <code>{JSON.stringify(parsed.raw, null, 2)}</code>
        </div>
      );
    case "error":
      return <p className="text-red-400">解析结果出错</p>;
  }
}

export const TaskDetailPanel: React.FC<TaskDetailPanelProps> = ({ task }) => {
  if (!task) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-gray-500 gap-4">
        <FileText className="w-16 h-16 opacity-20" />
        <p>请从左侧列表选择一个任务</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-gray-700 bg-gray-900/80 backdrop-blur flex justify-between items-center">
        <h2 className="text-lg font-semibold text-gray-100">任务 #{task.id}</h2>
        <span
          className={cn(
            "px-3 py-1 rounded-full text-xs font-medium border",
            task.status === "COMPLETED"
              ? "bg-green-500/10 text-green-400 border-green-500/20"
              : task.status === "FAILED"
                ? "bg-red-500/10 text-red-400 border-red-500/20"
                : "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
          )}
        >
          {task.status}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto p-6">
        <div className="grid grid-cols-1 gap-6">
          {task.file_url ? (
            <div className="rounded-xl overflow-hidden border border-gray-700 bg-gray-950/50 p-2 flex justify-center">
              <img
                src={task.file_url}
                alt="Task"
                className="h-full w-auto object-contain max-h-[250px]"
              />
            </div>
          ) : (
            <div className="rounded-xl border border-gray-700 bg-gray-950/50 h-64 flex flex-col items-center justify-center text-gray-500 gap-3">
              <ImageIcon className="w-12 h-12 opacity-20" />
              <p className="text-sm">预览图片不可用</p>
            </div>
          )}

          <div>
            <h3 className="text-sm font-medium text-gray-400 mb-3 uppercase tracking-wider">
              识别结果
            </h3>
            {renderResult(task.result)}
          </div>
        </div>
      </div>
    </div>
  );
};
