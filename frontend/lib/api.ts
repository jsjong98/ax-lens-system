/**
 * api.ts — FastAPI 백엔드와 통신하는 fetch 래퍼
 * 일반 API: Next.js rewrites 프록시 (/api/* → Backend)
 * SSE 스트리밍: 백엔드 직접 연결 (Next.js 프록시가 SSE를 버퍼링하므로)
 *
 * Railway 배포 시 NEXT_PUBLIC_BACKEND_URL 환경변수로 백엔드 주소를 지정합니다.
 * 로컬 개발 시에는 기존처럼 같은 호스트의 :8000 포트를 사용합니다.
 */

// NEXT_PUBLIC_BACKEND_URL이 설정되면 (Railway 배포) 해당 URL 사용
// 설정되지 않으면 (로컬 개발) 빈 문자열 → 상대경로로 Next.js rewrites 프록시 사용
const BACKEND_DIRECT = process.env.NEXT_PUBLIC_BACKEND_URL || "";

// ── 타입 정의 ────────────────────────────────────────────────────────────────

export type LabelType = "AI" | "AI + Human" | "Human" | "미분류";
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

// ── 인증 토큰 관리 ──────────────────────────────────────────────────────────

function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("auth_token");
}

function setAuthToken(token: string): void {
  if (typeof window !== "undefined") localStorage.setItem("auth_token", token);
}

function clearAuthToken(): void {
  if (typeof window !== "undefined") localStorage.removeItem("auth_token");
}

// ── 기본 fetch 헬퍼 ──────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const res = await fetch(`${BACKEND_DIRECT}/api${path}`, {
    headers,
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

// ── Auth API ────────────────────────────────────────────────────────────────

export interface AuthUser {
  email: string;
  name: string;
  must_change_password: boolean;
}

export async function login(email: string, password: string): Promise<{ token: string; user: AuthUser }> {
  const res = await fetch(`${BACKEND_DIRECT}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "로그인 실패" }));
    throw new Error(err.detail || "로그인 실패");
  }
  const data = await res.json();
  setAuthToken(data.token);
  return data;
}

export async function getMe(): Promise<AuthUser | null> {
  const token = getAuthToken();
  if (!token) return null;
  try {
    const res = await fetch(`${BACKEND_DIRECT}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.user;
  } catch {
    return null;
  }
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  await apiFetch("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  });
}

export async function apiLogout(): Promise<void> {
  try {
    await apiFetch("/auth/logout", { method: "POST" });
  } catch {}
  clearAuthToken();
}

// ── 비밀번호 재설정 API ────────────────────────────────────────────────────

export async function requestResetCode(email: string): Promise<string> {
  const res = await fetch(`${BACKEND_DIRECT}/api/auth/reset/request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "요청 실패");
  return data.message;
}

export async function verifyResetCode(email: string, code: string): Promise<void> {
  const res = await fetch(`${BACKEND_DIRECT}/api/auth/reset/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: "인증 실패" }));
    throw new Error(data.detail || "인증 실패");
  }
}

export async function confirmResetPassword(email: string, code: string, newPassword: string): Promise<void> {
  const res = await fetch(`${BACKEND_DIRECT}/api/auth/reset/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code, new_password: newPassword }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: "재설정 실패" }));
    throw new Error(data.detail || "재설정 실패");
  }
}

// ── Project History API ──────────────────────────────────────────────────────

export interface ProjectInfo {
  filename: string;
  dirname: string;
  created_at?: string;
  last_accessed?: string;
  task_count?: number;
  source?: string;
  saved_data: Record<string, boolean>;
  has_any_result: boolean;
}

export async function getProjectList(): Promise<{ ok: boolean; projects: ProjectInfo[] }> {
  return apiFetch("/projects");
}

export async function loadProject(filename: string): Promise<{
  ok: boolean;
  filename: string;
  loaded: Record<string, boolean>;
  saved: Record<string, boolean>;
}> {
  return apiFetch("/projects/load", {
    method: "POST",
    body: JSON.stringify({ filename }),
  });
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

export interface ExcelSheet {
  name: string;
  task_count: number;
  is_guide: boolean;
  recommended: boolean;
}

export async function getExcelSheets(): Promise<{ filename: string; sheets: ExcelSheet[] }> {
  return apiFetch("/upload/sheets");
}

export async function selectExcelSheet(
  sheetName: string,
): Promise<{ message: string; sheet_name: string; task_count: number }> {
  return apiFetch("/upload/select-sheet", {
    method: "POST",
    body: JSON.stringify({ sheet_name: sheetName }),
  });
}

export async function uploadExcel(
  file: File,
  onProgress?: (pct: number) => void
): Promise<{ message: string; filename: string; task_count: number; sheets?: ExcelSheet[] }> {
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
    xhr.open("POST", `${BACKEND_DIRECT}/api/upload`);
    const authToken = getAuthToken();
    if (authToken) xhr.setRequestHeader("Authorization", `Bearer ${authToken}`);
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
export interface ToBeInputSource {
  id: string;
  name: string;
  source_type: string;
  description?: string;
  related_task_ids?: string[];
}

export interface ToBeResult {
  ok: boolean;
  summary: {
    process_name: string;
    total_tasks: number;
    ai_tasks: number;
    hybrid_tasks: number;
    human_tasks: number;
    automation_rate: number;
    input_source_count: number;
    input_sources: ToBeInputSource[];
    junior_agent_count: number;
    junior_agents: Array<{
      id: string;
      name: string;
      technique: string;
      ai_tech_category: string;
      ai_tech_type: string;
      task_count: number;
      description?: string;
      senior_instruction?: string;
      input_sources: Array<{ id: string; name: string; source_type: string }>;
      tasks: Array<{
        task_id: string;
        label: string;
        technique?: string;
        ai_tech_category?: string;
        ai_tech_type?: string;
      }>;
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
      ai_tech_category?: string;
      ai_tech_type?: string;
      label?: string;
      input_sources?: Array<{ id: string; name: string; source_type: string }>;
      tasks?: Array<{
        task_id: string;
        label: string;
        technique?: string;
        ai_tech_category?: string;
        ai_tech_type?: string;
      }>;
    }>;
  }>;
  react_flow: { nodes: unknown[]; edges: unknown[]; lanes: string[] };
}

export async function saveSlideL4Mapping(
  mappings: Record<string, string>,
): Promise<{ ok: boolean; mappings: Record<string, string> }> {
  return apiFetch("/workflow/slide-l4-mapping", {
    method: "POST",
    body: JSON.stringify({ mappings }),
  });
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

// ── New Workflow ──────────────────────────────────────────────────────────────

export interface ExcelSheet {
  name: string;
  recommended: boolean;
  row_count: number;
  l5_count: number;
}

export async function uploadNewWorkflowExcel(file: File): Promise<{
  message: string;
  filename: string;
  task_count: number;
  sheets: ExcelSheet[];
}> {
  const formData = new FormData();
  formData.append("file", file);
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${BACKEND_DIRECT}/api/new-workflow/upload`, {
    method: "POST",
    headers,
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "업로드 실패" }));
    throw new Error(err.detail || "업로드 실패");
  }
  return res.json();
}

export async function selectNewWorkflowSheet(sheetName: string): Promise<{
  message: string;
  sheet_name: string;
  task_count: number;
}> {
  return apiFetch("/new-workflow/select-sheet", {
    method: "POST",
    body: JSON.stringify({ sheet_name: sheetName }),
  });
}

export async function getNewWorkflowTasks(): Promise<{
  total: number;
  tasks: Array<{
    id: string; l2: string; l3: string; l3_id: string;
    l4: string; l4_id: string; name: string;
    description: string; performer: string;
  }>;
}> {
  return apiFetch("/new-workflow/tasks");
}

export async function getNewWorkflowFilters(): Promise<{
  l3_options: Array<{ id: string; name: string }>;
}> {
  return apiFetch("/new-workflow/filters");
}

export interface NewWorkflowAssignedTask {
  task_id: string;
  task_name: string;
  l4: string;
  l3: string;
  ai_role: string;
  human_role: string;
  input_data: string[];
  output_data: string[];
  automation_level: "Human-on-the-Loop" | "Human-in-the-Loop" | "Human-Supervised";
}

export interface NewWorkflowAgent {
  agent_id: string;
  agent_name: string;
  agent_type: string;
  ai_technique: string;
  description: string;
  automation_level: "Human-on-the-Loop" | "Human-in-the-Loop" | "Human-Supervised";
  task_count: number;
  assigned_tasks: NewWorkflowAssignedTask[];
}

export interface NewWorkflowExecutionStep {
  step: number;
  step_name: string;
  step_type: "sequential" | "parallel";
  description: string;
  agent_ids: string[];
  task_ids: string[];
}

export interface NewWorkflowResult {
  ok: boolean;
  blueprint_summary: string;
  process_name: string;
  total_tasks: number;
  full_auto_count: number;
  human_in_loop_count: number;
  human_supervised_count: number;
  agents: NewWorkflowAgent[];
  execution_flow: NewWorkflowExecutionStep[];
}

export async function generateNewWorkflow(params: {
  process_name?: string;
  project_index?: string;
  l3?: string;
  l4?: string;
} = {}): Promise<NewWorkflowResult> {
  const qs = new URLSearchParams();
  if (params.process_name)  qs.set("process_name", params.process_name);
  if (params.project_index) qs.set("project_index", params.project_index);
  if (params.l3)            qs.set("l3", params.l3);
  if (params.l4)            qs.set("l4", params.l4);
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch(`/new-workflow/generate${query}`, { method: "POST" });
}

export async function generateNewWorkflowFreeform(params: {
  process_name: string;
  inputs?: string;
  outputs?: string;
  systems?: string;
  pain_points?: string;
  additional_info?: string;
}): Promise<NewWorkflowResult> {
  return apiFetch("/new-workflow/generate-freeform", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export interface BenchmarkInsight {
  source: string;
  insight: string;
  application: string;
  url?: string;
}

export interface BenchmarkResult extends NewWorkflowResult {
  benchmark_insights: BenchmarkInsight[];
  improvement_summary: string;
  search_count: number;
}

export async function benchmarkNewWorkflow(): Promise<BenchmarkResult> {
  return apiFetch("/new-workflow/benchmark", { method: "POST" });
}

export async function getNewWorkflowResult(): Promise<NewWorkflowResult> {
  return apiFetch("/new-workflow/result");
}

export async function saveEditedWorkflow(data: Record<string, unknown>): Promise<{ ok: boolean }> {
  return apiFetch("/new-workflow/result", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function clearNewWorkflowResult(): Promise<{ ok: boolean }> {
  return apiFetch("/new-workflow/result", { method: "DELETE" });
}

export async function downloadNewWorkflowAsHtml(): Promise<void> {
  const token = getAuthToken();
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${BACKEND_DIRECT}/api/new-workflow/export-html`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "HTML 다운로드 실패" }));
    throw new Error(err.detail ?? "HTML 다운로드 실패");
  }
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] ?? "AI_Service_Flow.html";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = decodeURIComponent(filename);
  a.click();
  URL.revokeObjectURL(url);
}

export async function downloadNewWorkflowAsHrJson(): Promise<void> {
  const token = getAuthToken();
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${BACKEND_DIRECT}/api/new-workflow/export-hr-json`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "다운로드 실패" }));
    throw new Error(err.detail ?? "다운로드 실패");
  }
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] ?? "new_workflow.json";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Project Management API ─────────────────────────────────────────────────

export interface MappingProcess {
  no: string;
  process_name: string;
  task_range: string;
}

export interface Stakeholder {
  project_owner: string;
  owner_department: string;
  collaborating_departments: string[];
  external_partners: string[];
}

export interface CurrentVsImprovement {
  current_issues: string[];
  improvement_directions: string[];
}

export interface ExpectedEffects {
  quantitative: string[];
  qualitative: string[];
}

export interface ProjectDefinitionResult {
  ok: boolean;
  project_number: string;
  project_title: string;
  created_date: string;
  author: string;
  overview: string[];
  mapping_processes: MappingProcess[];
  stakeholder: Stakeholder;
  current_vs_improvement: CurrentVsImprovement;
  expected_effects: ExpectedEffects;
  considerations: string[];
}

export async function generateProjectDefinition(params: {
  provider?: ProviderType;
  source?: string;
  process_name?: string;
  author?: string;
  l3?: string;
  l4?: string;
} = {}): Promise<ProjectDefinitionResult> {
  const qs = new URLSearchParams();
  if (params.provider)     qs.set("provider", params.provider);
  if (params.source)       qs.set("source", params.source);
  if (params.process_name) qs.set("process_name", params.process_name);
  if (params.author)       qs.set("author", params.author);
  if (params.l3)           qs.set("l3", params.l3);
  if (params.l4)           qs.set("l4", params.l4);
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch(`/project-management/definition/generate${query}`, { method: "POST" });
}

export async function getProjectDefinition(): Promise<ProjectDefinitionResult> {
  return apiFetch("/project-management/definition");
}

export async function clearProjectDefinition(): Promise<{ ok: boolean }> {
  return apiFetch("/project-management/definition", { method: "DELETE" });
}

// ── 과제 설계서 API ────────────────────────────────────────────────────────

export interface AIServiceFlowStep {
  step_order: number;
  step_name: string;
  actor: "Input" | "Senior AI" | "Junior AI" | "HR 담당자";
  description: string;
  sub_steps: string[];
}

export interface AIServiceFlow {
  inputs: string[];
  steps: AIServiceFlowStep[];
}

export interface AITechType {
  category: string;
  sub_types: string[];
  checked: string[];
}

export interface AITechInfo {
  tech_types: AITechType[];
  tech_names: string[];
}

export interface InputOutputInfo {
  input_internal: string[];
  input_external: string[];
  output: string[];
}

export interface ProcessingStep {
  step_number: number;
  step_name: string;
  method: string;
  result: string;
}

export interface AgentDefinition {
  agent_id: string;
  agent_name: string;
  agent_type: string;
  roles: string[];
  input_data: string[];
  processing_steps: ProcessingStep[];
  output_data: string[];
  flow_step_orders: number[];
}

export interface ProjectDesignResult {
  ok: boolean;
  project_title: string;
  ai_service_flow: AIServiceFlow;
  ai_tech_info: AITechInfo;
  input_output: InputOutputInfo;
  agent_definitions: AgentDefinition[];
}

export async function generateProjectDesign(params: {
  provider?: ProviderType;
  source?: string;
  process_name?: string;
  l3?: string;
  l4?: string;
} = {}): Promise<ProjectDesignResult> {
  const qs = new URLSearchParams();
  if (params.provider)     qs.set("provider", params.provider);
  if (params.source)       qs.set("source", params.source);
  if (params.process_name) qs.set("process_name", params.process_name);
  if (params.l3)           qs.set("l3", params.l3);
  if (params.l4)           qs.set("l4", params.l4);
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch(`/project-management/design/generate${query}`, { method: "POST" });
}

export async function getProjectDesign(): Promise<ProjectDesignResult> {
  return apiFetch("/project-management/design");
}

export async function clearProjectDesign(): Promise<{ ok: boolean }> {
  return apiFetch("/project-management/design", { method: "DELETE" });
}

export async function downloadProjectPpt(): Promise<void> {
  const token = getAuthToken();
  const hdrs: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${BACKEND_DIRECT}/api/project-management/export-ppt`, { headers: hdrs });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "PPT 다운로드 실패" }));
    throw new Error(err.detail ?? "PPT 다운로드 실패");
  }
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] ?? "과제정의서.pptx";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = decodeURIComponent(filename);
  a.click();
  URL.revokeObjectURL(url);
}
