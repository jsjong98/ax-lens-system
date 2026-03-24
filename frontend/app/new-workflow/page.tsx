"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  uploadNewWorkflowExcel,
  selectNewWorkflowSheet,
  getNewWorkflowFilters,
  generateNewWorkflow,
  downloadNewWorkflowAsHrJson,
  type ExcelSheet,
  type NewWorkflowResult,
  type NewWorkflowAgent,
  type NewWorkflowAssignedTask,
} from "@/lib/api";
import {
  Sparkles, ChevronDown, ChevronRight, Loader2, RefreshCw,
  Bot, User, Zap, Download, Upload, FileSpreadsheet, ArrowRight,
  FolderKanban,
} from "lucide-react";

/* ── 색상 ────────────────────────────────────────────────────────────────── */
const PWC = { primary: "#A62121", bg: "#FFF5F7", cardBg: "#FFFFFF" };

const AUTO_COLOR: Record<string, { bg: string; text: string; border: string }> = {
  "Full-Auto":        { bg: "#D6F5E3", text: "#1a7a45", border: "#6fcf97" },
  "Human-in-Loop":    { bg: "#FFF9DB", text: "#7a5c00", border: "#f2c94c" },
  "Human-Supervised": { bg: "#FFE0E0", text: "#A62121", border: "#eb5757" },
};

/* ── 뱃지 ─────────────────────────────────────────────────────────────────── */
function AutoBadge({ level }: { level: string }) {
  const c = AUTO_COLOR[level] ?? { bg: "#f0f0f0", text: "#333", border: "#ccc" };
  return (
    <span className="inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold"
      style={{ backgroundColor: c.bg, color: c.text, border: `1px solid ${c.border}` }}>
      {level}
    </span>
  );
}

/* ── Task 행 ──────────────────────────────────────────────────────────────── */
function TaskRow({ task }: { task: NewWorkflowAssignedTask }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-gray-100 last:border-0">
      <button className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
        onClick={() => setOpen((v) => !v)}>
        <span className="mt-0.5 text-gray-400 flex-shrink-0">
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono text-gray-400">{task.task_id}</span>
            <span className="text-sm font-medium text-gray-800 truncate">{task.task_name}</span>
            <AutoBadge level={task.automation_level} />
          </div>
          <p className="text-xs text-gray-500 mt-0.5">{task.l3} &gt; {task.l4}</p>
        </div>
      </button>
      {open && (
        <div className="px-10 pb-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="rounded-lg p-3" style={{ backgroundColor: "#EBF8F0", border: "1px solid #6fcf97" }}>
              <div className="flex items-center gap-1.5 mb-1">
                <Bot className="h-3.5 w-3.5" style={{ color: "#1a7a45" }} />
                <span className="text-xs font-semibold" style={{ color: "#1a7a45" }}>AI 역할</span>
              </div>
              <p className="text-sm text-gray-700">{task.ai_role || "—"}</p>
            </div>
            {task.human_role && (
              <div className="rounded-lg p-3" style={{ backgroundColor: "#FFF9DB", border: "1px solid #f2c94c" }}>
                <div className="flex items-center gap-1.5 mb-1">
                  <User className="h-3.5 w-3.5" style={{ color: "#7a5c00" }} />
                  <span className="text-xs font-semibold" style={{ color: "#7a5c00" }}>Human 역할</span>
                </div>
                <p className="text-sm text-gray-700">{task.human_role}</p>
              </div>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {task.input_data.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 mb-1">INPUT</p>
                <ul className="space-y-1">
                  {task.input_data.map((d, i) => (
                    <li key={i} className="flex items-center gap-1.5 text-sm text-gray-700">
                      <span className="h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: PWC.primary }} />{d}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {task.output_data.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 mb-1">OUTPUT</p>
                <ul className="space-y-1">
                  {task.output_data.map((d, i) => (
                    <li key={i} className="flex items-center gap-1.5 text-sm text-gray-700">
                      <span className="h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: "#6fcf97" }} />{d}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Agent 카드 ───────────────────────────────────────────────────────────── */
function AgentCard({ agent }: { agent: NewWorkflowAgent }) {
  const [open, setOpen] = useState(true);
  const c = AUTO_COLOR[agent.automation_level] ?? { bg: "#f0f0f0", text: "#333", border: "#ccc" };
  return (
    <div className="rounded-xl overflow-hidden shadow-sm" style={{ border: `1px solid ${c.border}`, backgroundColor: PWC.cardBg }}>
      <div className="px-5 py-4 cursor-pointer" style={{ backgroundColor: c.bg }} onClick={() => setOpen((v) => !v)}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <Bot className="h-4 w-4 flex-shrink-0" style={{ color: c.text }} />
              <h3 className="font-semibold text-gray-900">{agent.agent_name}</h3>
              <AutoBadge level={agent.automation_level} />
            </div>
            <p className="text-sm mt-1" style={{ color: c.text }}>{agent.agent_type} · {agent.ai_technique}</p>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <span className="text-sm font-medium text-gray-500">{agent.task_count}개 Task</span>
            {open ? <ChevronDown className="h-4 w-4 text-gray-400" /> : <ChevronRight className="h-4 w-4 text-gray-400" />}
          </div>
        </div>
        {agent.description && <p className="mt-2 text-sm text-gray-600">{agent.description}</p>}
      </div>
      {open && <div>{agent.assigned_tasks.map((t) => <TaskRow key={t.task_id} task={t} />)}</div>}
    </div>
  );
}

/* ── 실행 플로우 ──────────────────────────────────────────────────────────── */
function ExecutionFlow({ result }: { result: NewWorkflowResult }) {
  const agentMap = Object.fromEntries(result.agents.map((a) => [a.agent_id, a]));
  return (
    <div className="space-y-3">
      {result.execution_flow.map((step, idx) => (
        <div key={step.step} className="flex gap-4">
          <div className="flex flex-col items-center">
            <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-sm font-bold text-white"
              style={{ backgroundColor: PWC.primary }}>{step.step}</div>
            {idx < result.execution_flow.length - 1 && <div className="w-0.5 flex-1 mt-1" style={{ backgroundColor: "#e5e7eb" }} />}
          </div>
          <div className="flex-1 pb-6">
            <div className="flex items-center gap-2 mb-1">
              <p className="font-semibold text-gray-800">{step.step_name}</p>
              {step.step_type === "parallel" && (
                <span className="rounded-full px-2 py-0.5 text-xs font-medium"
                  style={{ backgroundColor: "#EBF4FF", color: "#2F80ED", border: "1px solid #2F80ED" }}>병렬</span>
              )}
            </div>
            <p className="text-sm text-gray-500 mb-2">{step.description}</p>
            <div className="flex flex-wrap gap-2">
              {step.agent_ids.map((aid) => {
                const agent = agentMap[aid];
                if (!agent) return null;
                const ac = AUTO_COLOR[agent.automation_level] ?? { bg: "#f0f0f0", text: "#333", border: "#ccc" };
                return (
                  <span key={aid} className="flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium"
                    style={{ backgroundColor: ac.bg, color: ac.text, border: `1px solid ${ac.border}` }}>
                    <Bot className="h-3 w-3" />{agent.agent_name}
                  </span>
                );
              })}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════ */
/* ── 메인 페이지 ─────────────────────────────────────────────────────────── */
/* ══════════════════════════════════════════════════════════════════════════ */

export default function NewWorkflowPage() {
  const router = useRouter();

  // 업로드 상태
  const [uploading, setUploading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const [taskCount, setTaskCount] = useState(0);
  const [sheets, setSheets] = useState<ExcelSheet[]>([]);
  const [selectedSheet, setSelectedSheet] = useState("");

  // 생성 상태
  const [l3Options, setL3Options] = useState<{ id: string; name: string }[]>([]);
  const [selectedL3, setSelectedL3] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<NewWorkflowResult | null>(null);
  const [activeTab, setActiveTab] = useState<"ai" | "human" | "flow">("ai");
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  // 파일 업로드
  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      const res = await uploadNewWorkflowExcel(file);
      setUploadedFile(res.filename);
      setTaskCount(res.task_count);
      setSheets(res.sheets);
      setResult(null);
      // 필터 옵션 로드
      const filters = await getNewWorkflowFilters();
      setL3Options(filters.l3_options);
    } catch (e) {
      setError(e instanceof Error ? e.message : "업로드 실패");
    } finally {
      setUploading(false);
    }
  }, []);

  // 시트 선택
  const handleSelectSheet = async (sheetName: string) => {
    setSelectedSheet(sheetName);
    try {
      const res = await selectNewWorkflowSheet(sheetName);
      setTaskCount(res.task_count);
      const filters = await getNewWorkflowFilters();
      setL3Options(filters.l3_options);
      setResult(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "시트 로드 실패");
    }
  };

  // Workflow 생성
  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await generateNewWorkflow({ l3: selectedL3 || undefined });
      setResult(res);
      setActiveTab("ai");
    } catch (e) {
      setError(e instanceof Error ? e.message : "생성 중 오류 발생");
    } finally {
      setLoading(false);
    }
  };

  // Export
  const handleExport = async () => {
    setExporting(true);
    try { await downloadNewWorkflowAsHrJson(); }
    catch (e) { setError(e instanceof Error ? e.message : "내보내기 실패"); }
    finally { setExporting(false); }
  };

  // AI / Human Task 분리
  const aiTasks = result?.agents.flatMap((a) =>
    a.assigned_tasks.filter((t) => t.automation_level === "Full-Auto")
  ) ?? [];
  const humanTasks = result?.agents.flatMap((a) =>
    a.assigned_tasks.filter((t) => t.automation_level !== "Full-Auto")
  ) ?? [];

  return (
    <div className="min-h-screen" style={{ backgroundColor: PWC.bg }}>
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">

        {/* 헤더 */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Sparkles className="h-6 w-6" style={{ color: PWC.primary }} />
            <h1 className="text-2xl font-bold text-gray-900">New Workflow</h1>
          </div>
          <p className="text-gray-500 text-sm">
            As-Is 프로세스 엑셀을 업로드하면, AI가 L4 기반으로 새로운 L5 Task를 정의하고 AI/Human 역할을 설계합니다.
          </p>
        </div>

        {/* ── Step 1: 엑셀 업로드 ─────────────────────────────────────────────── */}
        <div className="rounded-xl p-5 mb-6 shadow-sm" style={{ backgroundColor: PWC.cardBg, border: "1px solid #f0e0e0" }}>
          <div className="flex items-center gap-2 mb-3">
            <FileSpreadsheet className="h-5 w-5" style={{ color: PWC.primary }} />
            <h2 className="text-base font-semibold text-gray-900">1. 엑셀 파일 업로드</h2>
          </div>

          {!uploadedFile ? (
            <label className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 py-10 cursor-pointer hover:border-[#A62121] transition-colors">
              <input
                type="file"
                accept=".xlsx"
                className="hidden"
                onChange={(e) => { if (e.target.files?.[0]) handleUpload(e.target.files[0]); }}
                disabled={uploading}
              />
              {uploading ? (
                <Loader2 className="h-8 w-8 animate-spin text-gray-400 mb-2" />
              ) : (
                <Upload className="h-8 w-8 text-gray-400 mb-2" />
              )}
              <p className="text-sm text-gray-600 font-medium">
                {uploading ? "업로드 중..." : "클릭하거나 파일을 드래그해서 업로드"}
              </p>
              <p className="text-xs text-gray-400 mt-1">HR As-Is 템플릿 .xlsx 파일</p>
            </label>
          ) : (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileSpreadsheet className="h-5 w-5 text-green-600" />
                <div>
                  <p className="text-sm font-medium text-gray-900">{uploadedFile}</p>
                  <p className="text-xs text-gray-500">{taskCount}개 Task 로드됨</p>
                </div>
              </div>
              <label className="text-sm cursor-pointer font-medium" style={{ color: PWC.primary }}>
                <input
                  type="file"
                  accept=".xlsx"
                  className="hidden"
                  onChange={(e) => { if (e.target.files?.[0]) handleUpload(e.target.files[0]); }}
                />
                다른 파일
              </label>
            </div>
          )}

          {/* 시트 선택 */}
          {sheets.length > 1 && (
            <div className="mt-3">
              <label className="block text-xs font-medium text-gray-500 mb-1">시트 선택</label>
              <select
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                value={selectedSheet}
                onChange={(e) => handleSelectSheet(e.target.value)}
              >
                {sheets.map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.name} ({s.l5_count} tasks){s.recommended ? " ★ 추천" : ""}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* ── Step 2: 생성 컨트롤 ─────────────────────────────────────────────── */}
        {uploadedFile && taskCount > 0 && (
          <div className="rounded-xl p-5 mb-6 shadow-sm" style={{ backgroundColor: PWC.cardBg, border: "1px solid #f0e0e0" }}>
            <div className="flex items-center gap-2 mb-3">
              <Zap className="h-5 w-5" style={{ color: PWC.primary }} />
              <h2 className="text-base font-semibold text-gray-900">2. To-Be Workflow 생성</h2>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 items-end">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  L3 필터 <span className="text-gray-400 font-normal">(선택)</span>
                </label>
                <select
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#A62121]"
                  value={selectedL3}
                  onChange={(e) => setSelectedL3(e.target.value)}
                >
                  <option value="">전체</option>
                  {l3Options.map((o) => (
                    <option key={o.id} value={o.name}>{o.name}</option>
                  ))}
                </select>
              </div>
              <button
                onClick={handleGenerate}
                disabled={loading}
                className="flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold text-white transition-opacity disabled:opacity-60"
                style={{ backgroundColor: PWC.primary }}
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : result ? <RefreshCw className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
                {loading ? "AI가 새 Workflow를 설계하고 있습니다..." : result ? "재생성" : "AI Workflow 설계 시작"}
              </button>
            </div>
          </div>
        )}

        {/* 에러 */}
        {error && (
          <div className="mb-6 rounded-lg p-4 text-sm" style={{ backgroundColor: "#FFE0E0", color: PWC.primary, border: `1px solid ${PWC.primary}` }}>
            {error}
          </div>
        )}

        {/* ── Step 3: 결과 ─────────────────────────────────────────────────────── */}
        {result && (
          <>
            {/* 요약 */}
            <div className="rounded-xl p-5 mb-6 shadow-sm" style={{ backgroundColor: PWC.cardBg, border: "1px solid #f0e0e0" }}>
              <h2 className="text-base font-semibold text-gray-900 mb-3">
                {result.process_name} — To-Be Workflow 설계 결과
              </h2>
              <p className="text-sm text-gray-600 leading-relaxed mb-4">{result.blueprint_summary}</p>

              {/* AI / Human 통계 */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="rounded-lg p-3 text-center" style={{ backgroundColor: "#f5f5f5" }}>
                  <p className="text-2xl font-bold text-gray-900">{result.total_tasks}</p>
                  <p className="text-xs text-gray-500 mt-0.5">총 신규 Task</p>
                </div>
                <div className="rounded-lg p-3 text-center" style={{ backgroundColor: AUTO_COLOR["Full-Auto"].bg }}>
                  <p className="text-2xl font-bold" style={{ color: AUTO_COLOR["Full-Auto"].text }}>{aiTasks.length}</p>
                  <p className="text-xs mt-0.5" style={{ color: AUTO_COLOR["Full-Auto"].text }}>AI 수행</p>
                </div>
                <div className="rounded-lg p-3 text-center" style={{ backgroundColor: AUTO_COLOR["Human-in-Loop"].bg }}>
                  <p className="text-2xl font-bold" style={{ color: AUTO_COLOR["Human-in-Loop"].text }}>{humanTasks.length}</p>
                  <p className="text-xs mt-0.5" style={{ color: AUTO_COLOR["Human-in-Loop"].text }}>Human 수행</p>
                </div>
                <div className="rounded-lg p-3 text-center" style={{ backgroundColor: "#EBF4FF" }}>
                  <p className="text-2xl font-bold" style={{ color: "#2F80ED" }}>{result.agents.length}</p>
                  <p className="text-xs mt-0.5" style={{ color: "#2F80ED" }}>AI Agent</p>
                </div>
              </div>
            </div>

            {/* 탭 + 버튼 */}
            <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
              <div className="flex gap-1 rounded-lg p-1 w-fit" style={{ backgroundColor: "#f0e0e0" }}>
                {([
                  { key: "ai", label: `AI Task (${aiTasks.length})` },
                  { key: "human", label: `Human Task (${humanTasks.length})` },
                  { key: "flow", label: "실행 플로우" },
                ] as const).map(({ key, label }) => (
                  <button
                    key={key}
                    onClick={() => setActiveTab(key)}
                    className="rounded-md px-4 py-1.5 text-sm font-medium transition-colors"
                    style={activeTab === key ? { backgroundColor: PWC.primary, color: "#fff" } : { color: PWC.primary }}
                  >
                    {label}
                  </button>
                ))}
              </div>

              <div className="flex gap-2">
                <button onClick={handleExport} disabled={exporting}
                  className="flex items-center gap-2 rounded-lg border px-4 py-1.5 text-sm font-medium disabled:opacity-60"
                  style={{ borderColor: PWC.primary, color: PWC.primary }}>
                  {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                  JSON 내보내기
                </button>
              </div>
            </div>

            {/* AI Task 탭 */}
            {activeTab === "ai" && (
              <div className="space-y-4">
                {result.agents
                  .filter((a) => a.automation_level === "Full-Auto")
                  .map((agent) => <AgentCard key={agent.agent_id} agent={agent} />)}
                {result.agents
                  .filter((a) => a.automation_level === "Full-Auto").length === 0 && (
                  <div className="text-center py-8 text-gray-400 text-sm">Full-Auto AI 에이전트가 없습니다.</div>
                )}
              </div>
            )}

            {/* Human Task 탭 */}
            {activeTab === "human" && (
              <div className="space-y-4">
                {result.agents
                  .filter((a) => a.automation_level !== "Full-Auto")
                  .map((agent) => <AgentCard key={agent.agent_id} agent={agent} />)}
                {result.agents
                  .filter((a) => a.automation_level !== "Full-Auto").length === 0 && (
                  <div className="text-center py-8 text-gray-400 text-sm">Human 관여 에이전트가 없습니다.</div>
                )}
              </div>
            )}

            {/* 실행 플로우 탭 */}
            {activeTab === "flow" && (
              <div className="rounded-xl p-5 shadow-sm" style={{ backgroundColor: PWC.cardBg, border: "1px solid #f0e0e0" }}>
                <h2 className="text-base font-semibold text-gray-900 mb-5">To-Be Workflow 실행 순서</h2>
                <ExecutionFlow result={result} />
              </div>
            )}

            {/* ── 과제 관리로 연결 ────────────────────────────────────────────── */}
            <div className="mt-8 rounded-xl p-6 shadow-sm text-center"
              style={{ backgroundColor: PWC.cardBg, border: "2px solid #f0e0e0" }}>
              <FolderKanban className="mx-auto h-8 w-8 mb-3" style={{ color: PWC.primary }} />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">과제 관리로 이어서 진행하기</h3>
              <p className="text-sm text-gray-500 mb-4">
                이 Workflow 설계 결과를 기반으로 과제 정의서와 설계서를 자동 생성할 수 있습니다.
              </p>
              <button
                onClick={() => router.push("/project-management?source=new-workflow")}
                className="inline-flex items-center gap-2 rounded-lg px-6 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
                style={{ backgroundColor: PWC.primary }}
              >
                <FolderKanban className="h-4 w-4" />
                과제 정의서 / 설계서 생성
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </>
        )}

        {/* 빈 상태 */}
        {!result && !loading && !uploadedFile && (
          <div className="rounded-xl py-16 text-center" style={{ backgroundColor: PWC.cardBg, border: "1px dashed #d9a0a0" }}>
            <Sparkles className="mx-auto h-10 w-10 mb-4" style={{ color: "#d9a0a0" }} />
            <p className="text-gray-500 text-sm">엑셀 파일을 업로드하면 AI가 새로운 To-Be Workflow를 설계합니다.</p>
          </div>
        )}
      </div>
    </div>
  );
}
