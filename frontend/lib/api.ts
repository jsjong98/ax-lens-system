/**
 * api.ts — FastAPI 백엔드와 통신하는 fetch 래퍼
 * 일반 API: Next.js rewrites 프록시 (/api/* → http://localhost:8000/api/*)
 * SSE 스트리밍: 백엔드 직접 연결 (Next.js 프록시가 SSE를 버퍼링하므로)
 */

// SSE 스트리밍은 백엔드에 직접 연결 (프록시 버퍼링 우회)
const BACKEND_DIRECT = typeof window !== "undefined"
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : "http://localhost:8000";

// ── 타입 정의 ────────────────────────────────────────────────────────────────

export type LabelType = "AI 수행 가능" | "인간 수행 필요" | "미분류";

export interface Task {
  id: string;
  l2_id: string;
  l2: string;
  l3_id: string;
  l3: string;
  l4_id: string;
  l4: string;
  name: string;
  description: string;
  performer: string;
}

export interface StageAnalysis {
  passed: boolean;
  note: string;
}

export interface ClassificationResult {
  task_id: string;
  label: LabelType;
  criterion: string;
  stage1: StageAnalysis;
  stage2: StageAnalysis;
  stage3: StageAnalysis;
  input_types: string;
  output_types: string;
  reason: string;
  confidence: number;
  manually_edited: boolean;
}

export interface ClassifierSettings {
  criteria_prompt: string;
  api_key: string;
  model: string;
  batch_size: number;
  temperature: number;
}

export interface TaskListResponse {
  total: number;
  tasks: Task[];
}

export interface ResultsResponse {
  total: number;
  classified: number;
  unclassified: number;
  results: ClassificationResult[];
}

export interface StatsResponse {
  total: number;
  ai_count: number;
  human_count: number;
  unclassified_count: number;
  ai_ratio: number;
  human_ratio: number;
  by_l3: Array<{ l3: string; total: number; ai: number; human: number }>;
}

export interface FilterOptions {
  l2: Array<{ id: string; name: string }>;
  l3: Array<{ id: string; name: string }>;
  l4: Array<{ id: string; name: string }>;
}

export interface ClassifyRequest {
  task_ids?: string[] | null;
  settings?: ClassifierSettings | null;
}

// SSE 이벤트 타입
export type SSEEvent =
  | { type: "progress"; task_id: string; current: number; total: number; result: ClassificationResult }
  | { type: "done"; total: number }
  | { type: "error"; message: string };

// ── 기본 fetch 헬퍼 ──────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    let errorMsg = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      errorMsg = err.detail || errorMsg;
    } catch {}
    throw new Error(errorMsg);
  }

  return res.json() as Promise<T>;
}

// ── Task API ─────────────────────────────────────────────────────────────────

export interface TaskListParams {
  search?: string;
  l2?: string;
  l3?: string;
  l4?: string;
  page?: number;
  page_size?: number;
}

export async function getTasks(params: TaskListParams = {}): Promise<TaskListResponse> {
  const qs = new URLSearchParams();
  if (params.search)    qs.set("search", params.search);
  if (params.l2)        qs.set("l2", params.l2);
  if (params.l3)        qs.set("l3", params.l3);
  if (params.l4)        qs.set("l4", params.l4);
  if (params.page)      qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch<TaskListResponse>(`/tasks${query}`);
}

export async function getFilterOptions(): Promise<FilterOptions> {
  return apiFetch<FilterOptions>("/tasks/filters");
}

export async function getTask(taskId: string): Promise<Task> {
  return apiFetch<Task>(`/tasks/${encodeURIComponent(taskId)}`);
}

// ── 분류 API (SSE) ───────────────────────────────────────────────────────────

export function classifyTasks(
  req: ClassifyRequest,
  onEvent: (event: SSEEvent) => void,
  onError?: (err: Error) => void
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      // SSE: Next.js 프록시 우회하여 백엔드 직접 연결
      const res = await fetch(`${BACKEND_DIRECT}/api/classify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
        signal: controller.signal,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const event = JSON.parse(line.slice(6)) as SSEEvent;
              onEvent(event);
            } catch {}
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        onError?.(err as Error);
      }
    }
  })();

  return () => controller.abort();
}

// ── 결과 API ─────────────────────────────────────────────────────────────────

export async function getResults(params: {
  label?: string;
  page?: number;
  page_size?: number;
} = {}): Promise<ResultsResponse> {
  const qs = new URLSearchParams();
  if (params.label)     qs.set("label", params.label);
  if (params.page)      qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch<ResultsResponse>(`/results${query}`);
}

export async function getStats(): Promise<StatsResponse> {
  return apiFetch<StatsResponse>("/results/stats");
}

export async function updateResult(
  taskId: string,
  update: { label: LabelType; reason?: string }
): Promise<ClassificationResult> {
  return apiFetch<ClassificationResult>(`/results/${encodeURIComponent(taskId)}`, {
    method: "PUT",
    body: JSON.stringify(update),
  });
}

export async function deleteAllResults(): Promise<void> {
  await apiFetch("/results", { method: "DELETE" });
}

// ── 설정 API ─────────────────────────────────────────────────────────────────

export async function getSettings(): Promise<ClassifierSettings> {
  return apiFetch<ClassifierSettings>("/settings");
}

export async function saveSettings(settings: ClassifierSettings): Promise<ClassifierSettings> {
  return apiFetch<ClassifierSettings>("/settings", {
    method: "POST",
    body: JSON.stringify(settings),
  });
}

// ── 내보내기 ─────────────────────────────────────────────────────────────────

export function downloadExport(): void {
  window.location.href = "/api/export";
}

// ── 엑셀 업로드 ──────────────────────────────────────────────────────────────

export interface UploadCurrentInfo {
  filename: string | null;
  size_kb: number;
  task_count: number;
}

export async function getCurrentFile(): Promise<UploadCurrentInfo> {
  return apiFetch<UploadCurrentInfo>("/upload/current");
}

export async function uploadExcel(
  file: File,
  onProgress?: (pct: number) => void
): Promise<{ message: string; filename: string; task_count: number }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress?.(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          reject(new Error(JSON.parse(xhr.responseText).detail || `HTTP ${xhr.status}`));
        } catch {
          reject(new Error(`HTTP ${xhr.status}`));
        }
      }
    };
    xhr.onerror = () => reject(new Error("네트워크 오류"));
    xhr.open("POST", "/api/upload");
    xhr.send(formData);
  });
}

// ── 헬스체크 ─────────────────────────────────────────────────────────────────

export async function healthCheck(): Promise<{ status: string; task_count: number; api_key_configured: boolean }> {
  return apiFetch("/health");
}
