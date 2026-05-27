import React, { useEffect, useState } from "react";
import { FileUpload } from "../components/FileUpload";
import type { OcrModelMode } from "../components/ModelModeSwitch";
import { TaskList } from "../components/TaskList";
import {
  OCRService,
  loadStoredModelMode,
  saveStoredModelMode,
  MODEL_MODE_STORAGE_KEY,
} from "../services/ocr_service";
import type { Task } from "../models/task";
import { Modal, message } from "antd";
import { useOcrTasks } from "../hooks/useOcrTasks";

export const OCRController: React.FC = () => {
  const { tasks, refreshTasks } = useOcrTasks();
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [modelMode, setModelMode] = useState<OcrModelMode>(loadStoredModelMode);
  const [customAvailable, setCustomAvailable] = useState(true);

  useEffect(() => {
    OCRService.getModelOptions()
      .then((opts) => {
        setCustomAvailable(opts.local_models_available);
        const stored = localStorage.getItem(MODEL_MODE_STORAGE_KEY);
        if (!stored) {
          const mode: OcrModelMode =
            opts.default_use_local_models && opts.local_models_available
              ? "custom"
              : "official";
          setModelMode(mode);
          saveStoredModelMode(mode);
        } else if (!opts.local_models_available && stored === "custom") {
          setModelMode("official");
          saveStoredModelMode("official");
        }
      })
      .catch(() => {
        /* 离线时仍可用本地缓存的切换状态 */
      });
  }, []);

  // 轮询更新 tasks 后，同步当前选中任务（识别完成自动刷新详情区）
  useEffect(() => {
    setSelectedTask((prev) => {
      if (!prev) return prev;
      return tasks.find((t) => t.id === prev.id) ?? prev;
    });
  }, [tasks]);

  const handleModelModeChange = (mode: OcrModelMode) => {
    setModelMode(mode);
    saveStoredModelMode(mode);
  };

  const handleUpload = async (
    file: File,
    onProgress: (percent: number) => void,
  ) => {
    const useLocalModels = modelMode === "custom";
    const newTask = await OCRService.uploadTask(file, {
      onProgress,
      useLocalModels,
    });
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
    <div className="max-w-7xl mx-auto px-2 h-[calc(100vh-170px)] flex flex-col gap-4 overflow-hidden">
      <section className="shrink-0">
        <FileUpload
          onUpload={handleUpload}
          modelMode={modelMode}
          onModelModeChange={handleModelModeChange}
          customModelAvailable={customAvailable}
        />
      </section>

      <section className="flex-1 min-h-0">
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
