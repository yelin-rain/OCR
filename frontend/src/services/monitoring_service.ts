import { httpClient } from "../providers/http_provider";

export interface MonitoringSummary {
  errors_last_24h: number;
  warnings_last_24h: number;
  total_logs_last_24h: number;
  last_backup_at: string | null;
  last_backup_ok: boolean | null;
  backup_dir: string;
  app_log_file: string;
}

export interface SystemLogEntry {
  id: number;
  level: string;
  source: string;
  message: string;
  detail: string | null;
  path: string | null;
  user_id: number | null;
  created_at: string;
}

export interface BackupRecordEntry {
  id: number;
  filename: string;
  file_path: string;
  size_bytes: number;
  success: boolean;
  error_message: string | null;
  created_at: string;
}

export interface BackupTriggerResponse {
  success: boolean;
  message: string;
  record: BackupRecordEntry | null;
}

export const MonitoringService = {
  async getSummary(): Promise<MonitoringSummary> {
    const response = await httpClient.get<MonitoringSummary>("/monitoring/summary");
    return response.data;
  },

  async listLogs(params?: { limit?: number; level?: string }): Promise<SystemLogEntry[]> {
    const response = await httpClient.get<SystemLogEntry[]>("/monitoring/logs", {
      params,
    });
    return response.data;
  },

  async triggerBackup(): Promise<BackupTriggerResponse> {
    const response = await httpClient.post<BackupTriggerResponse>("/monitoring/backup");
    return response.data;
  },
};
