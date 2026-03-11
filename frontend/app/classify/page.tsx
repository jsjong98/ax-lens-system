"use client";

import { useEffect, useState, useRef } from "react";
import {
  getTasks, getSettings, classifyTasks, healthCheck,
  type Task, type ClassifierSettings, type SSEEvent, type ClassificationResult,
} from "@/lib/api";
import TaskTable from "@/components/TaskTable";
import StatusBadge from "@/components/StatusBadge";
import { Play, Square, AlertCircle, CheckCircle2, SlidersHorizontal, Trash2 } from "lucide-react";
import { deleteAllResults, type ProviderType } from "@/lib/api";

type RunState = "idle" | "running" | "done" | "error";

const PROVIDER_CONFIG = {
  openai: {
    label: "O 모델",
    badge: "O 모델",
    badgeColor: "#10a37f",
    keyEnv: "OPENAI_API_KEY",
  },
  anthropic: {
    label: "A 모델",
    badge: "A 모델",
    badgeColor: "#c96442",
    keyEnv: "ANTHROPIC_API_KEY",
  },
} as const;

export default function ClassifyPage() {
  const [tasks, setTasks]           = useState<Task[]>([]);
  const [settings, setSettings]     = useState<ClassifierSettings | null>(null);
  const [provider, setProvider]     = useState<ProviderType>("openai");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [runState, setRunState]     = useState<RunState>("idle");
  const [progress, setProgress]     = useState({ current: 0, total: 0 });
  const [liveResults, setLiveResults] = useState<Record<string, ClassificationResult>>({});
  const [errorMsg, setErrorMsg]     = useState("");
  const [backendOk, setBackendOk]         = useState<boolean | null>(null);
  const [openaiReady, setOpenaiReady]     = useState<boolean | null>(null);
  const [anthropicReady, setAnthropicReady] = useState<boolean | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const [remainingSec, setRemainingSec] = useState<number | null>(null);
  const stopRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    healthCheck()
      .then((res) => {
        setBackendOk(true);
        setOpenaiReady(res.openai_configured ?? false);
        setAnthropicReady(res.anthropic_configured ?? false);
      })
      .catch(() => {
        setBackendOk(false);
        setOpenaiReady(false);
        setAnthropicReady(false);
      });
    getTasks({ page_size: 500 }).then((r) => setTasks(r.tasks));
    getSettings().then(setSettings);
  }, []);

  const currentProviderReady = provider === "openai" ? openaiReady : anthropicReady;
  const canRun = backendOk && settings !== null && runState !== "running";

  const handleStart = () => {
    if (!canRun) return;
    setRunState("running");
    setLiveResults({});
    setErrorMsg("");
    setRemainingSec(null);
    startTimeRef.current = Date.now();

    const targetIds = selectedIds.size > 0 ? [...selectedIds] : null;
    const total = targetIds ? targetIds.length : tasks.length;
    setProgress({ current: 0, total });

    const stop = classifyTasks(
      { task_ids: targetIds, settings, provider },
      (event: SSEEvent) => {
        if (event.type === "progress") {
          setProgress({ current: event.current, total: event.total });
          setLiveResults((prev) => ({ ...prev, [event.task_id]: event.result }));

          // 남은 시간 계산
          if (startTimeRef.current && event.current > 0) {
            const elapsed = (Date.now() - startTimeRef.current) / 1000;
            const secPerTask = elapsed / event.current;
            const remaining = Math.round(secPerTask * (event.total - event.current));
            setRemainingSec(remaining);
          }
        } else if (event.type === "done") {
          setRunState("done");
          setRemainingSec(null);
        } else if (event.type === "error") {
          setRunState("error");
          setErrorMsg(event.message);
          setRemainingSec(null);
        }
      },
      (err) => {
        setRunState("error");
        setErrorMsg(err.message);
        setRemainingSec(null);
      }
    );
    stopRef.current = stop;
  };

  const formatRemaining = (sec: number): string => {
    if (sec < 60) return `약 ${sec}초 남음`;
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return s > 0 ? `약 ${m}분 ${s}초 남음` : `약 ${m}분 남음`;
  };

  const handleStop = () => {
    stopRef.current?.();
    setRunState("idle");
  };

  const pct = progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0;

  const aiCount     = Object.values(liveResults).filter((r) => r.label === "AI 수행 가능").length;
  const hybridCount = Object.values(liveResults).filter((r) => r.label === "AI + Human").length;
  const humanCount  = Object.values(liveResults).filter((r) => r.label === "인간 수행 필요").length;

  const taskRows = tasks.map((t) => ({ ...t, result: liveResults[t.id] }));

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div>
        <h1 className="text-xl font-bold text-gray-900">분류 실행</h1>
        <p className="mt-1 text-xs text-gray-500">
          Task를 선택하거나 전체 분류를 실행합니다.
        </p>
      </div>

      {/* 백엔드 상태 */}
      {backendOk === false && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          FastAPI 서버에 연결할 수 없습니다.{" "}
          <code className="rounded bg-red-100 px-1">uvicorn main:app --reload --port 8000</code>을 실행해 주세요.
        </div>
      )}

      {/* API Key 미설정 경고 */}
      {backendOk && currentProviderReady === false && (
        <div className="flex items-center gap-2 rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-800">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          {PROVIDER_CONFIG[provider].badge} API Key가 설정되지 않았습니다.{" "}
          <code className="rounded bg-yellow-100 px-1">backend/.env</code> 파일에{" "}
          <code className="rounded bg-yellow-100 px-1">{PROVIDER_CONFIG[provider].keyEnv}=...</code>를 추가하거나{" "}
          <a href="/settings" className="underline font-medium">설정 페이지</a>에서 입력해 주세요.
        </div>
      )}

      {/* Provider 선택 */}
      <div className="rounded-xl border border-gray-200 bg-white px-6 py-4 shadow-sm">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">분류 모델 선택</p>
        <div className="flex gap-3">
          {(["openai", "anthropic"] as ProviderType[]).map((p) => {
            const cfg = PROVIDER_CONFIG[p];
            const isActive = provider === p;
            return (
              <button
                key={p}
                onClick={() => { if (runState !== "running") setProvider(p); }}
                disabled={runState === "running"}
                className="flex items-center gap-2.5 rounded-lg border px-4 py-2.5 text-sm font-medium transition-all disabled:opacity-50"
                style={isActive
                  ? { backgroundColor: cfg.badgeColor, borderColor: cfg.badgeColor, color: "#fff" }
                  : { backgroundColor: "#fff", borderColor: "#D1D5DB", color: "#374151" }}
              >
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: isActive ? "#fff" : cfg.badgeColor }}
                />
                {cfg.label}
                {p === "openai" && openaiReady && (
                  <span className="ml-1 text-xs opacity-70">✓</span>
                )}
                {p === "anthropic" && anthropicReady && (
                  <span className="ml-1 text-xs opacity-70">✓</span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* 컨트롤 패널 */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex-1 space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">분류 대상</p>
            <p className="text-2xl font-bold text-gray-900">
              {selectedIds.size > 0 ? selectedIds.size : tasks.length}
              <span className="ml-1 text-sm font-normal text-gray-500">개 Task</span>
            </p>
            {selectedIds.size > 0 && (
              <button onClick={() => setSelectedIds(new Set())} className="text-xs hover:underline" style={{ color: "#A62121" }}>
                선택 해제 (전체 실행)
              </button>
            )}
          </div>

          <div className="flex gap-3">
            {runState !== "running" ? (
              <button
                onClick={handleStart}
                disabled={!canRun}
                className="flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium text-white shadow-sm disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                style={{ backgroundColor: canRun ? "#A62121" : "#A62121" }}
                onMouseEnter={(e) => { if (canRun) (e.currentTarget as HTMLElement).style.backgroundColor = "#8A1B1B"; }}
                onMouseLeave={(e) => { if (canRun) (e.currentTarget as HTMLElement).style.backgroundColor = "#A62121"; }}
              >
                <Play className="h-4 w-4" />
                {selectedIds.size > 0 ? "선택 분류" : "전체 분류"} 시작
              </button>
            ) : (
              <button
                onClick={handleStop}
                className="flex items-center gap-2 rounded-lg bg-red-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-red-700"
              >
                <Square className="h-4 w-4" />
                중단
              </button>
            )}
          </div>
        </div>

        {/* 진행 바 */}
        {(runState === "running" || runState === "done") && (
          <div className="mt-5 space-y-2">
            <div className="flex justify-between text-xs text-gray-500">
              <span className="flex items-center gap-2">
                {runState === "running" ? (
                  <>
                    <span className="inline-block h-2 w-2 rounded-full animate-pulse" style={{ backgroundColor: "#A62121" }} />
                    분류 중&nbsp;{progress.current} / {progress.total}개
                  </>
                ) : (
                  <>완료&nbsp;{progress.current} / {progress.total}개</>
                )}
              </span>
              <span className="flex items-center gap-3">
                {runState === "running" && remainingSec !== null && remainingSec > 0 && (
                  <span className="text-gray-400">{formatRemaining(remainingSec)}</span>
                )}
                <span className="font-medium" style={{ color: runState === "done" ? "#10B981" : "#A62121" }}>{pct}%</span>
              </span>
            </div>
            <div className="h-2.5 w-full rounded-full bg-gray-200">
              <div
                className="h-2.5 rounded-full transition-all duration-200"
                style={{ backgroundColor: runState === "done" ? "#10B981" : "#A62121", width: `${pct}%` }}
              />
            </div>

            {/* 실시간 통계 */}
            {Object.keys(liveResults).length > 0 && (
              <div className="flex flex-wrap gap-4 pt-2">
                <div className="flex items-center gap-2 rounded-lg bg-red-50 border border-red-200 px-3 py-1.5">
                  <span className="h-2 w-2 rounded-full bg-red-500" />
                  <span className="text-xs text-red-700 font-medium">AI 수행 가능</span>
                  <span className="text-sm font-bold text-red-800">{aiCount}</span>
                </div>
                <div className="flex items-center gap-2 rounded-lg bg-purple-50 border border-purple-200 px-3 py-1.5">
                  <span className="h-2 w-2 rounded-full bg-purple-500" />
                  <span className="text-xs text-purple-700 font-medium">AI + Human</span>
                  <span className="text-sm font-bold text-purple-800">{hybridCount}</span>
                </div>
                <div className="flex items-center gap-2 rounded-lg bg-emerald-50 border border-emerald-200 px-3 py-1.5">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  <span className="text-xs text-emerald-700 font-medium">인간 수행 필요</span>
                  <span className="text-sm font-bold text-emerald-800">{humanCount}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 완료 메시지 */}
        {runState === "done" && (
          <div className="mt-4 flex items-center justify-between gap-2 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
              분류 완료! &nbsp;<a href="/results" className="font-medium underline">결과 페이지</a>에서 확인하세요.
            </div>
            <button
              onClick={async () => {
                if (!confirm("이전 분류 결과를 초기화하고 다시 실행하시겠습니까?")) return;
                await deleteAllResults();
                setRunState("idle");
                setLiveResults({});
                setProgress({ current: 0, total: 0 });
              }}
              className="flex items-center gap-1 rounded px-2 py-1 text-xs text-emerald-700 hover:bg-emerald-100"
            >
              <Trash2 className="h-3.5 w-3.5" /> 결과 초기화 후 재실행
            </button>
          </div>
        )}

        {/* 에러 */}
        {runState === "error" && (
          <div className="mt-4 flex items-center gap-2 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            <AlertCircle className="h-5 w-5" />
            {errorMsg}
          </div>
        )}
      </div>

      {/* Task 선택 테이블 */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-gray-400" />
          <h2 className="text-sm font-medium text-gray-700">
            분류할 Task 선택 (체크하지 않으면 전체 처리)
          </h2>
        </div>
        <TaskTable
          rows={taskRows}
          showResult={Object.keys(liveResults).length > 0}
          selectable
          selectedIds={selectedIds}
          onSelectionChange={setSelectedIds}
        />
      </div>
    </div>
  );
}
