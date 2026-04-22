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

/** 401 응답 시 토큰 삭제 + 로그인 페이지로 이동 */
function handle401(): void {
  clearAuthToken();
  if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
    window.location.href = "/login";
  }
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
    // 401: 세션 만료 또는 무효 → 토큰 삭제 후 로그인 페이지로 이동
    if (res.status === 401) {
      clearAuthToken();
      if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
        window.location.href = "/login";
      }
    }
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
  is_admin?: boolean;
  is_pm?: boolean;
  pm_project?: string | null;
  project?: string | null;
  projects?: string[];
}

export interface TransferRequest {
  id: string;
  email: string;
  name: string;
  current_project: string | null;
  target_project: string;
  reason: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
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

// ── 프로젝트 이동 요청 API ─────────────────────────────────────────────────

export async function requestProjectTransfer(targetProject: string, reason?: string): Promise<{ ok: boolean; request: TransferRequest }> {
  return apiFetch("/auth/transfer-request", {
    method: "POST",
    body: JSON.stringify({ target_project: targetProject, reason: reason || "" }),
  });
}

export async function getPendingTransfers(): Promise<{ ok: boolean; requests: TransferRequest[] }> {
  return apiFetch("/auth/pending-transfers");
}

export async function approveTransfer(requestId: string): Promise<{ ok: boolean; request: TransferRequest }> {
  return apiFetch("/auth/approve-transfer", {
    method: "POST",
    body: JSON.stringify({ request_id: requestId }),
  });
}

export async function rejectTransfer(requestId: string): Promise<{ ok: boolean; request: TransferRequest }> {
  return apiFetch("/auth/reject-transfer", {
    method: "POST",
    body: JSON.stringify({ request_id: requestId }),
  });
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
  agent_count?: number;
  agent_names?: string[];
  team_project?: string;
}

export async function getBenchmarkResult(): Promise<{
  ok: boolean;
  benchmark_insights: BenchmarkInsight[];
  improvement_summary: string;
  search_count: number;
}> {
  return apiFetch("/new-workflow/benchmark-result");
}

export async function getProjectList(): Promise<{ ok: boolean; projects: ProjectInfo[] }> {
  return apiFetch("/projects");
}

export async function loadProject(filename: string): Promise<{
  ok: boolean;
  filename: string;
  loaded: Record<string, boolean>;
  saved: Record<string, boolean>;
  benchmark?: { benchmark_insights: BenchmarkInsight[]; improvement_summary: string; search_count: number } | null;
}> {
  return apiFetch("/projects/load", {
    method: "POST",
    body: JSON.stringify({ filename }),
  });
}

export async function deleteProject(dirname: string): Promise<{ ok: boolean }> {
  return apiFetch(`/projects/${encodeURIComponent(dirname)}`, {
    method: "DELETE",
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
  const token = getAuthToken();
  const url = `${BACKEND_DIRECT}/api/export?provider=${provider}`;
  // 토큰이 있으면 fetch로 다운로드 (Authorization 헤더 포함), 없으면 직접 이동
  if (token) {
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (res) => {
        if (res.status === 401) { handle401(); return; }
        if (!res.ok) throw new Error("다운로드 실패");
        const blob = await res.blob();
        const cd = res.headers.get("content-disposition") || "";
        const fnMatch = cd.match(/filename\*?=(?:UTF-8'')?(.+)/i);
        const filename = fnMatch ? decodeURIComponent(fnMatch[1].replace(/"/g, "")) : `분류결과_${provider}.xlsx`;
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        a.click();
      })
      .catch((e) => alert(`다운로드 실패: ${e.message}`));
  } else {
    window.location.href = url;
  }
}

export function downloadCompareExport(): void {
  const token = getAuthToken();
  const url = `${BACKEND_DIRECT}/api/export/compare`;
  if (token) {
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (res) => {
        if (res.status === 401) { handle401(); return; }
        if (!res.ok) throw new Error("다운로드 실패");
        const blob = await res.blob();
        const cd = res.headers.get("content-disposition") || "";
        const fnMatch = cd.match(/filename\*?=(?:UTF-8'')?(.+)/i);
        const filename = fnMatch ? decodeURIComponent(fnMatch[1].replace(/"/g, "")) : "비교결과.xlsx";
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        a.click();
      })
      .catch((e) => alert(`다운로드 실패: ${e.message}`));
  } else {
    window.location.href = url;
  }
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
        if (xhr.status === 401) handle401();
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

export interface WorkflowBranch {
  type: "decision" | "edge";
  // decision type
  decision_node_id?: string;
  decision_label?: string;
  branches?: Array<{
    condition: string;
    target_node_id: string;
    target_label: string;
    target_level: string;
  }>;
  // edge type
  condition?: string;
  target_node_id?: string;
  target_label?: string;
  target_level?: string;
}

export interface WorkflowDecisionNode {
  node_id: string;
  label: string;
  description: string;
  incoming: Array<{ from_node_id: string; from_label: string; condition: string }>;
  outgoing: Array<{ condition: string; to_node_id: string; to_label: string }>;
}

export interface WorkflowSheetSummary {
  sheet_id: string;
  sheet_name: string;
  lanes: string[];
  l4_count: number;
  l5_count: number;
  decision_count?: number;
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
    child_l5s: Array<WorkflowStepTask & { cls_label?: string; cls_reason?: string }>;
    branches?: WorkflowBranch[];
  }>;
  decision_nodes?: WorkflowDecisionNode[];
}

export interface WorkflowSummary {
  version: string;
  sheet_count: number;
  sheets: WorkflowSheetSummary[];
}

export async function uploadWorkflow(file: File): Promise<WorkflowSummary & { ok: boolean; filename: string }> {
  const formData = new FormData();
  formData.append("file", file);
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

  const res = await fetch(`${BACKEND_DIRECT}/api/workflow/upload`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!res.ok) {
    if (res.status === 401) handle401();
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
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${BACKEND_DIRECT}/api/workflow/upload-ppt`, {
    method: "POST",
    headers,
    body: formData,
  });
  if (!res.ok) {
    if (res.status === 401) handle401();
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

// ── Workflow Excel Upload + Step 1/2 ─────────────────────────────────────────

export interface WorkflowExcelTask {
  id: string;
  l2: string;
  l3: string;
  l4: string;
  name: string;
  description: string;
  performer: string;
  label: string;
  reason: string;
  criterion: string;
  ai_prerequisites: string;
  feedback: string;
}

export interface WorkflowExcelUploadResult {
  ok: boolean;
  filename: string;
  task_count: number;
  has_classification: boolean;
  classified_count: number;
  sheets: Array<{ name: string; recommended: boolean; row_count: number; l5_count: number }>;
}

export interface RedesignedL5Task {
  task_id: string;
  task_name: string;
  change_type: string;
  ai_application: string;
  automation_level: string;
  ai_technique: string;
}

export interface RedesignedL4 {
  l4_id: string;
  l4_name: string;
  change_type: string;
  change_reason: string;
  l5_list: RedesignedL5Task[];
}

export interface RedesignedL3 {
  l3_id: string;
  l3_name: string;
  change_type: string;
  change_reason: string;
  l4_list: RedesignedL4[];
}

export interface PainContextItem {
  task_id: string;
  task_name: string;
  l4: string;
  l3: string;
  classification: "" | "AI" | "AI + Human" | "Human";
  classification_reason: string;
  hybrid_note: string;
  ai_prerequisites: string;
  pain_points: Array<{ type: string; text: string }>;
}

export interface HumanOnlyTask {
  task_id: string;
  task_name: string;
  l4: string;
  l3: string;
  actor: string;       // HR 임원 · HR 담당자 · 현업 팀장 등
  description: string;
}

export interface WorkflowStepResult extends NewWorkflowResult {
  benchmark_insights?: Array<{ source: string; insight: string; application: string }> | string[];
  l2_restructure?: string;
  design_philosophy?: string;
  redesigned_process?: RedesignedL3[];
  pain_context?: PainContextItem[];
  classification_stats?: { AI: number; "AI + Human": number; Human: number };
  human_only_tasks?: HumanOnlyTask[];
}

export interface WorkflowChatResponse {
  ok: boolean;
  message: string;
  updated: boolean;
  result: WorkflowStepResult | null;
  benchmark_updated?: boolean;
  benchmark_table?: Record<string, BenchmarkTableRow[]>;
}

export async function uploadWorkflowExcel(file: File): Promise<WorkflowExcelUploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${BACKEND_DIRECT}/api/workflow/upload-excel`, {
    method: "POST",
    headers,
    body: formData,
  });
  if (!res.ok) {
    if (res.status === 401) handle401();
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function selectWorkflowExcelSheet(sheetName: string): Promise<{
  ok: boolean;
  sheet_name: string;
  task_count: number;
  classified_count: number;
}> {
  return apiFetch("/workflow/select-excel-sheet", {
    method: "POST",
    body: JSON.stringify({ sheet_name: sheetName }),
  });
}

export async function getWorkflowExcelTasks(): Promise<{
  total: number;
  classified: number;
  tasks: WorkflowExcelTask[];
}> {
  return apiFetch("/workflow/excel-tasks");
}

export interface ReferenceBenchmark {
  case_no: number;
  title: string;
  companies: string[];      // 정확한 명칭 (IBM/GM/Siemens 등)
  stage: string;
  description: string;
  applicable_l2: string[];
}

export async function getReferenceBenchmarks(): Promise<{
  ok: boolean;
  references: ReferenceBenchmark[];
  total: number;
}> {
  return apiFetch("/workflow/reference-benchmarks");
}

export interface BenchmarkTableRow {
  source: string;
  company_type?: string;
  industry: string;
  process_area: string;
  ai_adoption_goal?: string;
  ai_technology: string;
  key_data?: string;
  adoption_method?: string;
  use_case: string;
  outcome: string;
  infrastructure?: string;
  implication: string;
  url: string;
}

export interface SearchLogItem {
  type: string;        // "engine", "plan", "round_start", "round_end", "query", "embed_rank", "gap", "done"
  text?: string;
  q?: string;
  found?: number | string;
  round?: number;
  query_count?: number;
  total?: number;
  final?: number;
  top_score?: number;
  status?: string;
  queries?: string[];
  hypotheses?: string[];
  engine?: string;
  fallback?: boolean;
}

export interface BenchmarkStep1Result {
  ok: boolean;
  result_count: number;
  sheet_id?: string;
  benchmark_table: BenchmarkTableRow[];
  all_benchmark_table?: Record<string, BenchmarkTableRow[]>;
  summary: string;
  search_log?: SearchLogItem[];
}

export async function benchmarkWorkflowStep1(params?: {
  companies?: string;
  sheet_id?: string;
  scope?: "l3" | "l4";
}): Promise<BenchmarkStep1Result> {
  return apiFetch("/workflow/benchmark-step1", {
    method: "POST",
    body: JSON.stringify(params || {}),
  });
}

// ── 벤치마킹 SSE 스트리밍 ────────────────────────────────────────────────────

export interface BmProgressEvent {
  type:
    | "engine"
    | "plan"
    | "queries"
    | "round_start"
    | "query_done"
    | "round_end"
    | "embed"
    | "done_search"
    | "llm_analyze"
    | "final"
    | "error";
  round?: number;
  text?: string;
  queries?: string[];
  count?: number;
  idx?: number;
  total?: number;
  query?: string;
  found?: number;
  collected?: number;
  final?: number;
  // final 이벤트 payload
  ok?: boolean;
  result_count?: number;
  sheet_id?: string;
  benchmark_table?: BenchmarkTableRow[];
  all_benchmark_table?: Record<string, BenchmarkTableRow[]>;
  summary?: string;
  search_log?: SearchLogItem[];
  message?: string;
}

export function benchmarkWorkflowStep1Stream(
  params: { companies?: string; sheet_id?: string; scope?: "l3" | "l4" },
  onProgress: (event: BmProgressEvent) => void,
  onDone: (result: BenchmarkStep1Result) => void,
  onError: (err: Error) => void
): () => void {
  const controller = new AbortController();
  const token =
    typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;

  (async () => {
    try {
      const res = await fetch(
        `${BACKEND_DIRECT}/api/workflow/benchmark-step1`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(params || {}),
          signal: controller.signal,
        }
      );

      if (!res.ok) {
        if (res.status === 401) handle401();
        const err = await res
          .json()
          .catch(() => ({ detail: `HTTP ${res.status}` }));
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
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data: BmProgressEvent = JSON.parse(line.slice(6));
          if (data.type === "final") {
            onDone({
              ok: data.ok ?? true,
              result_count: data.result_count ?? 0,
              sheet_id: data.sheet_id,
              benchmark_table: data.benchmark_table ?? [],
              all_benchmark_table: data.all_benchmark_table,
              summary: data.summary ?? "",
              search_log: data.search_log,
            });
          } else if (data.type === "error") {
            onError(new Error(data.message || "벤치마킹 오류"));
          } else {
            onProgress(data);
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") onError(err as Error);
    }
  })();

  return () => controller.abort();
}

export interface GapItem {
  l4_activity: string;
  as_is: string;
  to_be: string;
  gap_description: string;
  gap_type: "A. 신규" | "B. 전환" | "C. 폐기/통합";
  root_cause: string;
  action_plan: string;
  priority: number;
}

export interface GapWrapUpDim {
  headline: string;
  as_is: string;
  to_be: string;
  gaps: string[];
  implication: string;
}

export interface GapWrapUp {
  process_gap: GapWrapUpDim | string | null;
  infra_gap: GapWrapUpDim | string | null;
  data_gap: GapWrapUpDim | string | null;
}

export interface GapAnalysisResult {
  ok: boolean;
  process_name: string;
  executive_summary: string;
  gap_items: GapItem[];
  gap_wrap_up?: GapWrapUp;
  quick_wins: string[];
  strategic_actions: string[];
}

export async function generateGapAnalysis(sheetId?: string): Promise<GapAnalysisResult> {
  return apiFetch("/workflow/gap-analysis", {
    method: "POST",
    body: JSON.stringify({ sheet_id: sheetId ?? "" }),
  });
}

export async function deleteBenchmarkRow(source: string, sheetId?: string): Promise<{
  ok: boolean; deleted_source: string; remaining: number;
  benchmark_table: Record<string, BenchmarkTableRow[]>;
}> {
  return apiFetch("/workflow/benchmark-table/row", {
    method: "DELETE",
    body: JSON.stringify({ source, sheet_id: sheetId ?? "" }),
  });
}

export async function downloadBenchmarkTableXlsx(): Promise<void> {
  const token = getAuthToken();
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${BACKEND_DIRECT}/api/workflow/benchmark-table/export`, { headers });
  if (!res.ok) { if (res.status === 401) handle401(); throw new Error("벤치마킹 엑셀 다운로드 실패"); }
  const blob = await res.blob();
  const cd = res.headers.get("content-disposition") || "";
  const match = cd.match(/filename\*?=(?:UTF-8'')?([^;]+)/i);
  const filename = match ? decodeURIComponent(match[1].replace(/"/g, "")) : "벤치마킹_결과.xlsx";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ── To-Be Workflow Swim Lane ──────────────────────────────────────────────────

export type TobeActor =
  | "임원" | "현업 팀장" | "HR 임원" | "HR 담당자"
  | "Senior AI" | "Junior AI" | "현업 구성원" | "그 외";

export type TobeNodeType = "start" | "task" | "decision" | "end";
export type TobeNodeLevel = "L2" | "L3" | "L4" | "L5" | "DECISION" | "MEMO";

export interface TobeNode {
  id: string;
  label: string;
  actor: TobeActor;
  actors_all?: TobeActor[];
  custom_role?: string;          // "그 외:DDI"의 DDI 부분
  type: TobeNodeType;
  level: TobeNodeLevel;
  ai_support?: string | null;
  position?: { x: number; y: number };
  origin?: "asis" | "ai";
  task_id?: string;
  description?: string;
  data?: Record<string, unknown>; // 원본 As-Is data 객체 (LevelNode 렌더링용)
  next?: string[];
  // Junior AI 관련 추가 정보
  automation_level?: string;
  human_role?: string;
  input_data?: string[];
  output_data?: string[];
  agent_name?: string;
  benchmark_source?: string | null;   // 벤치마킹 title (있으면 label 의 prefix 파트)
}

export interface TobeEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  origin?: "asis" | "ai";
  // hr-workflow-ai 호환 — React Flow 표준 필드
  type?: string;
  animated?: boolean;
  style?: { stroke?: string; strokeWidth?: number; [k: string]: unknown };
  markerEnd?: { type?: string; width?: number; height?: number; color?: string };
}

export interface TobeSheet {
  l4_id: string;
  l4_name: string;
  actors_used: TobeActor[];
  lanes?: TobeActor[];
  laneHeights?: number[];   // hr-workflow-ai SwimLaneOverlay 용
  swimHeight?: number;      // 합계 — 앱 기본값 2400 대체
  nodes: TobeNode[];
  edges?: TobeEdge[];
}

export interface TobeFlowResult {
  ok: boolean;
  process_name: string;
  tobe_sheets: TobeSheet[];
}

export async function generateTobeFlow(params?: { sheet_id?: string }): Promise<TobeFlowResult> {
  return apiFetch("/workflow/generate-tobe-flow", {
    method: "POST",
    body: JSON.stringify(params ?? {}),
  });
}

// ── 사용자 첨부 리소스 ────────────────────────────────────────────────────────

export interface UserResource {
  type: "url" | "image";
  source: string;
  title: string;
  content: string;
  image_b64?: string;   // 이미지만 존재 (메모리 전용, 세션 저장 제외)
  image_path?: string;
  added_at: string;
}

export interface ResourceListResult {
  resources: UserResource[];
  total: number;
}

export async function getWorkflowResources(): Promise<ResourceListResult> {
  return apiFetch("/workflow/resources");
}

export async function addUrlResource(url: string): Promise<{ ok: boolean; resource: UserResource; total: number }> {
  return apiFetch("/workflow/resources/url", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export async function addImageResource(
  image_b64: string,
  image_type: string,
  filename: string,
): Promise<{ ok: boolean; resource: UserResource; total: number }> {
  return apiFetch("/workflow/resources/image", {
    method: "POST",
    body: JSON.stringify({ image_b64, image_type, filename }),
  });
}

export async function deleteWorkflowResource(idx: number): Promise<{ ok: boolean; total: number }> {
  return apiFetch(`/workflow/resources/${idx}`, { method: "DELETE" });
}

// ── 멀티 세션 ────────────────────────────────────────────────────────────────

export interface WorkflowSession {
  id: string;
  name: string;
  created_at: string;
  updated_at?: string;
  excel_file?: string;
  json_file?: string;
  ppt_file?: string;
}

export interface WorkflowSessionsResult {
  ok: boolean;
  current: string;
  sessions: WorkflowSession[];
}

export interface PMSessionSummary {
  id: string;
  name: string;
  created_at: string;
  updated_at?: string;
  has_step1: boolean;
  has_step2: boolean;
  has_benchmark: boolean;
  has_gap: boolean;
}

export interface PMUserSessions {
  user_id: string;
  sessions: PMSessionSummary[];
}

export async function listWorkflowSessions(): Promise<WorkflowSessionsResult> {
  return apiFetch("/workflow/sessions");
}

/** 새 빈 세션 즉시 생성 (프로젝트 목록에 바로 등록) */
export async function createWorkflowSession(name: string): Promise<{
  ok: boolean; session_id: string; name: string;
}> {
  return apiFetch("/workflow/sessions/create", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function getSessionsOverview(): Promise<{ ok: boolean; users: PMUserSessions[] }> {
  return apiFetch("/workflow/sessions/overview");
}

export async function loadWorkflowSession(sessionId: string): Promise<{
  ok: boolean;
  session_id: string;
  has_step1: boolean;
  has_step2: boolean;
  has_benchmark: boolean;
  has_gap: boolean;
  classified_count: number;
  sheets?: WorkflowSummary["sheets"];
}> {
  return apiFetch(`/workflow/sessions/${encodeURIComponent(sessionId)}/load`, { method: "POST", body: "{}" });
}

export async function deleteWorkflowSession(sessionId: string): Promise<{ ok: boolean; deleted: string }> {
  return apiFetch(`/workflow/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
}

export async function renameWorkflowSession(sessionId: string, name: string): Promise<{ ok: boolean; session_id: string; name: string }> {
  return apiFetch(`/workflow/sessions/${encodeURIComponent(sessionId)}/rename`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

export async function saveCurrentSession(): Promise<{ ok: boolean; session_id: string; name: string; saved_at: string }> {
  return apiFetch("/workflow/sessions/current/save", { method: "POST", body: "{}" });
}

export interface SessionFileInfo {
  filename: string;
  size_kb: number;
  modified: string;
  is_current: boolean;
}

export async function listSessionFiles(sessionId: string): Promise<{
  ok: boolean;
  session_id: string;
  excels: SessionFileInfo[];
  ppts: SessionFileInfo[];
  has_json: boolean;
}> {
  return apiFetch(`/workflow/sessions/${encodeURIComponent(sessionId)}/files`);
}

export async function selectWorkflowFile(sessionId: string, filename: string): Promise<WorkflowExcelUploadResult & { ok: boolean }> {
  return apiFetch("/workflow/select-file", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, filename }),
  });
}

export async function getUploadHistory(): Promise<{ ok: boolean; files: SessionFileInfo[] }> {
  return apiFetch("/upload/history");
}

export async function generateWorkflowStep1(params: {
  prompt?: string;
  process_name?: string;
  sheet_id?: string;
}): Promise<{ ok: boolean } & WorkflowStepResult> {
  return apiFetch("/workflow/generate-step1", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function chatWorkflowStep1(message: string, sheet_id?: string): Promise<WorkflowChatResponse> {
  return apiFetch("/workflow/chat-step1", {
    method: "POST",
    body: JSON.stringify({ message, sheet_id }),
  });
}

export async function generateWorkflowStep2(params?: {
  additional_context?: string;
  sheet_id?: string;
}): Promise<{ ok: boolean } & WorkflowStepResult> {
  return apiFetch("/workflow/generate-step2", {
    method: "POST",
    body: JSON.stringify(params || {}),
  });
}

export async function getWorkflowStepResults(): Promise<{
  ok: boolean;
  has_excel: boolean;
  has_asis: boolean;
  has_step1: boolean;
  has_step2: boolean;
  step1: WorkflowStepResult | null;
  step2: WorkflowStepResult | null;
  chat_history: Array<{ role: string; content: string }>;
  benchmark_table: Record<string, BenchmarkTableRow[]>;
  gap_analysis: GapAnalysisResult | null;
}> {
  return apiFetch("/workflow/step-results");
}

// ── Mapping Check ────────────────────────────────────────────────────────────

export interface MappingL5Node {
  task_id: string;
  label: string;
  matched: boolean;
  fuzzy_matched: boolean;
  manual_matched: boolean;
  fuzzy_score: number;
  excel_id: string;
  excel_name: string;
  cls_label: string;
  pain_points: string[];
  description: string;
}

export interface MappingL4Node {
  task_id: string;
  label: string;
  level: string;
  l5_nodes: MappingL5Node[];
  cls_summary?: Record<string, number>;
  matched_l5: number;
  total_l5: number;
}

export interface MappingL3Group {
  task_id: string;
  label: string;
  l4_nodes: MappingL4Node[];
  total_l5: number;
  matched_l5: number;
}

export interface MappingSheet {
  sheet_id: string;
  sheet_name: string;
  l3_count: number;
  l4_count: number;
  l3_groups: MappingL3Group[];
}

export interface MappingExcelOnly {
  id: string;
  name: string;
  l2: string; l2_id: string;
  l3: string; l3_id: string;
  l4: string; l4_id: string;
  label: string;
}

export interface MappingCheckResult {
  ok: boolean;
  has_excel: boolean;
  has_asis: boolean;
  stats: {
    total_excel_tasks: number;
    matched_excel_tasks: number;
    unmatched_excel_tasks: number;
    total_l4_nodes: number;
    matched_l4_nodes: number;
    unmatched_l4_nodes: number;
    total_l5_nodes: number;
    matched_l5_nodes: number;
    unmatched_l5_nodes: number;
    match_rate: number;
    cls_matched: Record<string, number>;
    cls_total: Record<string, number>;
  };
  sheets: MappingSheet[];
  excel_only: MappingExcelOnly[];
  l4_cls_stats: Array<{ task_id: string; label: string; cls_summary: Record<string, number> }>;
}

export async function getMappingCheck(): Promise<MappingCheckResult> {
  return apiFetch<MappingCheckResult>("/workflow/mapping-check");
}

export async function setManualMatch(jsonTaskId: string, excelTaskId: string): Promise<{ ok: boolean }> {
  return apiFetch("/workflow/manual-match", {
    method: "POST",
    body: JSON.stringify({ json_task_id: jsonTaskId, excel_task_id: excelTaskId }),
  });
}

export async function deleteManualMatch(jsonTaskId: string): Promise<{ ok: boolean }> {
  return apiFetch(`/workflow/manual-match/${encodeURIComponent(jsonTaskId)}`, { method: "DELETE" });
}

export interface HrWorkflowNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: {
    id: string;
    label: string;
    level: string;
    description?: string;
    role?: string;
    automationLevel?: string;
    aiTechnique?: string;
    inputs?: Record<string, boolean>;
    outputs?: Record<string, boolean>;
    nodeColor?: string;
  };
}

export interface HrWorkflowEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
  animated?: boolean;
  label?: string;
  style?: Record<string, unknown>;
  markerEnd?: Record<string, unknown>;
}

export interface HrWorkflowSheet {
  id: string;
  name: string;
  type: string;
  lanes: string[];
  nodes: HrWorkflowNode[];
  edges: HrWorkflowEdge[];
  agentColors?: Record<string, string>;
}

export interface HrWorkflowJson {
  version: string;
  exportedAt: string;
  sheets: HrWorkflowSheet[];
}

export async function fetchToBeWorkflowJson(): Promise<HrWorkflowJson> {
  return apiFetch<HrWorkflowJson>("/workflow/export-tobe-json");
}

export async function downloadToBeWorkflowJson(): Promise<void> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${BACKEND_DIRECT}/api/workflow/export-tobe-json`, { headers });
  if (!res.ok) { if (res.status === 401) handle401(); throw new Error("다운로드 실패"); }
  const blob = await res.blob();
  const cd = res.headers.get("content-disposition") || "";
  const fnMatch = cd.match(/filename\*?=(?:UTF-8'')?(.+)/i);
  const filename = fnMatch ? decodeURIComponent(fnMatch[1].replace(/"/g, "")) : "tobe_workflow.json";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** generate-tobe-flow 결과를 hr-workflow-ai 호환 JSON으로 다운로드 (swim lane 버전) */
export async function downloadTobeFlowJson(): Promise<void> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${BACKEND_DIRECT}/api/workflow/export-tobe-flow-json`, { headers });
  if (!res.ok) { if (res.status === 401) handle401(); throw new Error("To-Be Flow JSON 다운로드 실패"); }
  const blob = await res.blob();
  const cd = res.headers.get("content-disposition") || "";
  const fnMatch = cd.match(/filename\*?=(?:UTF-8'')?(.+)/i);
  const filename = fnMatch ? decodeURIComponent(fnMatch[1].replace(/"/g, "")) : "tobe_flow.json";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** To-Be 설계를 As-Is 템플릿 포맷 Excel로 다운로드 */
export async function downloadTobeDesignExcel(): Promise<void> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${BACKEND_DIRECT}/api/workflow/export-tobe-excel`, { headers });
  if (!res.ok) { if (res.status === 401) handle401(); throw new Error("To-Be Excel 다운로드 실패"); }
  const blob = await res.blob();
  const cd = res.headers.get("content-disposition") || "";
  const fnMatch = cd.match(/filename\*?=(?:UTF-8'')?(.+)/i);
  const filename = fnMatch ? decodeURIComponent(fnMatch[1].replace(/"/g, "")) : "ToBe_설계.xlsx";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
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
    if (res.status === 401) handle401();
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
  ai_technique?: string;   // task 전용 AI 기법 (Agent 레벨과 다를 수 있음)
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
    if (res.status === 401) handle401();
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
    if (res.status === 401) handle401();
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
    if (res.status === 401) handle401();
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


// ── Admin API ─────────────────────────────────────────────────────────────────

export interface AdminUser {
  email: string;
  name: string;
  created_at: string;
  must_change_password: boolean;
  active_sessions: number;
  session_ips: string[];
  project?: string | null;
  projects?: string[];
}

export interface AdminSession {
  token_prefix: string;
  email: string;
  ip: string;
  user_agent: string;
  login_at: string;
}

export interface AuditLogEntry {
  timestamp: string;
  event: string;
  email: string;
  ip: string;
  detail: string;
}

export async function getAdminDashboard(): Promise<{
  ok: boolean;
  users: AdminUser[];
  active_sessions: AdminSession[];
  login_history: AuditLogEntry[];
  data_activity: AuditLogEntry[];
  total_sessions: number;
  total_users: number;
}> {
  return apiFetch("/admin/dashboard");
}

export async function getAdminAuditLog(params?: {
  limit?: number;
  offset?: number;
  email?: string;
  event?: string;
  ip?: string;
}): Promise<{ ok: boolean; logs: AuditLogEntry[]; total: number }> {
  const qs = new URLSearchParams();
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.offset) qs.set("offset", String(params.offset));
  if (params?.email) qs.set("email", params.email);
  if (params?.event) qs.set("event", params.event);
  if (params?.ip) qs.set("ip", params.ip);
  const q = qs.toString() ? `?${qs}` : "";
  return apiFetch(`/admin/audit-log${q}`);
}

export async function adminForceLogout(email: string): Promise<{ ok: boolean; sessions_removed: number }> {
  return apiFetch("/admin/force-logout", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export interface UploadedFile {
  filename: string;
  size_kb: number;
  modified: string;
  path?: string;
  session_id?: string;
  display_name?: string;
}

export async function getAdminUploads(): Promise<{ ok: boolean; directory: string; files: UploadedFile[] }> {
  return apiFetch("/admin/uploads");
}

export interface AdminUploadsAll {
  ok: boolean;
  categories: {
    task_excel: UploadedFile[];
    wf_excel: UploadedFile[];
    wf_json: UploadedFile[];
    wf_ppt: UploadedFile[];
    new_workflow: UploadedFile[];
  };
}

export async function getAdminUploadsAll(): Promise<AdminUploadsAll> {
  return apiFetch("/admin/uploads-all");
}

export async function downloadAdminFile(filename: string, sessionId?: string): Promise<void> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
  const qs = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
  const res = await fetch(
    `${BACKEND_DIRECT}/api/admin/download/${encodeURIComponent(filename)}${qs}`,
    { headers },
  );
  if (!res.ok) { if (res.status === 401) handle401(); throw new Error("다운로드 실패"); }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function deleteAdminWorkflowSession(sessionId: string): Promise<{ ok: boolean; deleted: string }> {
  return apiFetch(`/admin/workflow-session/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
}

export async function deleteAdminUpload(filename: string): Promise<{ ok: boolean; deleted: string }> {
  return apiFetch(`/admin/upload/${encodeURIComponent(filename)}`, { method: "DELETE" });
}

export async function getAdminProjects(): Promise<{ ok: boolean; projects: ProjectInfo[] }> {
  return apiFetch("/admin/projects");
}

export async function deleteAdminProject(dirname: string): Promise<{ ok: boolean; deleted: string }> {
  return apiFetch(`/admin/projects/${encodeURIComponent(dirname)}`, { method: "DELETE" });
}

export async function deleteAdminWorkflowFile(filename: string): Promise<{ ok: boolean; deleted: string }> {
  return apiFetch(`/admin/workflow-file/${encodeURIComponent(filename)}`, { method: "DELETE" });
}

export async function resetAllWorkflow(): Promise<{ ok: boolean; deleted: string[]; errors: string[] }> {
  return apiFetch("/admin/workflow-reset", { method: "DELETE" });
}
