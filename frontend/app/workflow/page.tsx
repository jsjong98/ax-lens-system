"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import {
  uploadWorkflow,
  uploadPptWorkflow,
  uploadWorkflowExcel,
  selectWorkflowExcelSheet,
  getWorkflowExcelTasks,
  getWorkflowSummary,
  benchmarkWorkflowStep1,
  generateWorkflowStep1,
  chatWorkflowStep1,
  generateWorkflowStep2,
  getWorkflowStepResults,
  type WorkflowSummary,
  type WorkflowExcelTask,
  type WorkflowExcelUploadResult,
  type WorkflowStepResult,
  type BenchmarkTableRow,
} from "@/lib/api";
import WorkflowEditor from "@/components/WorkflowEditor";
import ToBeWorkflowModal from "@/components/ToBeWorkflowModal";
import MappingCheckPanel from "@/components/MappingCheckPanel";

/* ── 색상 ─────────────────────────────────────────────────── */
const PWC = {
  primary: "#A62121",
  primaryLight: "#D95578",
  bg: "#FFF5F7",
  cardBg: "#FFFFFF",
};

/* ── 스텝 정의 ─────────────────────────────────────────────── */
type DesignStep = 0 | 1 | 2 | 3; // 0: 엑셀, 1: As-Is, 2: Step1, 3: Step2

const STEP_LABELS: Record<DesignStep, string> = {
  0: "엑셀 업로드",
  1: "As-Is 워크플로우",
  2: "Step 1: 기본 설계",
  3: "Step 2: 상세 설계",
};

/* ══════════════════════════════════════════════════════════════════════════ */

export default function WorkflowPage() {
  // 현재 디자인 스텝
  const [currentStep, setCurrentStep] = useState<DesignStep>(0);

  // Step 0: 엑셀 업로드
  const [excelResult, setExcelResult] = useState<WorkflowExcelUploadResult | null>(null);
  const [excelTasks, setExcelTasks] = useState<WorkflowExcelTask[]>([]);
  const [excelSheets, setExcelSheets] = useState<Array<{ name: string; recommended: boolean; row_count: number; l5_count: number }>>([]);
  const [selectedExcelSheet, setSelectedExcelSheet] = useState("");

  // Step 1: As-Is Workflow
  const [summary, setSummary] = useState<WorkflowSummary | null>(null);
  const [pptResult, setPptResult] = useState<Awaited<ReturnType<typeof uploadPptWorkflow>> | null>(null);
  const [activeSheet, setActiveSheet] = useState<string | null>(null);
  const [activePptSlide, setActivePptSlide] = useState(0);

  // Step 2: Step 1 기본 설계
  const [step1Result, setStep1Result] = useState<WorkflowStepResult | null>(null);
  const [chatMessages, setChatMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [chatInput, setChatInput] = useState("");
  const [benchmarkTable, setBenchmarkTable] = useState<BenchmarkTableRow[]>([]);
  const [benchmarkSummary, setBenchmarkSummary] = useState("");
  const [bmLoading, setBmLoading] = useState(false);

  // Step 3: Step 2 상세 설계
  const [step2Result, setStep2Result] = useState<WorkflowStepResult | null>(null);
  const [showToBeModal, setShowToBeModal] = useState(false);

  // 공통
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // 이전 상태 복원
  useEffect(() => {
    getWorkflowStepResults()
      .then((r) => {
        if (r.has_step2 && r.step2) {
          setStep2Result(r.step2);
        }
        if (r.has_step1 && r.step1) {
          setStep1Result(r.step1);
          setChatMessages(r.chat_history || []);
        }
        if (r.has_excel) {
          // 엑셀 로드되어 있음 표시
          getWorkflowExcelTasks()
            .then((et) => {
              if (et.total > 0) {
                setExcelTasks(et.tasks);
                setExcelResult({
                  ok: true,
                  filename: "이전 업로드",
                  task_count: et.total,
                  has_classification: et.classified > 0,
                  classified_count: et.classified,
                  sheets: [],
                });
              }
            })
            .catch(() => {});
        }
        if (r.has_asis) {
          getWorkflowSummary()
            .then((ws) => {
              setSummary(ws);
              if (ws.sheets.length > 0) setActiveSheet(ws.sheets[0].sheet_id);
            })
            .catch(() => {});
        }
      })
      .catch(() => {});
  }, []);

  /* ── Step 0: 엑셀 업로드 ───────────────────────────────── */
  const handleExcelUpload = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);
    try {
      const result = await uploadWorkflowExcel(file);
      setExcelResult(result);
      setExcelSheets(result.sheets);
      // Task 로드
      const tasks = await getWorkflowExcelTasks();
      setExcelTasks(tasks.tasks);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleExcelSheetSelect = useCallback(async (sheetName: string) => {
    setSelectedExcelSheet(sheetName);
    setLoading(true);
    try {
      await selectWorkflowExcelSheet(sheetName);
      const tasks = await getWorkflowExcelTasks();
      setExcelTasks(tasks.tasks);
      setExcelResult((prev) => prev ? { ...prev, task_count: tasks.total, classified_count: tasks.classified, has_classification: tasks.classified > 0 } : null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  /* ── Step 1: As-Is 워크플로우 업로드 ──────────────────── */
  const handleAsIsUpload = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);
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

  /* ── Step 2: 벤치마킹 ───────────────────────────────────── */
  const handleBenchmark = useCallback(async (companies?: string) => {
    setBmLoading(true);
    setError(null);
    setChatMessages((prev) => [
      ...prev,
      { role: "system", content: `벤치마킹 수행 중...${companies ? ` (기업: ${companies})` : " (Big Tech / Industry 선도사)"}` },
    ]);
    try {
      const result = await benchmarkWorkflowStep1({ companies, sheet_id: activeSheet ?? undefined });
      setBenchmarkTable(result.benchmark_table);
      setBenchmarkSummary(result.summary);
      setChatMessages((prev) => [
        ...prev.filter((m) => m.content !== `벤치마킹 수행 중...${companies ? ` (기업: ${companies})` : " (Big Tech / Industry 선도사)"}`),
        { role: "assistant", content: `[벤치마킹 완료] ${result.result_count}개 사례 수집\n\n${result.summary}` },
      ]);
    } catch (e) {
      setError((e as Error).message);
      setChatMessages((prev) => prev.filter((m) => !m.content.startsWith("벤치마킹 수행 중")));
    } finally {
      setBmLoading(false);
    }
  }, []);

  /* ── Step 2: Step 1 기본 설계 생성 + 채팅 ──────────────── */
  const handleGenerateStep1 = useCallback(async (prompt?: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await generateWorkflowStep1({
        prompt: prompt || "선도사례를 분석하여 To-Be Workflow 기본 설계를 수행해주세요.",
        ...(activeSheet ? { sheet_id: activeSheet } : {}),
      });
      setStep1Result(result);
      setChatMessages((prev) => [
        ...prev,
        { role: "user", content: prompt || "선도사례를 분석하여 To-Be Workflow 기본 설계를 수행해주세요." },
        { role: "assistant", content: `기본 설계가 완료되었습니다.\n\n${result.blueprint_summary || ""}` },
      ]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleChat = useCallback(async () => {
    if (!chatInput.trim()) return;
    const msg = chatInput;
    setChatInput("");
    setChatMessages((prev) => [...prev, { role: "user", content: msg }]);
    setLoading(true);
    try {
      const result = await chatWorkflowStep1(msg, activeSheet ?? undefined);
      setChatMessages((prev) => [...prev, { role: "assistant", content: result.message }]);
      if (result.updated && result.result) {
        setStep1Result(result.result);
      }
      if (result.benchmark_table && result.benchmark_table.length > 0) {
        setBenchmarkTable(result.benchmark_table);
      }
    } catch (e) {
      setChatMessages((prev) => [...prev, { role: "assistant", content: `오류: ${(e as Error).message}` }]);
    } finally {
      setLoading(false);
    }
  }, [chatInput]);

  /* ── Step 3: Step 2 상세 설계 생성 ──────────────────────── */
  const handleGenerateStep2 = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await generateWorkflowStep2({
        ...(activeSheet ? { sheet_id: activeSheet } : {}),
      });
      setStep2Result(result);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  const hasAsIs = summary || pptResult;
  const currentSheet = summary?.sheets.find((s) => s.sheet_id === activeSheet);

  return (
    <div className="space-y-6">
      {/* ═══ 헤더 + 스텝 네비게이션 ═══ */}
      <div>
        <h1 className="text-2xl font-bold" style={{ color: PWC.primary }}>
          Workflow 설계
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          엑셀 업로드 → As-Is 워크플로우 연결 → 벤치마킹 기본 설계 → 상세 설계
        </p>
      </div>

      {/* 스텝 인디케이터 */}
      <div className="flex items-center gap-1">
        {([0, 1, 2, 3] as DesignStep[]).map((step) => {
          const isActive = currentStep === step;
          const isDone =
            (step === 0 && excelResult) ||
            (step === 1 && hasAsIs) ||
            (step === 2 && step1Result) ||
            (step === 3 && step2Result);
          return (
            <button
              key={step}
              onClick={() => setCurrentStep(step)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition ${
                isActive
                  ? "text-white shadow-md"
                  : isDone
                  ? "bg-green-50 text-green-700 border border-green-200"
                  : "bg-gray-50 text-gray-400 border border-gray-200"
              }`}
              style={isActive ? { backgroundColor: PWC.primary } : undefined}
            >
              <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                isActive ? "bg-white/20 text-white" : isDone ? "bg-green-200 text-green-800" : "bg-gray-200 text-gray-500"
              }`}>
                {isDone && !isActive ? "\u2713" : step + 1}
              </span>
              {STEP_LABELS[step]}
            </button>
          );
        })}
      </div>

      {/* 에러 */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">닫기</button>
        </div>
      )}

      {/* ═══ Step 0: 엑셀 업로드 ═══ */}
      {currentStep === 0 && (
        <div className="space-y-6">
          {!excelResult ? (
            <div
              className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors cursor-pointer ${
                dragOver ? "border-red-400 bg-red-50" : "border-gray-300 bg-white"
              }`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                const file = e.dataTransfer.files[0];
                if (file) handleExcelUpload(file);
              }}
              onClick={() => document.getElementById("wf-excel-input")?.click()}
            >
              <input
                id="wf-excel-input"
                type="file"
                accept=".xlsx,.xls"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleExcelUpload(file);
                }}
              />
              <div className="text-4xl mb-3">&#128196;</div>
              <p className="text-sm font-medium text-gray-700">
                분류 결과가 포함된 엑셀 파일을 업로드하세요
              </p>
              <p className="text-xs text-gray-400 mt-1">
                .xlsx 파일 — As-Is 프로세스 + 분류 결과 (1차 평가 / 두산 검토 / PwC 검토)
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* 업로드 결과 */}
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full flex items-center justify-center text-white text-lg" style={{ backgroundColor: PWC.primary }}>
                      &#128196;
                    </div>
                    <div>
                      <div className="font-bold text-gray-800">{excelResult.filename}</div>
                      <div className="text-xs text-gray-500">
                        {excelResult.task_count}개 Task · {excelResult.classified_count}개 분류 완료
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {excelResult.has_classification && (
                      <span className="px-3 py-1 rounded-full text-xs font-bold bg-green-100 text-green-700 border border-green-200">
                        분류 결과 감지됨
                      </span>
                    )}
                    <button
                      onClick={() => { setExcelResult(null); setExcelTasks([]); }}
                      className="text-sm text-gray-400 hover:text-red-500 transition"
                    >
                      초기화
                    </button>
                  </div>
                </div>

                {/* 시트 선택 */}
                {excelSheets.length > 1 && (
                  <div className="mb-4">
                    <label className="text-xs font-medium text-gray-600 mb-1 block">시트 선택</label>
                    <div className="flex gap-2 flex-wrap">
                      {excelSheets.map((s) => (
                        <button
                          key={s.name}
                          onClick={() => handleExcelSheetSelect(s.name)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                            selectedExcelSheet === s.name
                              ? "border-red-300 bg-red-50 text-red-700"
                              : s.recommended
                              ? "border-green-300 bg-green-50 text-green-700"
                              : "border-gray-200 bg-white text-gray-600"
                          }`}
                        >
                          {s.name}
                          {s.recommended && " (추천)"}
                          <span className="text-gray-400 ml-1">{s.l5_count}개</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* 통계 */}
                <div className="flex gap-3 flex-wrap mb-4">
                  <StatCard label="전체 Task" value={excelResult.task_count} />
                  <StatCard label="분류 완료" value={excelResult.classified_count} accent />
                  <StatCard label="AI" value={excelTasks.filter((t) => t.label === "AI").length} />
                  <StatCard label="AI+Human" value={excelTasks.filter((t) => t.label === "AI + Human").length} />
                  <StatCard label="Human" value={excelTasks.filter((t) => t.label === "Human").length} />
                </div>

                {/* Task 테이블 (간략) */}
                {excelTasks.length > 0 && (
                  <div className="max-h-[400px] overflow-y-auto rounded-lg border border-gray-200">
                    <table className="w-full text-xs">
                      <thead className="sticky top-0 bg-gray-50 border-b border-gray-200">
                        <tr>
                          <th className="text-left px-3 py-2 font-medium text-gray-600">ID</th>
                          <th className="text-left px-3 py-2 font-medium text-gray-600">Task</th>
                          <th className="text-left px-3 py-2 font-medium text-gray-600">L3</th>
                          <th className="text-left px-3 py-2 font-medium text-gray-600">L4</th>
                          <th className="text-center px-3 py-2 font-medium text-gray-600">분류</th>
                          <th className="text-left px-3 py-2 font-medium text-gray-600">판단근거</th>
                        </tr>
                      </thead>
                      <tbody>
                        {excelTasks.map((t) => (
                          <tr key={t.id} className="border-b border-gray-100 hover:bg-gray-50">
                            <td className="px-3 py-2 font-mono text-gray-400">{t.id}</td>
                            <td className="px-3 py-2 text-gray-800 font-medium max-w-[200px] truncate">{t.name}</td>
                            <td className="px-3 py-2 text-gray-500 max-w-[120px] truncate">{t.l3}</td>
                            <td className="px-3 py-2 text-gray-500 max-w-[120px] truncate">{t.l4}</td>
                            <td className="px-3 py-2 text-center">
                              {t.label ? (
                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                  t.label === "AI" ? "bg-green-100 text-green-700" :
                                  t.label === "AI + Human" ? "bg-yellow-100 text-yellow-700" :
                                  t.label === "Human" ? "bg-red-100 text-red-700" :
                                  "bg-gray-100 text-gray-500"
                                }`}>
                                  {t.label}
                                </span>
                              ) : (
                                <span className="text-gray-300">-</span>
                              )}
                            </td>
                            <td className="px-3 py-2 text-gray-500 max-w-[200px] truncate">{t.reason || t.criterion || "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* 다음 단계 */}
              <div className="flex justify-end">
                <button
                  onClick={() => setCurrentStep(1)}
                  className="px-6 py-2.5 rounded-lg text-sm font-bold text-white transition"
                  style={{ backgroundColor: PWC.primary }}
                >
                  다음: As-Is 워크플로우 연결 &rarr;
                </button>
              </div>
            </div>
          )}

          {loading && (
            <div className="text-center py-10">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-red-200 border-t-red-600" />
              <p className="mt-2 text-sm text-gray-500">엑셀 파싱 중...</p>
            </div>
          )}
        </div>
      )}

      {/* ═══ Step 1: As-Is 워크플로우 업로드 ═══ */}
      {currentStep === 1 && (
        <div className="space-y-6">
          {!hasAsIs ? (
            <div className="space-y-4">
              <div
                className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors cursor-pointer ${
                  dragOver ? "border-red-400 bg-red-50" : "border-gray-300 bg-white"
                }`}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOver(false);
                  const file = e.dataTransfer.files[0];
                  if (file) handleAsIsUpload(file);
                }}
                onClick={() => document.getElementById("wf-asis-input")?.click()}
              >
                <input
                  id="wf-asis-input"
                  type="file"
                  accept=".json,.pptx,.ppt"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleAsIsUpload(file);
                  }}
                />
                <div className="text-4xl mb-3">&#128230;</div>
                <p className="text-sm font-medium text-gray-700">
                  As-Is 워크플로우 파일을 업로드하세요
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  JSON (.json) 또는 PPT (.pptx) 파일
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={async () => {
                    setLoading(true);
                    try {
                      const result = await getWorkflowSummary();
                      setSummary(result);
                      if (result.sheets.length > 0) setActiveSheet(result.sheets[0].sheet_id);
                    } catch {} finally { setLoading(false); }
                  }}
                  className="px-4 py-2 rounded-lg border border-gray-300 bg-white text-sm text-gray-600 hover:bg-gray-50 transition"
                >
                  기존 워크플로우 불러오기
                </button>
                <button
                  onClick={() => setCurrentStep(2)}
                  className="px-4 py-2 rounded-lg border border-gray-300 bg-white text-sm text-gray-500 hover:bg-gray-50 transition"
                >
                  건너뛰기 (As-Is 없이 진행) &rarr;
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* JSON Summary */}
              {summary && (
                <>
                  <div className="flex items-center justify-between">
                    <div className="flex gap-3 flex-wrap">
                      <StatCard label="시트 수" value={summary.sheet_count} />
                      {currentSheet && (
                        <>
                          <StatCard label="L4" value={currentSheet.l4_count} />
                          <StatCard label="L5" value={currentSheet.l5_count} accent />
                          {(currentSheet.decision_count ?? 0) > 0 && (
                            <StatCard label="Decision" value={currentSheet.decision_count ?? 0} />
                          )}
                          {/* L5 분류 연결 집계 */}
                          {(() => {
                            const counts: Record<string, number> = {};
                            currentSheet.l4_details.forEach((l4) =>
                              l4.child_l5s.forEach((l5) => {
                                if (l5.cls_label) counts[l5.cls_label] = (counts[l5.cls_label] || 0) + 1;
                              })
                            );
                            return Object.entries(counts).map(([lbl, cnt]) => (
                              <StatCard key={lbl} label={lbl === "AI + Human" ? "AI+Human" : lbl} value={cnt} />
                            ));
                          })()}
                          <StatCard label="총 스텝" value={currentSheet.total_steps} />
                        </>
                      )}
                    </div>
                    <button
                      onClick={() => { setSummary(null); setPptResult(null); setActiveSheet(null); }}
                      className="text-sm text-gray-400 hover:text-red-500 transition"
                    >
                      초기화
                    </button>
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
                    <div className="space-y-3">
                      {/* Decision 노드 요약 배너 */}
                      {currentSheet.decision_count != null && currentSheet.decision_count > 0 && (
                        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-700">
                          <span className="text-base">◇</span>
                          <span className="font-semibold">Decision 노드 {currentSheet.decision_count}개</span>
                          <span className="text-amber-500">— 분기 조건이 아래 L4 노드에 표시됩니다</span>
                        </div>
                      )}

                      <div className="max-h-[420px] overflow-y-auto space-y-3 pr-1">
                        {currentSheet.l4_details.map((l4) => (
                          <div key={l4.node_id} className="bg-white rounded-lg border border-gray-200 p-4">
                            <div className="flex items-center gap-2 mb-2 flex-wrap">
                              <span className="text-xs font-mono px-2 py-0.5 rounded" style={{ backgroundColor: PWC.bg, color: PWC.primary }}>
                                {l4.task_id}
                              </span>
                              <span className="font-semibold text-sm flex-1">{l4.label}</span>
                              {/* L5 분류 집계 미니 뱃지 */}
                              {(() => {
                                const counts: Record<string, number> = {};
                                l4.child_l5s.forEach((l5) => {
                                  if (l5.cls_label) counts[l5.cls_label] = (counts[l5.cls_label] || 0) + 1;
                                });
                                return Object.entries(counts).map(([lbl, cnt]) => {
                                  const s =
                                    lbl === "AI"         ? { bg: "#DCFCE7", text: "#15803D" } :
                                    lbl === "AI + Human" ? { bg: "#FEF9C3", text: "#A16207" } :
                                    lbl === "Human"      ? { bg: "#FEE2E2", text: "#DC2626" } :
                                    { bg: "#F3F4F6", text: "#6B7280" };
                                  return (
                                    <span key={lbl} className="px-1.5 py-0.5 rounded text-[9px] font-bold shrink-0"
                                      style={{ backgroundColor: s.bg, color: s.text }}>
                                      {lbl === "AI + Human" ? "A+H" : lbl} {cnt}
                                    </span>
                                  );
                                });
                              })()}
                            </div>

                            {/* L5 자식 */}
                            {l4.child_l5s.length > 0 && (
                              <div className="ml-4 space-y-1 mb-2">
                                {l4.child_l5s.map((l5, i) => {
                                  const cls = l5.cls_label;
                                  const clsStyle =
                                    cls === "AI"         ? { bg: "#DCFCE7", text: "#15803D" } :
                                    cls === "AI + Human" ? { bg: "#FEF9C3", text: "#A16207" } :
                                    cls === "Human"      ? { bg: "#FEE2E2", text: "#DC2626" } :
                                    null;
                                  return (
                                    <div key={l5.node_id || i} className="flex items-center gap-2 text-xs text-gray-600 py-0.5">
                                      <span className="w-1.5 h-1.5 rounded-full bg-gray-300 shrink-0" />
                                      <span className="font-mono text-gray-400 shrink-0">{l5.task_id}</span>
                                      <span className="flex-1">{l5.label}</span>
                                      {clsStyle ? (
                                        <span
                                          className="shrink-0 px-2 py-0.5 rounded-full text-[9px] font-bold"
                                          style={{ backgroundColor: clsStyle.bg, color: clsStyle.text }}
                                          title={l5.cls_reason || cls}
                                        >
                                          {cls}
                                        </span>
                                      ) : cls === "" ? null : (
                                        <span className="shrink-0 px-2 py-0.5 rounded-full text-[9px] font-bold bg-gray-100 text-gray-400">
                                          미분류
                                        </span>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            )}

                            {/* Decision 분기 */}
                            {l4.branches && l4.branches.length > 0 && (
                              <div className="ml-2 mt-2 space-y-1.5">
                                {l4.branches.map((b, bi) => (
                                  <div key={bi}>
                                    {b.type === "decision" ? (
                                      <div>
                                        <div className="flex items-center gap-1.5 text-xs text-amber-700 font-medium mb-1">
                                          <span className="text-base leading-none">◇</span>
                                          <span>{b.decision_label || "분기 조건"}</span>
                                        </div>
                                        <div className="ml-4 space-y-1">
                                          {b.branches?.map((br, bri) => (
                                            <div key={bri} className="flex items-center gap-1.5 text-xs">
                                              <span className="text-gray-400">├─</span>
                                              <span className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200 font-medium">
                                                {br.condition}
                                              </span>
                                              <span className="text-gray-400">→</span>
                                              <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${
                                                br.target_level === "L4" ? "bg-red-50 text-red-600" :
                                                br.target_level === "L5" ? "bg-blue-50 text-blue-600" :
                                                "bg-gray-100 text-gray-500"
                                              }`}>{br.target_level}</span>
                                              <span className="text-gray-600">{br.target_label}</span>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    ) : (
                                      <div className="flex items-center gap-1.5 text-xs">
                                        <span className="text-gray-400">→</span>
                                        <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 border border-blue-200 font-medium">
                                          {b.condition}
                                        </span>
                                        <span className="text-gray-400">→</span>
                                        <span className="text-gray-600">{b.target_label}</span>
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>

                      {/* Decision 노드 전체 목록 */}
                      {currentSheet.decision_nodes && currentSheet.decision_nodes.length > 0 && (
                        <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-4">
                          <div className="text-xs font-bold text-amber-700 mb-2 flex items-center gap-1.5">
                            <span>◇</span> Decision 노드 목록
                          </div>
                          <div className="space-y-2">
                            {currentSheet.decision_nodes.map((dn) => (
                              <div key={dn.node_id} className="bg-white rounded border border-amber-200 px-3 py-2">
                                <div className="text-xs font-semibold text-gray-700 mb-1">{dn.label || "(분기)"}</div>
                                <div className="space-y-0.5">
                                  {dn.outgoing.map((o, oi) => (
                                    <div key={oi} className="flex items-center gap-1.5 text-xs text-gray-600">
                                      <span className="text-amber-500 shrink-0">•</span>
                                      <span className="px-1 py-0.5 rounded bg-amber-100 text-amber-700 text-[10px] font-medium">{o.condition}</span>
                                      <span className="text-gray-400">→</span>
                                      <span>{o.to_label}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}

              {/* PPT Summary */}
              {pptResult && (
                <div className="bg-white rounded-xl border border-gray-200 p-4">
                  <div className="flex gap-3 mb-3">
                    <StatCard label="슬라이드" value={pptResult.slide_count} />
                    {pptResult.slides[activePptSlide] && (
                      <StatCard label="노드" value={pptResult.slides[activePptSlide].node_count} />
                    )}
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    {pptResult.slides.map((s, i) => (
                      <button
                        key={i}
                        onClick={() => setActivePptSlide(i)}
                        className={`px-3 py-1.5 rounded-lg text-xs border transition ${
                          activePptSlide === i ? "border-red-300 bg-red-50 text-red-700" : "border-gray-200 bg-white text-gray-600"
                        }`}
                      >
                        {s.title || `슬라이드 ${i + 1}`}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* 매핑 확인 패널 */}
              <MappingCheckPanel hasExcel={!!excelResult} hasAsIs={!!hasAsIs} activeSheetId={activeSheet} />

              {/* 다음 단계 */}
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setCurrentStep(2)}
                  className="px-6 py-2.5 rounded-lg text-sm font-bold text-white transition"
                  style={{ backgroundColor: PWC.primary }}
                >
                  다음: Step 1 기본 설계 &rarr;
                </button>
              </div>
            </div>
          )}

          {loading && (
            <div className="text-center py-10">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-red-200 border-t-red-600" />
              <p className="mt-2 text-sm text-gray-500">파싱 중...</p>
            </div>
          )}
        </div>
      )}

      {/* ═══ Step 2: Step 1 기본 설계 (Top-Down) ═══ */}
      {currentStep === 2 && (
        <div className="space-y-6">
          {/* 헤더 + 액션 버튼 */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: PWC.primary }}>1</div>
                <div>
                  <div className="font-bold text-gray-800">선도사례 벤치마킹 기반 Workflow 기본 설계</div>
                  <div className="text-xs text-gray-500">Top-Down: 벤치마킹과 프롬프트를 자유 순서로 실행할 수 있습니다.</div>
                </div>
              </div>
              {/* 벤치마킹 버튼 — 순서 무관 독립 실행 */}
              <button
                onClick={() => handleBenchmark()}
                disabled={bmLoading}
                className="px-4 py-2 rounded-lg text-sm font-bold border-2 transition disabled:opacity-50"
                style={{
                  borderColor: benchmarkTable.length > 0 ? "#16A34A" : "#3B82F6",
                  color: benchmarkTable.length > 0 ? "#16A34A" : "#3B82F6",
                  backgroundColor: benchmarkTable.length > 0 ? "#F0FDF4" : "#EFF6FF",
                }}
              >
                {bmLoading ? (
                  <span className="flex items-center gap-2">
                    <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-blue-300 border-t-blue-600" />
                    검색 중...
                  </span>
                ) : benchmarkTable.length > 0 ? (
                  `\u2713 벤치마킹 완료 (${benchmarkTable.length}건)`
                ) : (
                  "\uD83D\uDD0D 벤치마킹 수행"
                )}
              </button>
            </div>

            {/* 벤치마킹 결과 테이블 */}
            {benchmarkTable.length > 0 && (
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-xs font-bold text-gray-700">벤치마킹 결과표</div>
                  {benchmarkSummary && (
                    <div className="text-[10px] text-gray-500 max-w-[60%] text-right">{benchmarkSummary.slice(0, 150)}</div>
                  )}
                </div>
                <div className="max-h-[340px] overflow-y-auto overflow-x-auto rounded-lg border border-blue-200">
                  <table className="w-full text-xs" style={{ minWidth: "1100px" }}>
                    <thead className="sticky top-0 bg-blue-50 border-b border-blue-200">
                      <tr>
                        <th className="text-left px-3 py-2 font-medium text-blue-800 whitespace-nowrap">기업</th>
                        <th className="text-left px-3 py-2 font-medium text-blue-800 whitespace-nowrap">유형</th>
                        <th className="text-left px-3 py-2 font-medium text-blue-800 whitespace-nowrap">산업</th>
                        <th className="text-left px-3 py-2 font-medium text-blue-800 whitespace-nowrap">적용 L4</th>
                        <th className="text-left px-3 py-2 font-medium text-blue-800 whitespace-nowrap">도입 목표</th>
                        <th className="text-left px-3 py-2 font-medium text-blue-800 whitespace-nowrap">AI 기술</th>
                        <th className="text-left px-3 py-2 font-medium text-blue-800 whitespace-nowrap">핵심 데이터</th>
                        <th className="text-left px-3 py-2 font-medium text-blue-800 whitespace-nowrap">도입 방식</th>
                        <th className="text-left px-3 py-2 font-medium text-blue-800 whitespace-nowrap">적용 사례</th>
                        <th className="text-left px-3 py-2 font-medium text-blue-800 whitespace-nowrap">성과</th>
                        <th className="text-left px-3 py-2 font-medium text-blue-800 whitespace-nowrap">인프라</th>
                        <th className="text-left px-3 py-2 font-medium text-blue-800 whitespace-nowrap">두산 시사점</th>
                      </tr>
                    </thead>
                    <tbody>
                      {benchmarkTable.map((row, i) => (
                        <tr key={i} className="border-b border-blue-100 hover:bg-blue-50/50">
                          <td className="px-3 py-2 font-medium text-gray-800 whitespace-nowrap">
                            {row.url ? (
                              <a href={row.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{row.source}</a>
                            ) : row.source}
                          </td>
                          <td className="px-3 py-2 whitespace-nowrap">
                            {row.company_type && (
                              <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${row.company_type.includes("Tech") && !row.company_type.includes("非") ? "bg-indigo-50 text-indigo-700" : "bg-orange-50 text-orange-700"}`}>
                                {row.company_type.includes("非") ? "非Tech" : "Tech"}
                              </span>
                            )}
                          </td>
                          <td className="px-3 py-2 text-gray-500 whitespace-nowrap">{row.industry}</td>
                          <td className="px-3 py-2 text-gray-600 max-w-[120px]">{row.process_area}</td>
                          <td className="px-3 py-2 text-gray-600 max-w-[120px]">{row.ai_adoption_goal}</td>
                          <td className="px-3 py-2">
                            <span className="px-1.5 py-0.5 rounded bg-purple-50 text-purple-700 text-[10px] font-medium">{row.ai_technology}</span>
                          </td>
                          <td className="px-3 py-2 text-gray-500 max-w-[120px]">{row.key_data}</td>
                          <td className="px-3 py-2 text-gray-500 whitespace-nowrap">{row.adoption_method}</td>
                          <td className="px-3 py-2 text-gray-600 max-w-[200px]">{row.use_case}</td>
                          <td className="px-3 py-2 text-green-700 font-medium max-w-[130px]">{row.outcome}</td>
                          <td className="px-3 py-2 text-gray-500 max-w-[120px]">{row.infrastructure}</td>
                          <td className="px-3 py-2 text-gray-500 max-w-[180px]">{row.implication}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 채팅 영역 */}
            <div className="border border-gray-200 rounded-lg bg-gray-50" style={{ height: "380px", display: "flex", flexDirection: "column" }}>
              {/* 메시지 목록 */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {chatMessages.length === 0 && !step1Result && (
                  <div className="text-center py-8 text-gray-400 text-sm">
                    <div className="text-3xl mb-3">&#128172;</div>
                    <p>프롬프트를 입력하여 Workflow 기본 설계를 생성하세요.</p>
                    <p className="text-xs mt-1">특정 기업명을 언급하면 해당 기업의 적용 사례도 자동 벤치마킹합니다.</p>
                    <p className="text-xs mt-1 text-gray-300">벤치마킹을 먼저 하거나, 프롬프트를 먼저 하거나 — 순서는 자유입니다.</p>
                  </div>
                )}
                {chatMessages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[80%] rounded-lg px-4 py-2.5 text-sm ${
                      msg.role === "user"
                        ? "bg-red-50 text-gray-800 border border-red-200"
                        : msg.role === "system"
                        ? "bg-blue-50 text-blue-700 border border-blue-200 italic"
                        : "bg-white text-gray-700 border border-gray-200"
                    }`}>
                      <div className="whitespace-pre-wrap">{msg.content.length > 500 ? msg.content.slice(0, 500) + "..." : msg.content}</div>
                    </div>
                  </div>
                ))}
                {(loading || bmLoading) && currentStep === 2 && (
                  <div className="flex justify-start">
                    <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
                      <div className="flex items-center gap-2 text-sm text-gray-500">
                        <div className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-red-600" />
                        {bmLoading ? "벤치마킹 검색 중..." : "AI가 설계 중..."}
                      </div>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* 입력 영역 */}
              <div className="border-t border-gray-200 p-3 bg-white rounded-b-lg">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        if (step1Result) handleChat();
                        else handleGenerateStep1(chatInput || undefined);
                      }
                    }}
                    placeholder={
                      step1Result
                        ? "추가 질문이나 수정 요청... (예: Google처럼 People Analytics 적용해줘)"
                        : "프롬프트 입력... (예: Siemens, GE의 HR AI 적용 사례를 기반으로 설계해줘)"
                    }
                    className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-red-300"
                    disabled={loading || bmLoading}
                  />
                  {!step1Result ? (
                    <button
                      onClick={() => handleGenerateStep1(chatInput || undefined)}
                      disabled={loading || bmLoading}
                      className="px-4 py-2 rounded-lg text-sm font-bold text-white transition disabled:opacity-50 whitespace-nowrap"
                      style={{ backgroundColor: PWC.primary }}
                    >
                      {loading ? "생성 중..." : "기본 설계 생성"}
                    </button>
                  ) : (
                    <button
                      onClick={handleChat}
                      disabled={loading || bmLoading || !chatInput.trim()}
                      className="px-4 py-2 rounded-lg text-sm font-bold text-white transition disabled:opacity-50"
                      style={{ backgroundColor: PWC.primary }}
                    >
                      전송
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Step 1 결과 요약 */}
          {step1Result && (
            <div className="space-y-4">
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h3 className="font-bold text-gray-800 mb-3">기본 설계 결과</h3>
                <p className="text-sm text-gray-600 mb-4">{step1Result.blueprint_summary}</p>

                {/* L2~L3 재구조화 방향 */}
                {step1Result.l2_restructure && (
                  <div className="mb-4 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
                    <div className="text-xs font-bold text-amber-700 mb-1">L2~L3 프로세스 재구조화 방향</div>
                    <p className="text-xs text-amber-900">{step1Result.l2_restructure}</p>
                  </div>
                )}

                {/* 벤치마킹 인사이트 */}
                {step1Result.benchmark_insights && step1Result.benchmark_insights.length > 0 && (
                  <div className="mb-4">
                    <div className="text-xs font-bold text-gray-600 mb-2">벤치마킹 인사이트</div>
                    <div className="space-y-1.5">
                      {step1Result.benchmark_insights.map((insight, i) => {
                        const item = insight as Record<string, string>;
                        return typeof insight === "string" ? (
                          <div key={i} className="text-xs text-gray-500">{insight}</div>
                        ) : (
                          <div key={i} className="bg-blue-50 rounded-lg px-3 py-2 text-xs border border-blue-100">
                            <div className="font-medium text-blue-800">{item.source}</div>
                            <div className="text-gray-600 mt-0.5">{item.insight}</div>
                            {item.application && <div className="text-blue-600 mt-0.5">&rarr; {item.application}</div>}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* AI 적용 통계 */}
                <div className="flex gap-3 flex-wrap mb-5">
                  <StatCard label="Full-Auto" value={step1Result.full_auto_count || 0} accent />
                  <StatCard label="Human-in-Loop" value={step1Result.human_in_loop_count || 0} />
                  <StatCard label="Human-on-the-Loop" value={step1Result.human_supervised_count || 0} />
                </div>

                {/* L3 → L4 → L5 재설계 프로세스 트리 */}
                {step1Result.redesigned_process && step1Result.redesigned_process.length > 0 && (
                  <div className="space-y-3 max-h-[560px] overflow-y-auto pr-1">
                    {step1Result.redesigned_process.map((l3) => {
                      const changeBadge: Record<string, { bg: string; text: string }> = {
                        "유지": { bg: "#F3F4F6", text: "#6B7280" },
                        "통합": { bg: "#DBEAFE", text: "#1D4ED8" },
                        "세분화": { bg: "#D1FAE5", text: "#065F46" },
                        "추가": { bg: "#FEF9C3", text: "#92400E" },
                        "삭제": { bg: "#FEE2E2", text: "#991B1B" },
                      };
                      const l3badge = changeBadge[l3.change_type] || changeBadge["유지"];
                      return (
                        <div key={l3.l3_id} className="border border-gray-200 rounded-xl overflow-hidden">
                          {/* L3 헤더 */}
                          <div className="flex items-center gap-2 px-4 py-2.5 bg-gray-50 border-b border-gray-200">
                            <span className="font-mono text-[10px] text-gray-400">{l3.l3_id}</span>
                            <span className="text-sm font-bold text-gray-800 flex-1">{l3.l3_name}</span>
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold" style={{ backgroundColor: l3badge.bg, color: l3badge.text }}>{l3.change_type}</span>
                            {l3.change_reason && l3.change_type !== "유지" && (
                              <span className="text-[10px] text-gray-400 max-w-[200px] truncate">{l3.change_reason}</span>
                            )}
                          </div>
                          {/* L4 목록 */}
                          <div className="divide-y divide-gray-100">
                            {l3.l4_list.map((l4) => {
                              const l4badge = changeBadge[l4.change_type] || changeBadge["유지"];
                              return (
                                <div key={l4.l4_id} className="px-4 py-2">
                                  <div className="flex items-center gap-2 mb-1.5">
                                    <span className="font-mono text-[10px] text-gray-400">{l4.l4_id}</span>
                                    <span className="text-xs font-semibold text-gray-700 flex-1">{l4.l4_name}</span>
                                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold" style={{ backgroundColor: l4badge.bg, color: l4badge.text }}>{l4.change_type}</span>
                                  </div>
                                  {/* L5 Task 목록 */}
                                  <div className="space-y-1 pl-4">
                                    {l4.l5_list.map((l5) => {
                                      const hasAI = l5.ai_application && l5.ai_application !== "해당 없음";
                                      const l5badge = changeBadge[l5.change_type] || changeBadge["유지"];
                                      const autoColors: Record<string, string> = {
                                        "Full-Auto": "#15803D",
                                        "Human-in-Loop": "#A16207",
                                        "Human-on-the-Loop": "#1D4ED8",
                                        "Human": "#6B7280",
                                      };
                                      return (
                                        <div key={l5.task_id} className={`rounded border px-2.5 py-1.5 ${hasAI ? "bg-green-50 border-green-100" : "bg-gray-50 border-gray-100"}`}>
                                          <div className="flex items-center gap-1.5 flex-wrap">
                                            <span className="font-mono text-[9px] text-gray-400">{l5.task_id}</span>
                                            <span className="text-[11px] font-medium text-gray-700 flex-1">{l5.task_name}</span>
                                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold" style={{ backgroundColor: l5badge.bg, color: l5badge.text }}>{l5.change_type}</span>
                                            {hasAI && (
                                              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded" style={{ backgroundColor: "#D1FAE5", color: autoColors[l5.automation_level] || "#15803D" }}>
                                                {l5.automation_level}
                                              </span>
                                            )}
                                          </div>
                                          {hasAI && (
                                            <div className="mt-0.5 text-[10px] text-gray-500">
                                              <span className="text-green-700 font-medium">AI: </span>{l5.ai_application}
                                              {l5.ai_technique && l5.ai_technique !== "해당 없음" && (
                                                <span className="text-gray-400 ml-1">({l5.ai_technique})</span>
                                              )}
                                            </div>
                                          )}
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* 다음 단계 */}
              <div className="flex justify-between items-center">
                <button
                  onClick={() => setShowToBeModal(true)}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-bold border-2 transition"
                  style={{ borderColor: PWC.primary, color: PWC.primary, backgroundColor: PWC.bg }}
                >
                  &#9741; 워크플로우 보기 / 편집
                </button>
                <button
                  onClick={() => setCurrentStep(3)}
                  className="px-6 py-2.5 rounded-lg text-sm font-bold text-white transition"
                  style={{ backgroundColor: PWC.primary }}
                >
                  다음: Step 2 상세 설계 &rarr;
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* To-Be Workflow 모달 */}
      <ToBeWorkflowModal open={showToBeModal} onClose={() => setShowToBeModal(false)} />

      {/* ═══ Step 3: Step 2 상세 설계 (Bottom-Up) ═══ */}
      {currentStep === 3 && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: PWC.primary }}>2</div>
                <div>
                  <div className="font-bold text-gray-800">Pain Point 기반 상세 설계</div>
                  <div className="text-xs text-gray-500">
                    Bottom-Up: 두산에 최적화된 AI 기반 To-Be Workflow 상세 설계
                  </div>
                </div>
              </div>
              {!step2Result && (
                <button
                  onClick={handleGenerateStep2}
                  disabled={loading || !step1Result}
                  className="px-6 py-2.5 rounded-lg text-sm font-bold text-white transition disabled:opacity-50"
                  style={{ backgroundColor: PWC.primary }}
                >
                  {loading ? "생성 중..." : "상세 설계 생성"}
                </button>
              )}
            </div>

            {!step1Result && (
              <div className="text-center py-10 text-gray-400 text-sm">
                <p>Step 1 기본 설계를 먼저 완료하세요.</p>
                <button
                  onClick={() => setCurrentStep(2)}
                  className="mt-2 text-red-500 underline text-xs"
                >
                  Step 1로 이동
                </button>
              </div>
            )}

            {loading && currentStep === 3 && (
              <div className="text-center py-10">
                <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-red-200 border-t-red-600" />
                <p className="mt-2 text-sm text-gray-500">Step 1 결과 + Pain Point를 분석하여 상세 설계 중...</p>
                <p className="text-xs text-gray-400 mt-1">Senior AI 기반 E2E 오케스트레이션 구조를 설계합니다.</p>
              </div>
            )}
          </div>

          {/* Step 2 결과 */}
          {step2Result && (
            <div className="space-y-4">
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h3 className="font-bold text-gray-800 mb-3">상세 설계 결과</h3>
                <p className="text-sm text-gray-600 mb-2">{step2Result.blueprint_summary}</p>
                {step2Result.design_philosophy && (
                  <p className="text-xs text-gray-500 mb-4 italic">{step2Result.design_philosophy}</p>
                )}

                <div className="flex gap-3 flex-wrap mb-4">
                  <StatCard label="Agent 수" value={step2Result.agents?.length || 0} accent />
                  <StatCard label="Total Tasks" value={step2Result.total_tasks || 0} />
                  <StatCard label="Full-Auto" value={step2Result.full_auto_count || 0} />
                  <StatCard label="Human-in-Loop" value={step2Result.human_in_loop_count || 0} />
                </div>

                {/* Agent 상세 */}
                {step2Result.agents && (
                  <div className="space-y-3">
                    {step2Result.agents.map((agent) => (
                      <div key={agent.agent_id} className="border border-gray-200 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-700">
                            {agent.agent_type}
                          </span>
                          <span className="text-sm font-bold text-gray-800">{agent.agent_name}</span>
                          <span className="text-[10px] text-gray-400">{agent.ai_technique}</span>
                        </div>
                        <p className="text-xs text-gray-500 mb-3">{agent.description}</p>

                        {/* 소속 Task */}
                        <div className="space-y-1.5">
                          {agent.assigned_tasks?.map((task) => (
                            <div key={task.task_id} className="bg-gray-50 rounded-lg px-3 py-2 text-xs">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-mono text-gray-400">{task.task_id}</span>
                                <span className="font-medium text-gray-800">{task.task_name}</span>
                                <span className={`px-1.5 py-0.5 rounded-full text-[9px] font-bold ${
                                  task.automation_level?.includes("Full") ? "bg-green-100 text-green-700" :
                                  task.automation_level?.includes("on-the") ? "bg-blue-100 text-blue-700" :
                                  "bg-yellow-100 text-yellow-700"
                                }`}>
                                  {task.automation_level}
                                </span>
                              </div>
                              <div className="text-gray-500">
                                AI: {task.ai_role}
                                {task.human_role && <span className="ml-2">| Human: {task.human_role}</span>}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Execution Flow */}
                {step2Result.execution_flow && step2Result.execution_flow.length > 0 && (
                  <div className="mt-6">
                    <h4 className="text-sm font-bold text-gray-700 mb-3">실행 흐름</h4>
                    <div className="space-y-2">
                      {step2Result.execution_flow.map((step) => (
                        <div key={step.step} className="flex items-start gap-3">
                          <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0"
                            style={{ backgroundColor: step.step_type === "parallel" ? PWC.primaryLight : PWC.primary }}>
                            {step.step}
                          </div>
                          <div>
                            <div className="text-sm font-medium text-gray-800">{step.step_name}</div>
                            <div className="text-xs text-gray-500">{step.description}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* WorkflowEditor 편집 */}
              <WorkflowEditor
                result={step2Result as unknown as import("@/lib/api").NewWorkflowResult}
                onSave={() => {}}
              />
            </div>
          )}
        </div>
      )}
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
