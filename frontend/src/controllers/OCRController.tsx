import React, { useState } from "react";
import { FileUpload } from "../components/FileUpload";
import { TaskList } from "../components/TaskList";
import { OCRService } from "../services/ocr_service";
import type { Task } from "../models/task";
import { Modal, message } from "antd";
import { useOcrTasks } from "../hooks/useOcrTasks";

export const OCRController: React.FC = () => {
  const { tasks, refreshTasks } = useOcrTasks();
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  const handleUpload = async (
    file: File,
    onProgress: (percent: number) => void,
  ) => {
    const newTask = await OCRService.uploadTask(file, onProgress);
    setSelectedTask(newTask);
    await refreshTasks();
  };

  const handleStopTask = async (taskId: number) => {
    Modal.confirm({
      title: "确定要停止该任务吗？",
      onOk: async () => {
        try {
          await OCRService.stopTask(taskId);
          message.success("任务已停止");
          await refreshTasks();
        } catch {
          message.error("停止任务失败");
        }
      },
    });
  };

  const handleDeleteTask = async (taskId: number) => {
    Modal.confirm({
      title: "确定要删除该任务吗？",
      okText: "确定",
      cancelText: "取消",
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await OCRService.deleteTask(taskId);
          if (selectedTask?.id === taskId) {
            setSelectedTask(null);
          }
          message.success("项目已删除");
          await refreshTasks();
        } catch {
          message.error("删除任务失败");
        }
      },
    });
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 space-y-10">
      <section>
        <FileUpload onUpload={handleUpload} />
      </section>

      <section>
        <TaskList
          tasks={tasks}
          selectedTask={selectedTask}
          onSelectTask={setSelectedTask}
          onStopTask={handleStopTask}
          onDeleteTask={handleDeleteTask}
        />
      </section>
    </div>
  );
};
