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

    async getTask(taskId: number): Promise<Task> {
        const response = await httpClient.get<Task>(`/ocr/task/${taskId}`);
        return response.data;
    },

    async stopTask(taskId: number): Promise<void> {
        await httpClient.post(`/ocr/task/${taskId}/stop`);
    },

    async deleteTask(taskId: number): Promise<void> {
        await httpClient.delete(`/ocr/task/${taskId}`);
    }
};
