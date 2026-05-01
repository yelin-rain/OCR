import { httpClient } from "../providers/http_provider";
import type { Task } from "../models/task";

export const OCRService = {
    async uploadTask(file: File, onProgress?: (percent: number) => void): Promise<Task> {
        const formData = new FormData();
        formData.append('file', file);

        const response = await httpClient.post<Task>('/ocr/task', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            onUploadProgress: (progressEvent) => {
                if (onProgress) {
                    const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 100));
                    onProgress(percentCompleted);
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
