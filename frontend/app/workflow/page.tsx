"use client";

import { useState, useCallback } from "react";
import {
  uploadWorkflow,
  getWorkflowSummary,
  type WorkflowSummary,
  type WorkflowSheetSummary,
  type WorkflowStep,
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeSheet, setActiveSheet] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  /* ── 업로드 ────────────────────────────────────────────── */
  const handleUpload = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);
    try {
      const result = await uploadWorkflow(file);
      setSummary(result);
      if (result.sheets.length > 0) {
        setActiveSheet(result.sheets[0].sheet_id);
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
    if (file && file.name.endsWith(".json")) handleUpload(file);
  };

  /* ── 기존 워크플로우 로드 ─────────────────────────────── */
  const handleLoadExisting = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getWorkflowSummary();
      setSummary(result);
      if (result.sheets.length > 0) {
        setActiveSheet(result.sheets[0].sheet_id);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  const currentSheet = summary?.sheets.find((s) => s.sheet_id === activeSheet);

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div>
        <h1 className="text-2xl font-bold" style={{ color: PWC.primary }}>
          As-Is Workflow 분석
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          hr-workflow-ai에서 내보낸 JSON 파일을 업로드하면 프로세스 구조와 실행 순서(순차/병렬)를 분석합니다.
        </p>
      </div>

      {/* 업로드 영역 */}
      {!summary && (
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
              accept=".json"
              className="hidden"
              onChange={handleFileChange}
            />
            <div className="text-4xl mb-3">&#128230;</div>
            <p className="text-sm font-medium text-gray-700">
              워크플로우 JSON 파일을 드래그하거나 클릭하여 업로드
            </p>
            <p className="text-xs text-gray-400 mt-1">
              hr-workflow-ai에서 내보낸 .json 파일
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

      {/* 요약 카드 */}
      {summary && (
        <>
          <div className="flex items-center justify-between">
            <div className="flex gap-3">
              <StatCard label="시트 수" value={summary.sheet_count} />
              {currentSheet && (
                <>
                  <StatCard label="L4 (Activity)" value={currentSheet.l4_count} />
                  <StatCard label="L5 (Task)" value={currentSheet.l5_count} />
                  <StatCard label="총 스텝" value={currentSheet.total_steps} />
                  <StatCard
                    label="병렬 스텝"
                    value={currentSheet.parallel_steps}
                    accent
                  />
                  <StatCard label="순차 스텝" value={currentSheet.sequential_steps} />
                </>
              )}
            </div>
            <button
              onClick={() => { setSummary(null); setActiveSheet(null); }}
              className="text-sm text-gray-400 hover:text-red-500 transition"
            >
              다른 파일 업로드
            </button>
          </div>

          {/* 시트 탭 */}
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

          {/* 실행 순서 시각화 */}
          {currentSheet && (
            <div className="space-y-6">
              <h2 className="text-lg font-bold text-gray-800">
                실행 순서 — {currentSheet.sheet_name}
              </h2>
              <ExecutionOrderView
                steps={currentSheet.execution_order}
                sheet={currentSheet}
              />

              {/* L4 상세 */}
              <h2 className="text-lg font-bold text-gray-800 mt-8">
                L4 Activity 상세
              </h2>
              <div className="space-y-3">
                {currentSheet.l4_details.map((l4) => (
                  <div
                    key={l4.node_id}
                    className="bg-white rounded-lg border border-gray-200 p-4"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className="text-xs font-mono px-2 py-0.5 rounded"
                        style={{ backgroundColor: "#FFF5F7", color: PWC.primary }}
                      >
                        {l4.task_id}
                      </span>
                      <span className="font-semibold text-sm">{l4.label}</span>
                      {l4.description && (
                        <span className="text-xs text-gray-400">
                          — {l4.description}
                        </span>
                      )}
                    </div>
                    {l4.child_l5s.length > 0 && (
                      <div className="ml-4 mt-2 space-y-1">
                        {l4.child_l5s.map((l5, i) => (
                          <div
                            key={l5.node_id || i}
                            className="flex items-center gap-2 text-xs text-gray-600"
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-gray-300" />
                            <span className="font-mono text-gray-400">
                              {l5.task_id}
                            </span>
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
    </div>
  );
}

/* ── 통계 카드 ─────────────────────────────────────────────── */
function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: boolean;
}) {
  return (
    <div
      className="rounded-lg border px-4 py-3 min-w-[100px]"
      style={{
        backgroundColor: accent ? "#FFF5F7" : PWC.cardBg,
        borderColor: accent ? PWC.primaryLight : "#E5E7EB",
      }}
    >
      <div className="text-xs text-gray-500">{label}</div>
      <div
        className="text-xl font-bold mt-0.5"
        style={{ color: accent ? PWC.primary : "#1F2937" }}
      >
        {value}
      </div>
    </div>
  );
}

/* ── 실행 순서 시각화 ──────────────────────────────────────── */
function ExecutionOrderView({
  steps,
  sheet,
}: {
  steps: WorkflowStep[];
  sheet: WorkflowSheetSummary;
}) {
  if (steps.length === 0) {
    return (
      <div className="text-sm text-gray-400 py-6 text-center">
        실행 순서 정보가 없습니다.
      </div>
    );
  }

  return (
    <div className="relative">
      {steps.map((step, idx) => {
        const nodes = step.nodes || step.tasks || [];
        const isParallel = step.is_parallel ?? step.type === "병렬";

        return (
          <div key={step.step} className="flex items-start gap-4 mb-2">
            {/* 스텝 번호 + 연결선 */}
            <div className="flex flex-col items-center w-10 shrink-0">
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white"
                style={{
                  backgroundColor: isParallel ? PWC.primaryLight : PWC.primary,
                }}
              >
                {step.step}
              </div>
              {idx < steps.length - 1 && (
                <div
                  className="w-0.5 flex-1 min-h-[20px]"
                  style={{ backgroundColor: "#E5E7EB" }}
                />
              )}
            </div>

            {/* 노드 카드 */}
            <div
              className={`flex-1 flex gap-2 ${
                isParallel ? "flex-row" : "flex-col"
              }`}
            >
              {isParallel && (
                <div className="self-center text-[10px] font-bold text-white px-2 py-0.5 rounded-full mr-1" style={{ backgroundColor: PWC.primaryLight }}>
                  병렬
                </div>
              )}
              {nodes.map((node, ni) => (
                <div
                  key={node.node_id || ni}
                  className="bg-white border border-gray-200 rounded-lg px-4 py-2.5 flex items-center gap-3 shadow-sm"
                  style={
                    isParallel
                      ? { borderLeft: `3px solid ${PWC.primaryLight}` }
                      : {}
                  }
                >
                  <span
                    className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                    style={{
                      backgroundColor: "#FFF5F7",
                      color: PWC.primary,
                    }}
                  >
                    {node.task_id || node.label}
                  </span>
                  <span className="text-sm font-medium text-gray-800">
                    {node.label}
                  </span>
                  {node.level && (
                    <span className="text-[10px] text-gray-400">{node.level}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
