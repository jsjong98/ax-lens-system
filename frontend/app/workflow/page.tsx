"use client";

import { useState, useCallback, useEffect } from "react";
import {
  uploadWorkflow,
  uploadPptWorkflow,
  getWorkflowSummary,
  getFilterOptions,
  saveSlideL4Mapping,
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
  const [l4Options, setL4Options] = useState<{ id: string; name: string }[]>([]);
  const [slideL4Map, setSlideL4Map] = useState<Record<string, string>>({});

  // PPT 업로드 시 L4 목록 로드
  useEffect(() => {
    if (pptResult) {
      getFilterOptions()
        .then((opts) => setL4Options(opts.l4 || []))
        .catch(() => {});
    }
  }, [pptResult]);

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

  /* ── 슬라이드 L4 매핑 변경 ─────────────────────────────── */
  const handleSlideL4Change = useCallback(
    async (slideIdx: number, l4Id: string) => {
      const newMap = { ...slideL4Map, [String(slideIdx)]: l4Id };
      if (!l4Id) delete newMap[String(slideIdx)];
      setSlideL4Map(newMap);
      try {
        await saveSlideL4Mapping(newMap);
      } catch {}
    },
    [slideL4Map],
  );

  /* ── To-Be 생성 ────────────────────────────────────────── */
  const handleGenerateToBe = useCallback(async () => {
    setTobeLoading(true);
    setError(null);
    try {
      // PPT 모드: 현재 슬라이드의 sheet_id 사용
      const sheetId = pptResult
        ? `ppt-slide-${activePptSlide}`
        : activeSheet || undefined;
      const result = await generateToBe({
        sheet_id: sheetId,
        provider,
      });
      setTobeResult(result);
      setActiveTab("tobe");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setTobeLoading(false);
    }
  }, [activeSheet, activePptSlide, pptResult, provider]);

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

          {/* 슬라이드별 L4 매핑 테이블 */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-4 py-2 font-medium text-gray-600 w-12">#</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">슬라이드</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">노드</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600 min-w-[280px]">L4 Activity 지정</th>
                </tr>
              </thead>
              <tbody>
                {pptResult.slides.map((s, i) => (
                  <tr
                    key={i}
                    onClick={() => setActivePptSlide(i)}
                    className={`border-b border-gray-100 cursor-pointer transition ${
                      activePptSlide === i ? "bg-red-50" : "hover:bg-gray-50"
                    }`}
                  >
                    <td className="px-4 py-2 text-gray-400 font-mono">{i + 1}</td>
                    <td className="px-4 py-2 font-medium text-gray-800">
                      {s.title || `슬라이드 ${i + 1}`}
                    </td>
                    <td className="px-4 py-2 text-gray-500">{s.node_count}개</td>
                    <td className="px-4 py-2" onClick={(e) => e.stopPropagation()}>
                      <select
                        value={slideL4Map[String(i)] || ""}
                        onChange={(e) => handleSlideL4Change(i, e.target.value)}
                        className={`w-full text-xs border rounded-lg px-2 py-1.5 ${
                          slideL4Map[String(i)]
                            ? "border-green-300 bg-green-50 text-green-800"
                            : "border-gray-200 text-gray-500"
                        }`}
                      >
                        <option value="">-- L4 선택 --</option>
                        {l4Options.map((opt) => (
                          <option key={opt.id} value={opt.id}>
                            {opt.id} {opt.name}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

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

/* ── To-Be 결과 뷰 — 4-Lane Swim Lane 워크플로우 맵 ────── */
function ToBeView({ result }: { result: ToBeResult }) {
  const { summary } = result;
  const { junior_agents, human_steps, senior_agent } = summary;

  // AI 기술 대분류별 색상
  const categoryColor = (category: string) => {
    if (category.includes("생성형")) return { bg: "#FFF5F7", text: "#A62121", border: "#F2A0AF" };
    if (category.includes("판별") || category.includes("예측")) return { bg: "#EEF2FF", text: "#3730A3", border: "#C7D2FE" };
    if (category.includes("인식")) return { bg: "#ECFDF5", text: "#065F46", border: "#A7F3D0" };
    if (category.includes("의사결정") || category.includes("최적화")) return { bg: "#FFF7ED", text: "#9A3412", border: "#FDBA74" };
    if (category.includes("자동화")) return { bg: "#FEF3C7", text: "#92400E", border: "#FCD34D" };
    return { bg: "#F3F4F6", text: "#374151", border: "#D1D5DB" };
  };

  // Input source 유형별 색상
  const sourceColor = (sourceType: string) => {
    if (sourceType.includes("시스템")) return { bg: "#DBEAFE", text: "#1E40AF", border: "#93C5FD" };
    if (sourceType.includes("문서")) return { bg: "#FEF3C7", text: "#92400E", border: "#FCD34D" };
    if (sourceType.includes("외부")) return { bg: "#E0E7FF", text: "#3730A3", border: "#A5B4FC" };
    return { bg: "#F3F4F6", text: "#374151", border: "#D1D5DB" };
  };

  return (
    <div className="space-y-6">
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
        <StatCard label="Input" value={summary.input_source_count || 0} />
        <StatCard label="Junior Agent" value={summary.junior_agent_count} />
        <StatCard label="Human 스텝" value={summary.human_step_count} />
      </div>

      {/* ═══ 4-Lane Swim Lane 워크플로우 맵 ═══ */}
      <div className="overflow-x-auto">
        <div className="border border-gray-200 rounded-xl bg-white" style={{ minWidth: Math.max(junior_agents.length * 260 + 120, 600) }}>
          {/* 범례 */}
          <div className="flex items-center gap-6 px-4 py-2 border-b border-gray-100 bg-gray-50 rounded-t-xl text-[11px]">
            <span className="font-medium text-gray-500">범위</span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded" style={{ backgroundColor: "#DBEAFE", border: "1px solid #93C5FD" }} />
              Input
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded" style={{ backgroundColor: PWC.primary }} />
              Senior AI
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded" style={{ backgroundColor: "#FEF3C7", border: "1px solid #FCD34D" }} />
              Junior AI
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-gray-200 border border-gray-300" />
              Human
            </span>
          </div>

          <div className="flex">
            {/* 왼쪽 라벨 컬럼 */}
            <div className="w-[80px] flex-shrink-0 border-r border-gray-200 bg-gray-50">
              {/* L4 헤더 행 */}
              <div className="h-[56px] flex items-center justify-center border-b border-gray-200" />
              {/* Input 행 */}
              <div className="flex items-center justify-center border-b border-gray-200 py-4">
                <div className="text-center">
                  <div className="w-8 h-8 mx-auto rounded-full flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: "#3B82F6" }}>I</div>
                  <div className="text-[10px] font-bold mt-1 text-blue-600">Input</div>
                </div>
              </div>
              {/* Senior AI 행 */}
              <div className="flex items-center justify-center border-b border-gray-200 py-4">
                <div className="text-center">
                  <div className="w-8 h-8 mx-auto rounded-full flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: PWC.primary }}>S</div>
                  <div className="text-[10px] font-bold mt-1" style={{ color: PWC.primary }}>Senior</div>
                  <div className="text-[10px]" style={{ color: PWC.primary }}>AI</div>
                </div>
              </div>
              {/* Junior AI 행 */}
              <div className="flex items-center justify-center border-b border-gray-200 py-4">
                <div className="text-center">
                  <div className="w-8 h-8 mx-auto rounded-full flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: "#D97706" }}>J</div>
                  <div className="text-[10px] font-bold mt-1 text-amber-700">Junior</div>
                  <div className="text-[10px] text-amber-700">AI</div>
                </div>
              </div>
              {/* Human 행 */}
              <div className="flex items-center justify-center py-4">
                <div className="text-center">
                  <div className="text-xl">&#128100;</div>
                  <div className="text-[10px] font-bold text-gray-600">Human</div>
                </div>
              </div>
            </div>

            {/* Agent 컬럼들 */}
            <div className="flex flex-1 divide-x divide-gray-200">
              {junior_agents.map((agent, agentIdx) => {
                // 이 agent에 대응하는 human steps 찾기
                const agentTaskIds = new Set(agent.tasks.map((t) => t.task_id));
                const relatedHumans = human_steps.filter((h) => {
                  const hPrefix = h.label.split(" ")[0];
                  return agentTaskIds.has(hPrefix) ||
                    agent.tasks.some((t) => {
                      const tp = t.task_id.split(".").slice(0, 3).join(".");
                      return h.label.includes(tp);
                    });
                });

                // Agent의 Input Sources
                const agentInputs = agent.input_sources || [];

                return (
                  <div key={agent.id} className="flex-1 min-w-[240px]">
                    {/* L4 헤더 */}
                    <div className="h-[56px] flex items-center justify-center px-3 border-b border-gray-200 bg-gray-50">
                      <div className="text-center">
                        <div className="text-xs font-bold text-gray-800">
                          {agent.name.replace(/^Agent \d+:\s*/, "").split(" 외")[0]}
                        </div>
                        <div className="text-[10px] text-gray-400">
                          Agent {agentIdx + 1}
                          {agent.task_count > 1 && ` · ${agent.task_count}개 태스크`}
                        </div>
                      </div>
                    </div>

                    {/* Input 행 */}
                    <div className="flex items-center justify-center border-b border-gray-200 py-3 px-3 min-h-[60px]">
                      {agentInputs.length > 0 ? (
                        <div className="space-y-1.5 w-full">
                          {agentInputs.map((src, si) => {
                            const sc = sourceColor(src.source_type);
                            return (
                              <div key={src.id || si} className="rounded-lg border px-2.5 py-1.5 text-center"
                                style={{ backgroundColor: sc.bg, borderColor: sc.border }}>
                                <div className="text-[10px] font-medium" style={{ color: sc.text }}>{src.name}</div>
                                {src.source_type && (
                                  <div className="text-[9px] mt-0.5 opacity-70" style={{ color: sc.text }}>{src.source_type}</div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <span className="text-gray-300 text-sm">—</span>
                      )}
                    </div>

                    {/* Senior AI 기동 지시 */}
                    <div className="flex items-center justify-center border-b border-gray-200 py-4 px-3">
                      <div className="rounded-lg px-3 py-2 text-center text-xs w-full" style={{ backgroundColor: "#FFF5F7", border: `1px solid ${PWC.primaryLight}` }}>
                        <div className="font-bold" style={{ color: PWC.primary }}>
                          Agent {agentIdx + 1} 기동 지시
                        </div>
                        {agent.ai_tech_category && (
                          <div className="text-[10px] mt-1">
                            <span className="px-1.5 py-0.5 rounded-full border font-medium"
                              style={categoryColor(agent.ai_tech_category)}>
                              {agent.ai_tech_category}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Junior AI 태스크 그룹 */}
                    <div className="border-b border-gray-200 py-4 px-3">
                      <div className="rounded-lg border-2 p-3" style={{ backgroundColor: "#FFFBEB", borderColor: "#FCD34D" }}>
                        {/* Agent 헤더 */}
                        <div className="flex items-center justify-between mb-3 pb-2 border-b border-amber-200">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-amber-800">Agent {agentIdx + 1}</span>
                            {agent.task_count > 1 && (
                              <span className="text-[10px] text-amber-600">순차 파이프라인</span>
                            )}
                          </div>
                        </div>

                        {/* L5 태스크 목록 */}
                        <div className="space-y-2">
                          {agent.tasks.map((task, ti) => {
                            const taskCategory = task.ai_tech_category || agent.ai_tech_category || "";
                            const taskType = task.ai_tech_type || agent.ai_tech_type || "";
                            const technique = task.technique || agent.technique || "";
                            const cc = categoryColor(taskCategory);

                            return (
                              <div key={`${task.task_id}-${ti}`}>
                                <div className="rounded-lg bg-white border border-gray-200 px-3 py-2">
                                  <div className="text-[11px] font-mono text-gray-400 mb-0.5">{task.task_id}</div>
                                  <div className="text-xs font-medium text-gray-800 mb-1.5">{task.label}</div>
                                  <div className="flex flex-wrap gap-1">
                                    {taskCategory && (
                                      <span className="text-[9px] px-1.5 py-0.5 rounded-full border font-medium"
                                        style={{ backgroundColor: cc.bg, color: cc.text, borderColor: cc.border }}>
                                        {taskCategory}
                                      </span>
                                    )}
                                    {taskType && (
                                      <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600 border border-gray-200 font-medium">
                                        {taskType}
                                      </span>
                                    )}
                                    {technique && (
                                      <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-white text-gray-500 border border-gray-200">
                                        {technique}
                                      </span>
                                    )}
                                  </div>
                                </div>
                                {/* 순차 화살표 */}
                                {ti < agent.tasks.length - 1 && (
                                  <div className="flex justify-center py-1">
                                    <span className="text-gray-300 text-sm">&#8595;</span>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>

                    {/* Human 행 */}
                    <div className="py-4 px-3 flex items-center justify-center min-h-[60px]">
                      {relatedHumans.length > 0 ? (
                        <div className="space-y-2 w-full">
                          {relatedHumans.map((h) => (
                            <div key={h.id} className="rounded-lg bg-gray-100 border border-gray-300 px-3 py-2 text-center">
                              <div className="text-xs font-medium text-gray-700">{h.label}</div>
                              {h.is_hybrid_part && (
                                <div className="text-[10px] text-orange-600 mt-0.5">AI+Human 분할</div>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <span className="text-gray-300 text-sm">—</span>
                      )}
                    </div>
                  </div>
                );
              })}

              {/* 독립 Human 스텝 컬럼 */}
              {human_steps.length > 0 && (
                <div className="flex-1 min-w-[220px]">
                  <div className="h-[56px] flex items-center justify-center px-3 border-b border-gray-200 bg-gray-50">
                    <div className="text-xs font-bold text-gray-600">인간 수행 영역</div>
                  </div>
                  <div className="flex items-center justify-center border-b border-gray-200 py-3 px-3 min-h-[60px]">
                    <span className="text-gray-300 text-sm">—</span>
                  </div>
                  <div className="flex items-center justify-center border-b border-gray-200 py-4 px-3">
                    <span className="text-gray-300 text-sm">—</span>
                  </div>
                  <div className="flex items-center justify-center border-b border-gray-200 py-4 px-3">
                    <span className="text-gray-300 text-sm">—</span>
                  </div>
                  <div className="py-4 px-3">
                    <div className="space-y-2">
                      {human_steps.map((h) => (
                        <div key={h.id} className="rounded-lg bg-gray-100 border border-gray-300 px-3 py-2 text-center">
                          <div className="text-xs font-medium text-gray-700">{h.label}</div>
                          {h.reason && <div className="text-[10px] text-gray-500 mt-0.5">{h.reason}</div>}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Senior Agent 설명 */}
      <div className="bg-white rounded-xl border-2 p-4" style={{ borderColor: PWC.primary }}>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: PWC.primary }}>S</div>
          <div>
            <div className="text-sm font-bold" style={{ color: PWC.primary }}>{senior_agent.name}</div>
            <div className="text-xs text-gray-500">{senior_agent.description}</div>
          </div>
        </div>
      </div>

      {/* AI 기술 유형 범례 */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="text-xs font-bold text-gray-700 mb-3">AI 기술 유형 분류</div>
        <div className="grid grid-cols-5 gap-2 text-[10px]">
          {[
            { label: "생성형 모델", sub: "텍스트 생성 / 요약·QA / 멀티모달 / 정보 추출" },
            { label: "판별·예측 모델", sub: "예측 / 군집·분류 / 추천·랭킹" },
            { label: "인식 모델", sub: "OCR / 음성 인식" },
            { label: "의사결정·최적화", sub: "최적화" },
            { label: "자동화", sub: "RPA" },
          ].map((item) => {
            const cc = categoryColor(item.label);
            return (
              <div key={item.label} className="rounded-lg border px-2 py-1.5"
                style={{ backgroundColor: cc.bg, borderColor: cc.border }}>
                <div className="font-bold" style={{ color: cc.text }}>{item.label}</div>
                <div className="mt-0.5 opacity-70" style={{ color: cc.text }}>{item.sub}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* To-Be JSON 다운로드 */}
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
