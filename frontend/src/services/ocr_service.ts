import { httpClient } from "../providers/http_provider";
import type { Task } from "../models/task";

export type OcrModelModeOption = {
  id: "official" | "custom";
  use_local_models: boolean;
  label: string;
  description: string;
  available?: boolean;
};

export type OcrModelOptions = {
  provider: string;
  default_use_local_models: boolean;
  local_models_available: boolean;
  modes: OcrModelModeOption[];
};

export const MODEL_MODE_STORAGE_KEY = "ocr_model_mode";

export function loadStoredModelMode(): "official" | "custom" {
  const stored = localStorage.getItem(MODEL_MODE_STORAGE_KEY);
  if (stored === "official" || stored === "custom") {
    return stored;
  }
  return "official";
}

export function saveStoredModelMode(mode: "official" | "custom") {
  localStorage.setItem(MODEL_MODE_STORAGE_KEY, mode);
}

export const OCRService = {
    async getModelOptions(): Promise<OcrModelOptions> {
        const response = await httpClient.get<OcrModelOptions>("/ocr/model-options");
        return response.data;
    },

    async uploadTask(
        file: File,
        options?: {
            onProgress?: (percent: number) => void;
            useLocalModels?: boolean;
        },
    ): Promise<Task> {
        const formData = new FormData();
        formData.append('file', file);

        const response = await httpClient.post<Task>('/ocr/task', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            params:
                options?.useLocalModels === undefined
                    ? undefined
                    : { use_local_models: options.useLocalModels },
            onUploadProgress: (progressEvent) => {
                if (options?.onProgress) {
                    const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 100));
                    options.onProgress(percentCompleted);
                }
            }
        });
        return response.data;
    },

    async listTasks(): Promise<Task[]> {
        const response = await httpClient.get<Task[]>('/ocr/tasks');
        return response.data;
    },

    async listHistory(params?: { keyword?: string; days?: number; skip?: number; limit?: number }): Promise<Task[]> {
        const response = await httpClient.get<Task[]>('/ocr/history', { params });
        return response.data;
    },

    async getDashboardAnalytics(days = 7): Promise<{
      trend: Array<{ date: string; avg_inference_ms: number }>;
      confidence_distribution: { gt90: number; '70to90': number; lt70: number; unknown: number };
      failure_ratio: number;
      total_tasks: number;
      failed_tasks: number;
    }> {
      const response = await httpClient.get('/ocr/analytics/dashboard', { params: { days } });
      return response.data;
    },

    async getTask(taskId: number): Promise<Task> {
        const response = await httpClient.get<Task>(`/ocr/task/${taskId}`);
        return response.data;
    },

    async getTaskStatus(taskId: number): Promise<{
        task_id: number;
        status: Task["status"];
        celery_task_id?: string | null;
        celery_state?: string | null;
    }> {
        const response = await httpClient.get(`/ocr/task/${taskId}/status`);
        return response.data;
    },

    async stopTask(taskId: number): Promise<void> {
        await httpClient.post(`/ocr/task/${taskId}/stop`);
    },

    async saveCorrection(
      taskId: number,
      corrections: Array<{ index: number; original: string; corrected: string }>
    ): Promise<Task> {
      const response = await httpClient.post<Task>(`/ocr/task/${taskId}/correction`, { corrections });
      return response.data;
    },

    async deleteTask(taskId: number): Promise<void> {
        await httpClient.delete(`/ocr/task/${taskId}`);
    }
};
