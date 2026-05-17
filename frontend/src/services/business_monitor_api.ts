import { httpClient } from "../providers/http_provider";

export interface MonitorStats {
  latency_24h: Array<{ hour: string; avg_inference_ms: number; count: number }>;
  low_confidence_task_ids: number[];
  pie: {
    success: number;
    failed: number;
    in_progress: number;
    total: number;
  };
}

export interface BadCaseItem {
  task_id: number;
  filename: string;
  status: string;
  avg_confidence: number | null;
  inference_ms: number | null;
  file_url: string | null;
  created_at: string;
  result_preview: string | null;
}

export async function fetchMonitorStats(): Promise<MonitorStats> {
  const res = await httpClient.get<MonitorStats>("/api/monitor/stats");
  return res.data;
}

export async function fetchBadCases(): Promise<{ items: BadCaseItem[] }> {
  const res = await httpClient.get<{ items: BadCaseItem[] }>("/api/monitor/bad-cases");
  return res.data;
}
