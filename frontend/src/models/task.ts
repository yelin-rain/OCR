export interface Task {
    id: number;
    filename: string;
    status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
    created_at: string;
    result: string | null;
    correction_log?: string | null;
    model_version?: string | null;
    inference_ms?: number | null;
    avg_confidence?: number | null;
    image_width?: number | null;
    image_height?: number | null;
    file_url?: string;
    celery_task_id?: string;
    /** 拼接后的 CRNN 原始文本（仅 strip） */
    original_text?: string | null;
    /** 后处理后的文本 */
    processed_text?: string | null;
}
