export interface Task {
    id: number;
    filename: string;
    status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
    created_at: string;
    result: string | null;
    file_url?: string;
    celery_task_id?: string;
}
