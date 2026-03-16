/**
 * api.ts — FastAPI 백엔드와 통신하는 fetch 래퍼
 * 일반 API: Next.js rewrites 프록시 (/api/* → http://localhost:8000/api/*)
 * SSE 스트리밍: 백엔드 직접 연결 (Next.js 프록시가 SSE를 버퍼링하므로)
 */

const BACKEND_DIRECT = typeof window !== "undefined"
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : "http://localhost:8000";

// ── 타입 정의 ────────────────────────────────────────────────────────────────

export type LabelType = "AI 수행 가능" | "AI + Human" | "인간 수행 필요" | "미분류";
export type ProviderType = "openai" | "anthropic";

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
  provider: ProviderType;
  criterion: string;
  stage1: StageAnalysis;
  stage2: StageAnalysis;
  stage3: StageAnalysis;
  hybrid_check: boolean;
  hybrid_note: string;
  input_types: string;
  output_types: string;
  reason: string;
  manually_edited: boolean;
}

export interface ClassifierSettings {
  criteria_prompt: string;
  api_key: string;
  model: string;
  anthropic_api_key: string;
  anthropic_model: string;
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
  hybrid_count: number;
  human_count: number;
  unclassified_count: number;
  ai_ratio: number;
  hybrid_ratio: number;
  human_ratio: number;
  by_l3: Array<{ l3: string; total: number; ai: number; hybrid: number; human: number }>;
}

export interface FilterOptions {
  l2: Array<{ id: string; name: string }>;
  l3: Array<{ id: string; name: string }>;
  l4: Array<{ id: string; name: string }>;
}

export interface ClassifyRequest {
  task_ids?: string[] | null;
  settings?: ClassifierSettings | null;
  provider?: ProviderType;
}

export interface ComparisonItem {
  task_id: string;
  openai_label: LabelType | null;
  openai_reason: string | null;
  anthropic_label: LabelType | null;
  anthropic_reason: string | null;
  match: boolean | null;
}

export interface ComparisonResponse {
  total: number;
  both_classified: number;
  matching: number;
  match_rate: number;
  comparison: ComparisonItem[];
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
  provider?: ProviderType;
  page?: number;
  page_size?: number;
} = {}): Promise<ResultsResponse> {
  const qs = new URLSearchParams();
  if (params.label)     qs.set("label", params.label);
  if (params.provider)  qs.set("provider", params.provider);
  if (params.page)      qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch<ResultsResponse>(`/results${query}`);
}

export async function getStats(provider: ProviderType = "openai"): Promise<StatsResponse> {
  return apiFetch<StatsResponse>(`/results/stats?provider=${provider}`);
}

export async function getComparisonResults(params: {
  page?: number;
  page_size?: number;
} = {}): Promise<ComparisonResponse> {
  const qs = new URLSearchParams();
  if (params.page)      qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch<ComparisonResponse>(`/results/compare${query}`);
}

export async function updateResult(
  taskId: string,
  update: { label: LabelType; reason?: string },
  provider: ProviderType = "openai"
): Promise<ClassificationResult> {
  return apiFetch<ClassificationResult>(
    `/results/${encodeURIComponent(taskId)}?provider=${provider}`,
    { method: "PUT", body: JSON.stringify(update) }
  );
}

export async function deleteAllResults(
  provider: "openai" | "anthropic" | "all" = "openai"
): Promise<void> {
  await apiFetch(`/results?provider=${provider}`, { method: "DELETE" });
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

export function downloadExport(provider: ProviderType = "openai"): void {
  window.location.href = `/api/export?provider=${provider}`;
}

export function downloadCompareExport(): void {
  window.location.href = "/api/export/compare";
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

export async function healthCheck(): Promise<{
  status: string;
  task_count: number;
  api_key_configured: boolean;
  openai_configured: boolean;
  anthropic_configured: boolean;
}> {
  return apiFetch("/health");
}

// ── 사용량 ───────────────────────────────────────────────────────────────────

export interface ProviderUsage {
  total_calls: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  last_used: string | null;
  price_per_1m_input: number;
  price_per_1m_output: number;
}

export interface UsageStats {
  openai: ProviderUsage;
  anthropic: ProviderUsage;
}

export async function getUsage(): Promise<UsageStats> {
  return apiFetch("/usage");
}

export async function resetUsage(provider: "all" | "openai" | "anthropic" = "all"): Promise<void> {
  await apiFetch(`/usage?provider=${provider}`, { method: "DELETE" });
}

// ── Workflow API ──────────────────────────────────────────────────────────────

export interface WorkflowStepTask {
  task_id: string;
  label: string;
  level: string;
  node_id?: string;
}

export interface WorkflowStep {
  step: number;
  type: "순차" | "병렬";
  tasks: WorkflowStepTask[];
  is_parallel?: boolean;
  nodes?: WorkflowStepTask[];
}

export interface WorkflowSheetSummary {
  sheet_id: string;
  sheet_name: string;
  lanes: string[];
  l4_count: number;
  l5_count: number;
  total_steps: number;
  parallel_steps: number;
  sequential_steps: number;
  execution_order: WorkflowStep[];
  l4_details: Array<{
    node_id: string;
    task_id: string;
    label: string;
    description: string;
    child_l5_count: number;
    child_l5s: WorkflowStepTask[];
  }>;
}

export interface WorkflowSummary {
  version: string;
  sheet_count: number;
  sheets: WorkflowSheetSummary[];
}

export async function uploadWorkflow(file: File): Promise<WorkflowSummary & { ok: boolean; filename: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch("/api/workflow/upload", {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getWorkflowSummary(): Promise<WorkflowSummary> {
  return apiFetch<WorkflowSummary>("/workflow/summary");
}

export async function getWorkflowSheets(): Promise<{ sheets: WorkflowSheetSummary[] }> {
  return apiFetch("/workflow/sheets");
}

export async function getWorkflowExecutionOrder(sheetId: string): Promise<{
  sheet_id: string;
  sheet_name: string;
  total_steps: number;
  parallel_count: number;
  sequential_count: number;
  steps: WorkflowStep[];
}> {
  return apiFetch(`/workflow/execution-order/${encodeURIComponent(sheetId)}`);
}

// PPT 업로드
export async function uploadPptWorkflow(file: File): Promise<{
  ok: boolean;
  filename: string;
  slide_count: number;
  slides: Array<{
    slide_index: number;
    title: string;
    node_count: number;
    edge_count: number;
    matches: Array<{
      node_id: string;
      node_text: string;
      matched_task_id: string | null;
      matched_task_name: string | null;
      match_confidence: number;
    }>;
  }>;
}> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch("/api/workflow/upload-ppt", {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// To-Be 생성
export interface ToBeResult {
  ok: boolean;
  summary: {
    process_name: string;
    total_tasks: number;
    ai_tasks: number;
    hybrid_tasks: number;
    human_tasks: number;
    automation_rate: number;
    junior_agent_count: number;
    junior_agents: Array<{
      id: string;
      name: string;
      technique: string;
      task_count: number;
      tasks: Array<{ task_id: string; label: string }>;
    }>;
    human_step_count: number;
    human_steps: Array<{
      id: string;
      label: string;
      is_hybrid_part: boolean;
      reason: string;
    }>;
    senior_agent: { id: string; name: string; description: string };
  };
  execution_steps: Array<{
    step: number;
    is_parallel: boolean;
    actors: Array<{
      type: "junior_ai" | "human";
      agent_id?: string;
      agent_name?: string;
      technique?: string;
      label?: string;
      tasks?: Array<{ task_id: string; label: string }>;
    }>;
  }>;
  react_flow: { nodes: unknown[]; edges: unknown[]; lanes: string[] };
}

export async function generateToBe(params: {
  sheet_id?: string;
  provider?: ProviderType;
  process_name?: string;
} = {}): Promise<ToBeResult> {
  const qs = new URLSearchParams();
  if (params.sheet_id)     qs.set("sheet_id", params.sheet_id);
  if (params.provider)     qs.set("provider", params.provider);
  if (params.process_name) qs.set("process_name", params.process_name);
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch(`/workflow/generate-tobe${query}`, { method: "POST" });
}
