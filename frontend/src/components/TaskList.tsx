import React from "react";
import { FileText } from "lucide-react";
import type { Task } from "../models/task";
import { TaskListItem } from "./task/TaskListItem";
import { TaskDetailPanel } from "./task/TaskDetailPanel";

interface TaskListProps {
  tasks: Task[];
  selectedTask: Task | null;
  onSelectTask: (task: Task) => void;
  onStopTask: (taskId: number) => void;
  onDeleteTask: (taskId: number) => void;
}

export const TaskList: React.FC<TaskListProps> = ({
  tasks,
  selectedTask,
  onSelectTask,
  onStopTask,
  onDeleteTask,
}) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[600px]">
      {/* List */}
      <div className="col-span-1 bg-gray-900/50 rounded-xl border border-gray-700 overflow-hidden flex flex-col">
        <div className="p-4 border-b border-gray-700 bg-gray-900/80 backdrop-blur">
          <h2 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-400" />
            历史任务
          </h2>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-2">
          {tasks.map((task) => (
            <TaskListItem
              key={task.id}
              task={task}
              isSelected={selectedTask?.id === task.id}
              onSelect={onSelectTask}
              onStopTask={onStopTask}
              onDeleteTask={onDeleteTask}
            />
          ))}
        </div>
      </div>

      {/* Detail View */}
      <div className="col-span-1 lg:col-span-2 bg-gray-900/50 rounded-xl border border-gray-700 overflow-hidden flex flex-col">
        <TaskDetailPanel task={selectedTask} />
      </div>
    </div>
  );
};
