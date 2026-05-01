import React from "react";
import { CheckCircle2, Clock, Image as ImageIcon, Trash2, XCircle } from "lucide-react";

import { cn } from "../../utils/utils";
import type { Task } from "../../models/task";

interface TaskListItemProps {
  task: Task;
  isSelected: boolean;
  onSelect: (task: Task) => void;
  onStopTask: (taskId: number) => void;
  onDeleteTask: (taskId: number) => void;
}

const getStatusIcon = (status: Task["status"]) => {
  switch (status) {
    case "COMPLETED":
      return <CheckCircle2 className="w-5 h-5 text-green-400" />;
    case "FAILED":
      return <XCircle className="w-5 h-5 text-red-400" />;
    default:
      return <Clock className="w-5 h-5 text-yellow-400 animate-pulse" />;
  }
};

export const TaskListItem: React.FC<TaskListItemProps> = ({
  task,
  isSelected,
  onSelect,
  onStopTask,
  onDeleteTask,
}) => {
  return (
    <div
      onClick={() => onSelect(task)}
      className={cn(
        "p-3 rounded-lg cursor-pointer transition-all hover:bg-gray-50 border flex items-center justify-between group",
        isSelected
          ? "bg-blue-50 border-blue-300"
          : "bg-white border-transparent hover:border-gray-200",
      )}
    >
      <div className="flex items-center gap-3 overflow-hidden">
        <div className="p-2 rounded-lg bg-gray-100">
          <ImageIcon className="w-5 h-5 text-gray-500" />
        </div>
        <div className="min-w-0">
          <p className="font-medium text-gray-800 truncate">{task.filename}</p>
          <p className="text-xs text-gray-400">
            {new Date(task.created_at).toLocaleTimeString()}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {(task.status === "PROCESSING" || task.status === "PENDING") && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onStopTask(task.id);
            }}
            className="p-1 hover:bg-red-500/20 rounded text-red-500 transition-colors opacity-0 group-hover:opacity-100"
            title="停止任务"
          >
            <XCircle className="w-4 h-4" />
          </button>
        )}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDeleteTask(task.id);
          }}
          className="p-1 hover:bg-red-500/20 rounded text-gray-500 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
          title="删除任务"
        >
          <Trash2 className="w-4 h-4" />
        </button>
        {getStatusIcon(task.status)}
      </div>
    </div>
  );
};
