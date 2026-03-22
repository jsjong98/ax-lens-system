"use client";

import { useState, useEffect } from "react";
import {
  generateNewWorkflow,
  getFilterOptions,
  type NewWorkflowResult,
  type NewWorkflowAgent,
  type NewWorkflowAssignedTask,
} from "@/lib/api";
import { Sparkles, ChevronDown, ChevronRight, Loader2, RefreshCw, Bot, User, Zap } from "lucide-react";

/* ── 색상 ────────────────────────────────────────────────────────────────── */
const PWC = {
  primary: "#A62121",
  bg: "#FFF5F7",
  cardBg: "#FFFFFF",
};

const AUTOMATION_COLOR: Record<string, { bg: string; text: string; border: string }> = {
  "Full-Auto":         { bg: "#D6F5E3", text: "#1a7a45", border: "#6fcf97" },
  "Human-in-Loop":     { bg: "#FFF9DB", text: "#7a5c00", border: "#f2c94c" },
  "Human-Supervised":  { bg: "#FFE0E0", text: "#A62121", border: "#eb5757" },
};

const AUTOMATION_LABEL: Record<string, string> = {
  "Full-Auto":        "Full Auto",
  "Human-in-Loop":    "Human-in-Loop",
  "Human-Supervised": "Human-Supervised",
};

/* ── 컴포넌트: 자동화 수준 뱃지 ──────────────────────────────────────────── */
function AutoBadge({ level }: { level: string }) {
  const c = AUTOMATION_COLOR[level] ?? { bg: "#f0f0f0", text: "#333", border: "#ccc" };
  return (
    <span
      className="inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold"
      style={{ backgroundColor: c.bg, color: c.text, border: `1px solid ${c.border}` }}
    >
      {AUTOMATION_LABEL[level] ?? level}
    </span>
  );
}

/* ── 컴포넌트: 개별 Task 행 ─────────────────────────────────────────────── */
function TaskRow({ task }: { task: NewWorkflowAssignedTask }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-gray-100 last:border-0">
      <button
        className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
        onClick={() => setOpen((v) => !v)}
      >
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
          {/* AI / Human 역할 */}
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

          {/* Input / Output */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {task.input_data.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 mb-1">INPUT</p>
                <ul className="space-y-1">
                  {task.input_data.map((d, i) => (
                    <li key={i} className="flex items-center gap-1.5 text-sm text-gray-700">
                      <span className="h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: PWC.primary }} />
                      {d}
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
                      <span className="h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: "#6fcf97" }} />
                      {d}
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

/* ── 컴포넌트: AI 에이전트 카드 ─────────────────────────────────────────── */
function AgentCard({ agent }: { agent: NewWorkflowAgent }) {
  const [open, setOpen] = useState(true);
  const c = AUTOMATION_COLOR[agent.automation_level] ?? { bg: "#f0f0f0", text: "#333", border: "#ccc" };

  return (
    <div className="rounded-xl overflow-hidden shadow-sm" style={{ border: `1px solid ${c.border}`, backgroundColor: PWC.cardBg }}>
      {/* 카드 헤더 */}
      <div
        className="px-5 py-4 cursor-pointer"
        style={{ backgroundColor: c.bg }}
        onClick={() => setOpen((v) => !v)}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <Bot className="h-4 w-4 flex-shrink-0" style={{ color: c.text }} />
              <h3 className="font-semibold text-gray-900">{agent.agent_name}</h3>
              <AutoBadge level={agent.automation_level} />
            </div>
            <p className="text-sm mt-1" style={{ color: c.text }}>
              {agent.agent_type} · {agent.ai_technique}
            </p>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <span className="text-sm font-medium text-gray-500">
              {agent.task_count}개 Task
            </span>
            {open ? <ChevronDown className="h-4 w-4 text-gray-400" /> : <ChevronRight className="h-4 w-4 text-gray-400" />}
          </div>
        </div>

        {agent.description && (
          <p className="mt-2 text-sm text-gray-600">{agent.description}</p>
        )}
      </div>

      {/* Task 목록 */}
      {open && (
        <div>
          {agent.assigned_tasks.map((task) => (
            <TaskRow key={task.task_id} task={task} />
          ))}
        </div>
      )}
    </div>
  );
}

/* ── 컴포넌트: 실행 플로우 ──────────────────────────────────────────────── */
function ExecutionFlow({ result }: { result: NewWorkflowResult }) {
  const agentMap = Object.fromEntries(result.agents.map((a) => [a.agent_id, a]));

  return (
    <div className="space-y-3">
      {result.execution_flow.map((step, idx) => (
        <div key={step.step} className="flex gap-4">
          {/* 스텝 번호 + 연결선 */}
          <div className="flex flex-col items-center">
            <div
              className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-sm font-bold text-white"
              style={{ backgroundColor: PWC.primary }}
            >
              {step.step}
            </div>
            {idx < result.execution_flow.length - 1 && (
              <div className="w-0.5 flex-1 mt-1" style={{ backgroundColor: "#e5e7eb" }} />
            )}
          </div>

          {/* 스텝 내용 */}
          <div className="flex-1 pb-6">
            <div className="flex items-center gap-2 mb-1">
              <p className="font-semibold text-gray-800">{step.step_name}</p>
              {step.step_type === "parallel" && (
                <span className="rounded-full px-2 py-0.5 text-xs font-medium"
                  style={{ backgroundColor: "#EBF4FF", color: "#2F80ED", border: "1px solid #2F80ED" }}>
                  병렬
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500 mb-2">{step.description}</p>
            <div className="flex flex-wrap gap-2">
              {step.agent_ids.map((aid) => {
                const agent = agentMap[aid];
                if (!agent) return null;
                const c = AUTOMATION_COLOR[agent.automation_level] ?? { bg: "#f0f0f0", text: "#333", border: "#ccc" };
                return (
                  <span
                    key={aid}
                    className="flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium"
                    style={{ backgroundColor: c.bg, color: c.text, border: `1px solid ${c.border}` }}
                  >
                    <Bot className="h-3 w-3" />
                    {agent.agent_name}
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

/* ── 메인 페이지 ────────────────────────────────────────────────────────── */
export default function NewWorkflowPage() {
  const [result, setResult] = useState<NewWorkflowResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"agents" | "flow">("agents");
  const [l3Options, setL3Options] = useState<{ id: string; name: string }[]>([]);
  const [selectedL3, setSelectedL3] = useState("");

  useEffect(() => {
    getFilterOptions()
      .then((f) => setL3Options(f.l3 ?? []))
      .catch(() => {});
  }, []);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await generateNewWorkflow({
        l3: selectedL3 || undefined,
      });
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "생성 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: PWC.bg }}>
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">

        {/* 페이지 헤더 */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Sparkles className="h-6 w-6" style={{ color: PWC.primary }} />
            <h1 className="text-2xl font-bold text-gray-900">New Workflow</h1>
          </div>
          <p className="text-gray-500 text-sm">
            엑셀 파일의 L5 Task를 분석하여 AI가 어떻게 통합되어야 하는지 워크플로우 설계 초안을 자동으로 생성합니다.
          </p>
        </div>

        {/* 생성 컨트롤 */}
        <div className="rounded-xl p-5 mb-6 shadow-sm" style={{ backgroundColor: PWC.cardBg, border: "1px solid #f0e0e0" }}>
          <div className="flex flex-col sm:flex-row gap-3 items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                L3 단위 프로세스 필터 <span className="text-gray-400 font-normal">(선택 · 비우면 전체)</span>
              </label>
              <select
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2"
                style={{ focusRingColor: PWC.primary } as React.CSSProperties}
                value={selectedL3}
                onChange={(e) => setSelectedL3(e.target.value)}
              >
                <option value="">전체 Task</option>
                {l3Options.map((o) => (
                  <option key={o.id} value={o.name}>{o.name}</option>
                ))}
              </select>
            </div>

            <button
              onClick={handleGenerate}
              disabled={loading}
              className="flex items-center gap-2 rounded-lg px-5 py-2 text-sm font-semibold text-white transition-opacity disabled:opacity-60"
              style={{ backgroundColor: PWC.primary }}
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : result ? (
                <RefreshCw className="h-4 w-4" />
              ) : (
                <Zap className="h-4 w-4" />
              )}
              {loading ? "AI 설계 중..." : result ? "재생성" : "AI 워크플로우 설계"}
            </button>
          </div>
        </div>

        {/* 에러 */}
        {error && (
          <div className="mb-6 rounded-lg p-4 text-sm" style={{ backgroundColor: "#FFE0E0", color: PWC.primary, border: `1px solid ${PWC.primary}` }}>
            {error}
          </div>
        )}

        {/* 결과 */}
        {result && (
          <>
            {/* 요약 카드 */}
            <div className="rounded-xl p-5 mb-6 shadow-sm" style={{ backgroundColor: PWC.cardBg, border: "1px solid #f0e0e0" }}>
              <h2 className="text-base font-semibold text-gray-900 mb-3">{result.process_name} — AI 통합 설계 요약</h2>
              <p className="text-sm text-gray-600 leading-relaxed mb-4">{result.blueprint_summary}</p>

              {/* 통계 */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="rounded-lg p-3 text-center" style={{ backgroundColor: "#f5f5f5" }}>
                  <p className="text-2xl font-bold text-gray-900">{result.total_tasks}</p>
                  <p className="text-xs text-gray-500 mt-0.5">총 L5 Task</p>
                </div>
                <div className="rounded-lg p-3 text-center" style={{ backgroundColor: AUTOMATION_COLOR["Full-Auto"].bg }}>
                  <p className="text-2xl font-bold" style={{ color: AUTOMATION_COLOR["Full-Auto"].text }}>{result.full_auto_count}</p>
                  <p className="text-xs mt-0.5" style={{ color: AUTOMATION_COLOR["Full-Auto"].text }}>Full-Auto</p>
                </div>
                <div className="rounded-lg p-3 text-center" style={{ backgroundColor: AUTOMATION_COLOR["Human-in-Loop"].bg }}>
                  <p className="text-2xl font-bold" style={{ color: AUTOMATION_COLOR["Human-in-Loop"].text }}>{result.human_in_loop_count}</p>
                  <p className="text-xs mt-0.5" style={{ color: AUTOMATION_COLOR["Human-in-Loop"].text }}>Human-in-Loop</p>
                </div>
                <div className="rounded-lg p-3 text-center" style={{ backgroundColor: AUTOMATION_COLOR["Human-Supervised"].bg }}>
                  <p className="text-2xl font-bold" style={{ color: AUTOMATION_COLOR["Human-Supervised"].text }}>{result.human_supervised_count}</p>
                  <p className="text-xs mt-0.5" style={{ color: AUTOMATION_COLOR["Human-Supervised"].text }}>Human-Supervised</p>
                </div>
              </div>
            </div>

            {/* 탭 */}
            <div className="flex gap-1 mb-5 rounded-lg p-1 w-fit" style={{ backgroundColor: "#f0e0e0" }}>
              {(["agents", "flow"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className="rounded-md px-4 py-1.5 text-sm font-medium transition-colors"
                  style={
                    activeTab === tab
                      ? { backgroundColor: PWC.primary, color: "#fff" }
                      : { color: PWC.primary }
                  }
                >
                  {tab === "agents" ? `AI 에이전트 (${result.agents.length})` : "실행 플로우"}
                </button>
              ))}
            </div>

            {/* 에이전트 목록 탭 */}
            {activeTab === "agents" && (
              <div className="space-y-4">
                {result.agents.map((agent) => (
                  <AgentCard key={agent.agent_id} agent={agent} />
                ))}
              </div>
            )}

            {/* 실행 플로우 탭 */}
            {activeTab === "flow" && (
              <div className="rounded-xl p-5 shadow-sm" style={{ backgroundColor: PWC.cardBg, border: "1px solid #f0e0e0" }}>
                <h2 className="text-base font-semibold text-gray-900 mb-5">AI 워크플로우 실행 순서</h2>
                <ExecutionFlow result={result} />
              </div>
            )}
          </>
        )}

        {/* 빈 상태 */}
        {!result && !loading && (
          <div className="rounded-xl py-16 text-center" style={{ backgroundColor: PWC.cardBg, border: "1px dashed #d9a0a0" }}>
            <Sparkles className="mx-auto h-10 w-10 mb-4" style={{ color: "#d9a0a0" }} />
            <p className="text-gray-500 text-sm">
              엑셀 파일을 먼저 업로드한 뒤, &apos;AI 워크플로우 설계&apos; 버튼을 눌러주세요.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
