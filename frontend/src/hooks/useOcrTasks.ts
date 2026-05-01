import { useCallback, useEffect, useRef, useState } from "react";

import { OCRService } from "../services/ocr_service";
import type { Task } from "../models/task";

export function useOcrTasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const refreshTimerRef = useRef<number | null>(null);

  const clearTimer = useCallback(() => {
    if (refreshTimerRef.current !== null) {
      window.clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }
  }, []);

  const fetchTasks = useCallback(async () => {
    try {
      const data = await OCRService.listTasks();
      setTasks(data);

      const hasPending = data.some((t) =>
        ["PENDING", "PROCESSING"].includes(t.status),
      );
      if (hasPending) {
        clearTimer();
        refreshTimerRef.current = window.setTimeout(fetchTasks, 2000);
      } else {
        clearTimer();
      }
    } catch (error) {
      console.error("Failed to fetch tasks", error);
    }
  }, [clearTimer]);

  useEffect(() => {
    fetchTasks();
    return clearTimer;
  }, [fetchTasks, clearTimer]);

  return {
    tasks,
    setTasks,
    refreshTasks: fetchTasks,
  };
}
