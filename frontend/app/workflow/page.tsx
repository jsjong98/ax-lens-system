"use client";

import { useState, useCallback } from "react";
import {
  uploadWorkflow,
  uploadPptWorkflow,
  getWorkflowSummary,
  generateToBe,
  type WorkflowSummary,
  type WorkflowStep,
  type ToBeResult,
  type ProviderType,
} from "@/lib/api";

/* ── 색상 ─────────────────────────────────────────────────── */
const PWC = {
  primary: "#A62121",
  primaryLight: "#D95578",
  bg: "#FFF5F7",
  cardBg: "#FFFFFF",
};

export default function WorkflowPage() {
  const [summary, setSummary] = useState<WorkflowSummary | null>(null);
  const [pptResult, setPptResult] = useState<Awaited<ReturnType<typeof uploadPptWorkflow>> | null>(null);
  const [tobeResult, setTobeResult] = useState<ToBeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [tobeLoading, setTobeLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeSheet, setActiveSheet] = useState<string | null>(null);
  const [activePptSlide, setActivePptSlide] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const [activeTab, setActiveTab] = useState<"asis" | "tobe">("asis");
  const [provider, setProvider] = useState<ProviderType>("openai");

  /* ── JSON 업로드 ───────────────────────────────────────── */
  const handleUpload = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);
    setPptResult(null);
    setTobeResult(null);
    try {
      if (file.name.endsWith(".pptx") || file.name.endsWith(".ppt")) {
        const result = await uploadPptWorkflow(file);
        setPptResult(result);
        setSummary(null);
      } else {
        const result = await uploadWorkflow(file);
        setSummary(result);
        if (result.sheets.length > 0) setActiveSheet(result.sheets[0].sheet_id);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  const handleLoadExisting = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getWorkflowSummary();
      setSummary(result);
      if (result.sheets.length > 0) setActiveSheet(result.sheets[0].sheet_id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  /* ── To-Be 생성 ────────────────────────────────────────── */
  const handleGenerateToBe = useCallback(async () => {
    setTobeLoading(true);
    setError(null);
    try {
      const result = await generateToBe({
        sheet_id: activeSheet || undefined,
        provider,
      });
      setTobeResult(result);
      setActiveTab("tobe");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setTobeLoading(false);
    }
  }, [activeSheet, provider]);

  const currentSheet = summary?.sheets.find((s) => s.sheet_id === activeSheet);
  const hasWorkflow = summary || pptResult;

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: PWC.primary }}>
            Workflow 분석
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            As-Is Workflow를 업로드하고, 분류 결과를 기반으로 To-Be Workflow 초안을 생성합니다.
          </p>
        </div>
        {hasWorkflow && (
          <div className="flex items-center gap-2">
            {/* As-Is / To-Be 탭 */}
            <div className="flex rounded-lg border border-gray-200 overflow-hidden">
              <button
                onClick={() => setActiveTab("asis")}
                className={`px-4 py-2 text-sm font-medium transition ${
                  activeTab === "asis"
                    ? "bg-gray-800 text-white"
                    : "bg-white text-gray-600 hover:bg-gray-50"
                }`}
              >
                As-Is
              </button>
              <button
                onClick={() => setActiveTab("tobe")}
                className={`px-4 py-2 text-sm font-medium transition ${
                  activeTab === "tobe"
                    ? "text-white"
                    : "bg-white text-gray-600 hover:bg-gray-50"
                }`}
                style={activeTab === "tobe" ? { backgroundColor: PWC.primary } : undefined}
              >
                To-Be
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 업로드 영역 */}
      {!hasWorkflow && (
        <div className="flex gap-4">
          <div
            className={`flex-1 border-2 border-dashed rounded-xl p-10 text-center transition-colors cursor-pointer ${
              dragOver ? "border-red-400 bg-red-50" : "border-gray-300 bg-white"
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => document.getElementById("wf-file-input")?.click()}
          >
            <input
              id="wf-file-input"
              type="file"
              accept=".json,.pptx,.ppt"
              className="hidden"
              onChange={handleFileChange}
            />
            <div className="text-4xl mb-3">&#128230;</div>
            <p className="text-sm font-medium text-gray-700">
              워크플로우 파일을 드래그하거나 클릭하여 업로드
            </p>
            <p className="text-xs text-gray-400 mt-1">
              JSON (.json) 또는 PPT (.pptx) 파일
            </p>
          </div>
          <button
            onClick={handleLoadExisting}
            className="px-6 py-3 rounded-xl border-2 border-gray-300 bg-white text-sm font-medium text-gray-600 hover:border-red-300 hover:bg-red-50 transition self-start"
          >
            기존 워크플로우 불러오기
          </button>
        </div>
      )}

      {loading && (
        <div className="text-center py-10">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-red-200 border-t-red-600" />
          <p className="mt-2 text-sm text-gray-500">파싱 중...</p>
        </div>
      )}

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* ═══ As-Is 탭 ═══ */}
      {activeTab === "asis" && summary && (
        <>
          <div className="flex items-center justify-between">
            <div className="flex gap-3 flex-wrap">
              <StatCard label="시트 수" value={summary.sheet_count} />
              {currentSheet && (
                <>
                  <StatCard label="L4 (Activity)" value={currentSheet.l4_count} />
                  <StatCard label="L5 (Task)" value={currentSheet.l5_count} />
                  <StatCard label="총 스텝" value={currentSheet.total_steps} />
                  <StatCard label="병렬 스텝" value={currentSheet.parallel_steps} accent />
                  <StatCard label="순차 스텝" value={currentSheet.sequential_steps} />
                </>
              )}
            </div>
            <div className="flex items-center gap-2">
              {/* To-Be 생성 버튼 */}
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value as ProviderType)}
                className="text-xs border border-gray-200 rounded-lg px-2 py-2"
              >
                <option value="openai">Model A 기준</option>
                <option value="anthropic">Model B 기준</option>
              </select>
              <button
                onClick={handleGenerateToBe}
                disabled={tobeLoading}
                className="px-4 py-2 rounded-lg text-sm font-bold text-white transition disabled:opacity-50"
                style={{ backgroundColor: PWC.primary }}
              >
                {tobeLoading ? "생성 중..." : "To-Be 초안 생성"}
              </button>
              <button
                onClick={() => { setSummary(null); setPptResult(null); setActiveSheet(null); setTobeResult(null); }}
                className="text-sm text-gray-400 hover:text-red-500 transition"
              >
                초기화
              </button>
            </div>
          </div>

          {summary.sheets.length > 1 && (
            <div className="flex gap-1 border-b border-gray-200">
              {summary.sheets.map((s) => (
                <button
                  key={s.sheet_id}
                  onClick={() => setActiveSheet(s.sheet_id)}
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                    activeSheet === s.sheet_id
                      ? "border-red-600 text-red-700"
                      : "border-transparent text-gray-500 hover:text-gray-700"
                  }`}
                >
                  {s.sheet_name || s.sheet_id}
                </button>
              ))}
            </div>
          )}

          {currentSheet && (
            <div className="space-y-6">
              <h2 className="text-lg font-bold text-gray-800">
                실행 순서 — {currentSheet.sheet_name}
              </h2>
              <ExecutionOrderView steps={currentSheet.execution_order} />

              <h2 className="text-lg font-bold text-gray-800 mt-8">L4 Activity 상세</h2>
              <div className="space-y-3">
                {currentSheet.l4_details.map((l4) => (
                  <div key={l4.node_id} className="bg-white rounded-lg border border-gray-200 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs font-mono px-2 py-0.5 rounded" style={{ backgroundColor: "#FFF5F7", color: PWC.primary }}>
                        {l4.task_id}
                      </span>
                      <span className="font-semibold text-sm">{l4.label}</span>
                      {l4.description && <span className="text-xs text-gray-400">— {l4.description}</span>}
                    </div>
                    {l4.child_l5s.length > 0 && (
                      <div className="ml-4 mt-2 space-y-1">
                        {l4.child_l5s.map((l5, i) => (
                          <div key={l5.node_id || i} className="flex items-center gap-2 text-xs text-gray-600">
                            <span className="w-1.5 h-1.5 rounded-full bg-gray-300" />
                            <span className="font-mono text-gray-400">{l5.task_id}</span>
                            <span>{l5.label}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* ═══ As-Is PPT 결과 ═══ */}
      {activeTab === "asis" && pptResult && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex gap-3">
              <StatCard label="슬라이드" value={pptResult.slide_count} />
              {pptResult.slides[activePptSlide] && (
                <>
                  <StatCard label="노드" value={pptResult.slides[activePptSlide].node_count} />
                  <StatCard label="엣지" value={pptResult.slides[activePptSlide].edge_count} />
                  <StatCard
                    label="매칭됨"
                    value={pptResult.slides[activePptSlide].matches.filter((m) => m.matched_task_id).length}
                    accent
                  />
                </>
              )}
            </div>
            <div className="flex items-center gap-2">
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value as ProviderType)}
                className="text-xs border border-gray-200 rounded-lg px-2 py-2"
              >
                <option value="openai">Model A 기준</option>
                <option value="anthropic">Model B 기준</option>
              </select>
              <button
                onClick={handleGenerateToBe}
                disabled={tobeLoading}
                className="px-4 py-2 rounded-lg text-sm font-bold text-white transition disabled:opacity-50"
                style={{ backgroundColor: PWC.primary }}
              >
                {tobeLoading ? "생성 중..." : "To-Be 초안 생성"}
              </button>
              <button
                onClick={() => { setPptResult(null); setSummary(null); setTobeResult(null); }}
                className="text-sm text-gray-400 hover:text-red-500 transition"
              >
                초기화
              </button>
            </div>
          </div>

          {/* 슬라이드 탭 */}
          {pptResult.slides.length > 1 && (
            <div className="flex gap-1 border-b border-gray-200">
              {pptResult.slides.map((s, i) => (
                <button
                  key={i}
                  onClick={() => setActivePptSlide(i)}
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                    activePptSlide === i
                      ? "border-red-600 text-red-700"
                      : "border-transparent text-gray-500 hover:text-gray-700"
                  }`}
                >
                  {s.title || `슬라이드 ${i + 1}`}
                </button>
              ))}
            </div>
          )}

          {/* PPT 노드 매칭 결과 */}
          {pptResult.slides[activePptSlide] && (
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-gray-800">
                노드-태스크 매칭 — {pptResult.slides[activePptSlide].title || `슬라이드 ${activePptSlide + 1}`}
              </h2>
              <div className="space-y-2">
                {pptResult.slides[activePptSlide].matches.map((m, i) => (
                  <div
                    key={i}
                    className={`bg-white rounded-lg border p-3 flex items-center justify-between ${
                      m.matched_task_id ? "border-green-200" : "border-gray-200"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-gray-800 max-w-[300px] truncate">
                        {m.node_text}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {m.matched_task_id ? (
                        <>
                          <span className="text-xs font-mono px-2 py-0.5 rounded bg-green-50 text-green-700">
                            {m.matched_task_id}
                          </span>
                          <span className="text-xs text-gray-500">{m.matched_task_name}</span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700">
                            {Math.round(m.match_confidence * 100)}%
                          </span>
                        </>
                      ) : (
                        <span className="text-xs text-gray-400">매칭 없음</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ═══ To-Be 탭 ═══ */}
      {activeTab === "tobe" && tobeResult && (
        <ToBeView result={tobeResult} />
      )}

      {activeTab === "tobe" && !tobeResult && (
        <div className="text-center py-16 text-gray-400">
          <div className="text-5xl mb-4">&#9881;</div>
          <p className="text-sm">As-Is 탭에서 &ldquo;To-Be 초안 생성&rdquo; 버튼을 눌러주세요.</p>
          <p className="text-xs mt-1">분류 결과가 필요합니다. 먼저 분류를 실행하세요.</p>
        </div>
      )}
    </div>
  );
}

/* ── To-Be 결과 뷰 ────────────────────────────────────────── */
function ToBeView({ result }: { result: ToBeResult }) {
  const { summary, execution_steps } = result;

  return (
    <div className="space-y-8">
      {/* 요약 카드 */}
      <div className="flex gap-3 flex-wrap">
        <StatCard label="전체 태스크" value={summary.total_tasks} />
        <StatCard label="AI 수행" value={summary.ai_tasks} />
        <StatCard label="AI+Human" value={summary.hybrid_tasks} accent />
        <StatCard label="인간 수행" value={summary.human_tasks} />
        <div className="rounded-lg border px-4 py-3 min-w-[120px]" style={{ backgroundColor: "#FFF5F7", borderColor: PWC.primaryLight }}>
          <div className="text-xs text-gray-500">자동화율</div>
          <div className="text-xl font-bold" style={{ color: PWC.primary }}>{summary.automation_rate}%</div>
        </div>
        <StatCard label="Junior Agent" value={summary.junior_agent_count} />
        <StatCard label="Human 스텝" value={summary.human_step_count} />
      </div>

      {/* Senior Agent */}
      <div className="bg-white rounded-xl border-2 p-5" style={{ borderColor: PWC.primary }}>
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: PWC.primary }}>
            S
          </div>
          <div>
            <div className="text-sm font-bold" style={{ color: PWC.primary }}>{summary.senior_agent.name}</div>
            <div className="text-xs text-gray-500">{summary.senior_agent.description}</div>
          </div>
        </div>

        {/* Junior Agents */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mt-4">
          {summary.junior_agents.map((agent) => (
            <div key={agent.id} className="rounded-lg border border-gray-200 p-3 bg-gray-50">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-full flex items-center justify-center text-white text-[10px] font-bold" style={{ backgroundColor: PWC.primaryLight }}>
                  J
                </div>
                <span className="text-sm font-semibold text-gray-800">{agent.name}</span>
              </div>
              <div className="text-[10px] px-2 py-0.5 rounded bg-blue-50 text-blue-700 inline-block mb-2">
                {agent.technique}
              </div>
              <div className="space-y-1">
                {agent.tasks.map((t) => (
                  <div key={t.task_id} className="text-xs text-gray-600 flex items-center gap-1.5">
                    <span className="w-1 h-1 rounded-full bg-gray-400" />
                    <span className="font-mono text-gray-400">{t.task_id}</span>
                    <span>{t.label}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Human Steps */}
        {summary.human_steps.length > 0 && (
          <div className="mt-4">
            <h4 className="text-xs font-bold text-gray-500 uppercase mb-2">Human 스텝</h4>
            <div className="space-y-2">
              {summary.human_steps.map((h) => (
                <div key={h.id} className="flex items-center gap-3 bg-amber-50 rounded-lg px-3 py-2 border border-amber-200">
                  <div className="w-6 h-6 rounded-full bg-amber-500 flex items-center justify-center text-white text-[10px] font-bold">
                    H
                  </div>
                  <span className="text-sm text-gray-800">{h.label}</span>
                  {h.is_hybrid_part && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-200 text-amber-800">
                      AI+Human 분할
                    </span>
                  )}
                  {h.reason && <span className="text-xs text-gray-400">— {h.reason}</span>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 실행 순서 */}
      <div>
        <h2 className="text-lg font-bold text-gray-800 mb-4">To-Be 실행 순서</h2>
        <div className="relative">
          {execution_steps.map((step, idx) => (
            <div key={step.step} className="flex items-start gap-4 mb-3">
              <div className="flex flex-col items-center w-10 shrink-0">
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white"
                  style={{ backgroundColor: step.is_parallel ? PWC.primaryLight : PWC.primary }}
                >
                  {step.step}
                </div>
                {idx < execution_steps.length - 1 && (
                  <div className="w-0.5 flex-1 min-h-[20px] bg-gray-200" />
                )}
              </div>

              <div className={`flex-1 flex gap-2 ${step.is_parallel ? "flex-row" : "flex-col"}`}>
                {step.is_parallel && (
                  <div className="self-center text-[10px] font-bold text-white px-2 py-0.5 rounded-full mr-1" style={{ backgroundColor: PWC.primaryLight }}>
                    병렬
                  </div>
                )}
                {step.actors.map((actor, ai) => (
                  <div
                    key={ai}
                    className="bg-white border rounded-lg px-4 py-2.5 flex items-center gap-3 shadow-sm"
                    style={{
                      borderColor: actor.type === "junior_ai" ? PWC.primaryLight : "#F59E0B",
                      borderLeftWidth: 3,
                    }}
                  >
                    <div
                      className="w-6 h-6 rounded-full flex items-center justify-center text-white text-[10px] font-bold shrink-0"
                      style={{ backgroundColor: actor.type === "junior_ai" ? PWC.primaryLight : "#F59E0B" }}
                    >
                      {actor.type === "junior_ai" ? "J" : "H"}
                    </div>
                    <div>
                      <div className="text-sm font-medium text-gray-800">
                        {actor.agent_name || actor.label}
                      </div>
                      {actor.technique && (
                        <div className="text-[10px] text-gray-400">{actor.technique}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* React Flow JSON 다운로드 */}
      <div className="flex gap-2">
        <button
          onClick={() => {
            const blob = new Blob(
              [JSON.stringify(result.react_flow, null, 2)],
              { type: "application/json" }
            );
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "tobe-workflow.json";
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="px-4 py-2 rounded-lg text-sm font-medium text-white transition"
          style={{ backgroundColor: PWC.primary }}
        >
          To-Be JSON 다운로드
        </button>
        <span className="self-center text-xs text-gray-400">
          hr-workflow-ai에서 불러올 수 있는 React Flow 형식
        </span>
      </div>
    </div>
  );
}

/* ── 통계 카드 ─────────────────────────────────────────────── */
function StatCard({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div
      className="rounded-lg border px-4 py-3 min-w-[100px]"
      style={{
        backgroundColor: accent ? "#FFF5F7" : PWC.cardBg,
        borderColor: accent ? PWC.primaryLight : "#E5E7EB",
      }}
    >
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-xl font-bold mt-0.5" style={{ color: accent ? PWC.primary : "#1F2937" }}>
        {value}
      </div>
    </div>
  );
}

/* ── 실행 순서 시각화 ──────────────────────────────────────── */
function ExecutionOrderView({ steps }: { steps: WorkflowStep[] }) {
  if (steps.length === 0) {
    return <div className="text-sm text-gray-400 py-6 text-center">실행 순서 정보가 없습니다.</div>;
  }

  return (
    <div className="relative">
      {steps.map((step, idx) => {
        const nodes = step.nodes || step.tasks || [];
        const isParallel = step.is_parallel ?? step.type === "병렬";

        return (
          <div key={step.step} className="flex items-start gap-4 mb-2">
            <div className="flex flex-col items-center w-10 shrink-0">
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white"
                style={{ backgroundColor: isParallel ? PWC.primaryLight : PWC.primary }}
              >
                {step.step}
              </div>
              {idx < steps.length - 1 && (
                <div className="w-0.5 flex-1 min-h-[20px]" style={{ backgroundColor: "#E5E7EB" }} />
              )}
            </div>
            <div className={`flex-1 flex gap-2 ${isParallel ? "flex-row" : "flex-col"}`}>
              {isParallel && (
                <div className="self-center text-[10px] font-bold text-white px-2 py-0.5 rounded-full mr-1" style={{ backgroundColor: PWC.primaryLight }}>
                  병렬
                </div>
              )}
              {nodes.map((node, ni) => (
                <div
                  key={node.node_id || ni}
                  className="bg-white border border-gray-200 rounded-lg px-4 py-2.5 flex items-center gap-3 shadow-sm"
                  style={isParallel ? { borderLeft: `3px solid ${PWC.primaryLight}` } : {}}
                >
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded" style={{ backgroundColor: "#FFF5F7", color: PWC.primary }}>
                    {node.task_id || node.label}
                  </span>
                  <span className="text-sm font-medium text-gray-800">{node.label}</span>
                  {node.level && <span className="text-[10px] text-gray-400">{node.level}</span>}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
