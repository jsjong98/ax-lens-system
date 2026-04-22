"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import {
  uploadWorkflow,
  uploadPptWorkflow,
  uploadWorkflowExcel,
  selectWorkflowExcelSheet,
  getWorkflowExcelTasks,
  getWorkflowSummary,
  benchmarkWorkflowStep1Stream,
  type BmProgressEvent,
  generateWorkflowStep1,
  chatWorkflowStep1,
  generateWorkflowStep2,
  getWorkflowStepResults,
  generateGapAnalysis,
  deleteBenchmarkRow,
  downloadBenchmarkTableXlsx,
  generateTobeFlow,
  getWorkflowResources,
  addUrlResource,
  addImageResource,
  deleteWorkflowResource,
  type UserResource,
  listWorkflowSessions,
  loadWorkflowSession,
  deleteWorkflowSession,
  listSessionFiles,
  selectWorkflowFile,
  renameWorkflowSession,
  saveCurrentSession,
  getSessionsOverview,
  getMe,
  type AuthUser,
  type WorkflowSummary,
  type WorkflowExcelTask,
  type WorkflowExcelUploadResult,
  type WorkflowStepResult,
  type BenchmarkTableRow,
  type SearchLogItem,
  type GapAnalysisResult,
  type TobeFlowResult,
  type WorkflowSession,
  type SessionFileInfo,
  type PMUserSessions,
} from "@/lib/api";
import { ToBeSwimlaneRF } from "@/components/tobe/ToBeSwimlaneRF";
import WorkflowEditor from "@/components/WorkflowEditor";
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
  // 시트별 벤치마킹 결과 {sheet_id: rows[]}
  const [benchmarkTableBySheet, setBenchmarkTableBySheet] = useState<Record<string, BenchmarkTableRow[]>>({});
  // 벤치마킹이 완료된 시트 ID — Gap 분석·기본 설계의 고정 스코프
  // (activeSheet는 "보기용 탭 선택"이고, bmSheetId는 "분석 범위"로 분리)
  const [bmSheetId, setBmSheetId] = useState<string | null>(null);
  const [bmLoading, setBmLoading] = useState(false);
  const [searchLog, setSearchLog] = useState<SearchLogItem[]>([]);
  const [showSearchLog, setShowSearchLog] = useState(false);
  const [bmProgressLog, setBmProgressLog] = useState<BmProgressEvent[]>([]);

  // Step 3: Step 2 상세 설계
  const [step2Result, setStep2Result] = useState<WorkflowStepResult | null>(null);

  // Gap 분석
  const [gapAnalysis, setGapAnalysis] = useState<GapAnalysisResult | null>(null);
  const [gapLoading, setGapLoading] = useState(false);

  // To-Be Swim Lane
  const [tobeFlow, setTobeFlow] = useState<TobeFlowResult | null>(null);
  const [tobeLoading, setTobeLoading] = useState(false);
  const [tobeActiveSheet, setTobeActiveSheet] = useState<number>(0);

  // 사용자 첨부 리소스
  const [userResources, setUserResources] = useState<UserResource[]>([]);
  const [resourceLoading, setResourceLoading] = useState(false);
  const [pendingImages, setPendingImages] = useState<Array<{ b64: string; type: string; name: string }>>([]);
  const [showResources, setShowResources] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // L3/L4 스코프 선택
  const [bmScope, setBmScope] = useState<"l3" | "l4">("l4");

  // 멀티 세션
  const [sessions, setSessions] = useState<WorkflowSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string>("");
  const [sessionLoading, setSessionLoading] = useState(false);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingSessionName, setEditingSessionName] = useState("");
  const [saveToast, setSaveToast] = useState("");

  // 파일 피커
  const [sessionFiles, setSessionFiles] = useState<SessionFileInfo[]>([]);
  const [showFilePicker, setShowFilePicker] = useState(false);
  const [filePickerLoading, setFilePickerLoading] = useState(false);

  // 로그인된 사용자 정보 (auth_store 기반)
  const [userId, setUserId] = useState<string>("");
  const [teamId, setTeamId] = useState<string>("");

  // PM 대시보드
  const [showPMDashboard, setShowPMDashboard] = useState(false);
  const [pmData, setPmData] = useState<PMUserSessions[]>([]);
  const [pmLoading, setPmLoading] = useState(false);

  // 공통
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // 로그인된 사용자 정보 초기화 — getMe()로 이름/프로젝트 가져오기
  useEffect(() => {
    getMe().then((me: AuthUser | null) => {
      if (me) {
        setUserId(me.name || "");
        setTeamId(me.project || "공통");
      }
    }).catch(() => {});
  }, []);

  // PM 대시보드 열기
  const handleOpenPMDashboard = useCallback(async () => {
    setShowPMDashboard(true);
    setPmLoading(true);
    try {
      const res = await getSessionsOverview();
      setPmData(res.users);
    } catch (e) {
      console.error("PM 대시보드 로드 실패", e);
    } finally {
      setPmLoading(false);
    }
  }, []);

  // 페이지 전체 Ctrl+V 이미지 감지 (textarea 포커스 없이도 동작)
  useEffect(() => {
    const handleGlobalPaste = async (e: ClipboardEvent) => {
      // 기본 텍스트 입력 필드에 붙여넣기 중이면 무시
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") return;
      // Step 1 (기본 설계) 화면일 때만 활성화
      if (currentStep !== 2) return;

      const items = Array.from(e.clipboardData?.items ?? []);
      const imageItem = items.find((it) => it.type.startsWith("image/"));
      if (!imageItem) return;

      e.preventDefault();
      const file = imageItem.getAsFile();
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        const b64 = (reader.result as string).split(",")[1];
        setPendingImages((prev) => [...prev, { b64, type: file.type, name: "screenshot.png" }]);
      };
      reader.readAsDataURL(file);
    };

    document.addEventListener("paste", handleGlobalPaste);
    return () => document.removeEventListener("paste", handleGlobalPaste);
  }, [currentStep]);

  // 세션 목록 로드
  const loadSessions = useCallback(async () => {
    try {
      const res = await listWorkflowSessions();
      setSessions(res.sessions);
      setCurrentSessionId(res.current || "");
    } catch (_) {}
  }, []);

  // 세션 전환
  const handleLoadSession = useCallback(async (sessionId: string) => {
    setSessionLoading(true);
    setError(null);
    try {
      await loadWorkflowSession(sessionId);
      setCurrentSessionId(sessionId);
      // 상태 초기화 후 새 세션 데이터 로드
      setExcelResult(null);
      setExcelTasks([]);
      setSummary(null);
      setStep1Result(null);
      setStep2Result(null);
      setBenchmarkTableBySheet({});
      setGapAnalysis(null);
      setChatMessages([]);
      setCurrentStep(0);
      // 복구된 세션의 워크플로우 + 태스크 불러오기
      const [ws, et, sr] = await Promise.allSettled([
        getWorkflowSummary(),
        getWorkflowExcelTasks(),
        getWorkflowStepResults(),
      ]);
      if (ws.status === "fulfilled") {
        setSummary(ws.value);
        if (ws.value.sheets.length > 0) setActiveSheet(ws.value.sheets[0].sheet_id);
        setCurrentStep(1);
      }
      if (et.status === "fulfilled" && et.value.total > 0) {
        setExcelTasks(et.value.tasks);
        setExcelResult({
          ok: true, filename: sessionId,
          task_count: et.value.total,
          has_classification: et.value.classified > 0,
          classified_count: et.value.classified,
          sheets: [],
        });
      }
      if (sr.status === "fulfilled") {
        const r = sr.value;
        if (r.has_step1 && r.step1) { setStep1Result(r.step1); setChatMessages(r.chat_history || []); setCurrentStep(2); }
        if (r.has_step2 && r.step2) { setStep2Result(r.step2); setCurrentStep(3); }
        // 벤치마킹·Gap 분석 결과 복원
        if (r.benchmark_table && Object.keys(r.benchmark_table).length > 0) {
          setBenchmarkTableBySheet(r.benchmark_table);
          // 분석 스코프 복원: 가장 많은 결과를 가진 시트 ID
          const topSheet = Object.entries(r.benchmark_table)
            .sort((a, b) => b[1].length - a[1].length)[0]?.[0];
          if (topSheet && topSheet !== "__default__") setBmSheetId(topSheet);
        }
        if (r.gap_analysis) {
          setGapAnalysis(r.gap_analysis);
        }
      }
      // 누적 리서치 자료 복원
      try {
        const rr = await getWorkflowResources();
        setUserResources(rr.resources);
      } catch { /* 무시 */ }
      await loadSessions();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSessionLoading(false);
    }
  }, [loadSessions]);

  // 새 프로젝트 모달 state
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  // 다음 엑셀 업로드 시 새로 생길 세션을 rename 할 pending 이름
  const [pendingProjectName, setPendingProjectName] = useState<string | null>(null);

  // 새 프로젝트 시작 — 이름 입력 모달 오픈
  const handleNewProject = useCallback(() => {
    // 기본 이름 제안: 현재 날짜 기반
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, "0");
    const suggested = `새 프로젝트 ${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`;
    setNewProjectName(suggested);
    setShowNewProjectModal(true);
  }, []);

  // 이름 확정 → 현재 세션 자동 저장 + 백엔드에 빈 세션 즉시 생성 + state 초기화
  const handleConfirmNewProject = useCallback(async () => {
    const name = newProjectName.trim();
    if (!name) return;

    // 현재 세션이 있으면 자동 저장 (데이터 유실 방지)
    if (currentSessionId) {
      try {
        await saveCurrentSession();
      } catch (e) {
        console.warn("현재 세션 저장 실패 (계속 진행):", e);
      }
    }

    setShowNewProjectModal(false);

    // state 초기화
    setExcelResult(null);
    setExcelTasks([]);
    setExcelSheets([]);
    setSummary(null);
    setPptResult(null);
    setStep1Result(null);
    setStep2Result(null);
    setBenchmarkTableBySheet({});
    setGapAnalysis(null);
    setTobeFlow(null);
    setTobeActiveSheet(0);
    setChatMessages([]);
    setChatInput("");
    setPendingImages([]);
    setUserResources([]);
    setShowResources(false);
    setSearchLog([]);
    setError(null);
    setCurrentStep(0);

    // 🔑 백엔드에 빈 세션 즉시 생성 → 프로젝트 목록에 바로 등록
    try {
      const { createWorkflowSession } = await import("@/lib/api");
      const created = await createWorkflowSession(name);
      setCurrentSessionId(created.session_id);
      setPendingProjectName(null);  // 이미 이름이 지정된 상태라 rename 불필요
      await loadSessions();         // 프로젝트 목록 즉시 갱신
    } catch (e) {
      console.warn("빈 세션 생성 실패 → 엑셀 업로드 시 fallback 생성:", e);
      // fallback: 엑셀 업로드 시 rename 시도
      setCurrentSessionId("");
      setPendingProjectName(name);
    }
  }, [newProjectName, currentSessionId, loadSessions]);

  // 현재 세션 저장
  const handleSaveSession = useCallback(async () => {
    if (!currentSessionId) return;
    try {
      const r = await saveCurrentSession();
      setSaveToast(`"${r.name}" 저장 완료`);
      setTimeout(() => setSaveToast(""), 2500);
    } catch (e) {
      setSaveToast(`저장 실패: ${(e as Error).message}`);
      setTimeout(() => setSaveToast(""), 3000);
    }
  }, [currentSessionId]);

  // 세션 이름 편집 시작
  const handleStartRename = useCallback((s: WorkflowSession) => {
    setEditingSessionId(s.id);
    setEditingSessionName(s.name || s.id);
  }, []);

  // 세션 이름 저장
  const handleConfirmRename = useCallback(async (sessionId: string) => {
    const name = editingSessionName.trim();
    if (!name) { setEditingSessionId(null); return; }
    try {
      await renameWorkflowSession(sessionId, name);
      setSessions((prev) => prev.map((s) => s.id === sessionId ? { ...s, name } : s));
    } catch (e) {
      console.error("이름 변경 실패", e);
    } finally {
      setEditingSessionId(null);
    }
  }, [editingSessionName]);

  // 세션 삭제
  const handleDeleteSession = useCallback(async (sessionId: string) => {
    if (!confirm(`"${sessionId}" 세션을 삭제할까요?`)) return;
    try {
      await deleteWorkflowSession(sessionId);
      if (sessionId === currentSessionId) {
        setCurrentSessionId("");
      }
      await loadSessions();
    } catch (e) {
      setError((e as Error).message);
    }
  }, [currentSessionId, loadSessions]);

  // 파일 피커 열기: 현재 세션의 Excel 목록 조회
  const handleOpenFilePicker = useCallback(async () => {
    if (!currentSessionId) return;
    setFilePickerLoading(true);
    try {
      const res = await listSessionFiles(currentSessionId);
      setSessionFiles(res.excels);
      setShowFilePicker(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setFilePickerLoading(false);
    }
  }, [currentSessionId]);

  // 파일 선택: 명시적으로 특정 Excel 로드
  const handleSelectFile = useCallback(async (filename: string) => {
    if (!currentSessionId) return;
    setLoading(true);
    setError(null);
    setShowFilePicker(false);
    try {
      const result = await selectWorkflowFile(currentSessionId, filename);
      setExcelResult(result);
      setExcelSheets(result.sheets);
      const tasks = await getWorkflowExcelTasks();
      setExcelTasks(tasks.tasks);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [currentSessionId]);

  // currentSessionId → localStorage 동기화 (새로고침 후 자동 복원용)
  useEffect(() => {
    if (currentSessionId) {
      localStorage.setItem("lastWorkflowSessionId", currentSessionId);
    }
  }, [currentSessionId]);

  // 이전 상태 복원
  useEffect(() => {
    const lastSessionId = localStorage.getItem("lastWorkflowSessionId");

    if (lastSessionId) {
      // 마지막 세션 자동 복원 (벤치마킹·Gap 등 모두 session_data.json에서 복구)
      loadWorkflowSession(lastSessionId)
        .then(() => {
          setCurrentSessionId(lastSessionId);
          return Promise.allSettled([
            getWorkflowSummary(),
            getWorkflowExcelTasks(),
            getWorkflowStepResults(),
            listWorkflowSessions(),
          ]);
        })
        .then((results) => {
          const [ws, et, sr, sl] = results;
          if (ws.status === "fulfilled" && ws.value.sheets.length > 0) {
            setSummary(ws.value);
            setActiveSheet(ws.value.sheets[0].sheet_id);
            setCurrentStep(1);
          }
          if (et.status === "fulfilled" && et.value.total > 0) {
            setExcelTasks(et.value.tasks);
            setExcelResult({
              ok: true, filename: lastSessionId,
              task_count: et.value.total,
              has_classification: et.value.classified > 0,
              classified_count: et.value.classified,
              sheets: [],
            });
          }
          if (sr.status === "fulfilled") {
            const r = sr.value;
            if (r.has_step1 && r.step1) { setStep1Result(r.step1); setChatMessages(r.chat_history || []); setCurrentStep(2); }
            if (r.has_step2 && r.step2) { setStep2Result(r.step2); setCurrentStep(3); }
            if (r.benchmark_table && Object.keys(r.benchmark_table).length > 0) {
              setBenchmarkTableBySheet(r.benchmark_table);
              const topSheet2 = Object.entries(r.benchmark_table)
                .sort((a, b) => b[1].length - a[1].length)[0]?.[0];
              if (topSheet2 && topSheet2 !== "__default__") setBmSheetId(topSheet2);
            }
            if (r.gap_analysis) setGapAnalysis(r.gap_analysis);
          }
          if (sl.status === "fulfilled") setSessions(sl.value.sessions);
        })
        .catch(() => {
          // 세션이 삭제됐거나 없는 경우 → 클리어 후 기존 방식 폴백
          localStorage.removeItem("lastWorkflowSessionId");
          loadSessions();
        });
    } else {
      // 저장된 세션 없음 → 백엔드 메모리에서 복원 시도 (서버 재시작 없는 경우)
      loadSessions();
      getWorkflowStepResults()
        .then((r) => {
          if (r.has_step2 && r.step2) setStep2Result(r.step2);
          if (r.has_step1 && r.step1) {
            setStep1Result(r.step1);
            setChatMessages(r.chat_history || []);
          }
          if (r.benchmark_table && Object.keys(r.benchmark_table).length > 0) {
            setBenchmarkTableBySheet(r.benchmark_table);
            const topSheet3 = Object.entries(r.benchmark_table)
              .sort((a, b) => b[1].length - a[1].length)[0]?.[0];
            if (topSheet3 && topSheet3 !== "__default__") setBmSheetId(topSheet3);
          }
          if (r.gap_analysis) setGapAnalysis(r.gap_analysis);
          if (r.has_excel) {
            getWorkflowExcelTasks()
              .then((et) => {
                if (et.total > 0) {
                  setExcelTasks(et.tasks);
                  setExcelResult({ ok: true, filename: "이전 업로드", task_count: et.total, has_classification: et.classified > 0, classified_count: et.classified, sheets: [] });
                }
              })
              .catch(() => {});
          }
          if (r.has_asis) {
            getWorkflowSummary()
              .then((ws) => { setSummary(ws); if (ws.sheets.length > 0) setActiveSheet(ws.sheets[0].sheet_id); })
              .catch(() => {});
          }
        })
        .catch(() => {});
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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

      // 새 프로젝트에서 시작한 경우: 백엔드가 생성한 새 세션을 pending 이름으로 rename
      const newSessionId = (result as { session_id?: string }).session_id;
      if (newSessionId) {
        setCurrentSessionId(newSessionId);
        if (pendingProjectName) {
          try {
            await renameWorkflowSession(newSessionId, pendingProjectName);
            await loadSessions();
          } catch (e) {
            console.warn("세션 이름 반영 실패:", e);
          } finally {
            setPendingProjectName(null);
          }
        }
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [pendingProjectName, loadSessions]);

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

  /* ── Step 2: 벤치마킹 (SSE 실시간 스트리밍) ─────────────── */
  const handleBenchmark = useCallback((companies?: string) => {
    setBmLoading(true);
    setError(null);
    setSearchLog([]);
    setShowSearchLog(true);
    setBmProgressLog([]);
    const loadingMsg = `벤치마킹 수행 중...${companies ? ` (기업: ${companies})` : " (Big Tech / Industry 선도사)"}`;
    setChatMessages((prev) => [...prev, { role: "system", content: loadingMsg }]);

    benchmarkWorkflowStep1Stream(
      { companies, sheet_id: activeSheet ?? undefined, scope: bmScope },
      (event) => {
        setBmProgressLog((prev) => [...prev, event]);
      },
      (result) => {
        const sheetKey = result.sheet_id ?? activeSheet ?? "__default__";
        setBenchmarkTableBySheet((prev) => ({ ...prev, [sheetKey]: result.benchmark_table }));
        // 벤치마킹 완료 시 분석 스코프 고정
        // - L4 단위: 해당 시트 ID로 고정 → Gap/기본설계가 그 L4 기준으로 실행
        // - L3 전체: null 유지 → Gap/기본설계가 sheet_id="" (전체) 기준으로 실행
        if (bmScope === "l4" && sheetKey !== "__default__") {
          setBmSheetId(sheetKey);
        } else {
          setBmSheetId(null); // L3 scope는 고정 시트 없음
        }

        if (result.search_log) setSearchLog(result.search_log);
        setChatMessages((prev) => [
          ...prev.filter((m) => m.content !== loadingMsg),
          { role: "assistant", content: `[벤치마킹 완료] ${result.result_count}개 사례 수집\n\n${result.summary}` },
        ]);
        setBmLoading(false);
      },
      (err) => {
        setError(err.message);
        setChatMessages((prev) => prev.filter((m) => m.content !== loadingMsg));
        setBmLoading(false);
      }
    );
  }, [activeSheet, bmScope]);

  /* ── Step 2: Step 1 기본 설계 생성 + 채팅 ──────────────── */
  const handleGenerateStep1 = useCallback(async (prompt?: string) => {
    setLoading(true);
    setError(null);
    try {
      // bmSheetId 우선: 벤치마킹 완료된 시트가 분석 스코프
      const step1Sheet = bmSheetId ?? activeSheet;
      const result = await generateWorkflowStep1({
        prompt: prompt || "선도사례를 분석하여 To-Be Workflow 기본 설계를 수행해주세요.",
        ...(step1Sheet ? { sheet_id: step1Sheet } : {}),
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
  }, [bmSheetId, activeSheet]);

  /* ── 사용자 리소스 핸들러 ──────────────────────────────────── */

  // 이미지 파일 → base64 변환
  const fileToBase64 = (file: File): Promise<string> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve((reader.result as string).split(",")[1]);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

  // 채팅 입력창 paste 이벤트 (이미지 붙여넣기)
  const handleChatPaste = useCallback(async (e: React.ClipboardEvent) => {
    const items = Array.from(e.clipboardData.items);
    const imageItem = items.find((it) => it.type.startsWith("image/"));
    if (!imageItem) return;
    e.preventDefault();
    const file = imageItem.getAsFile();
    if (!file) return;
    const b64 = await fileToBase64(file);
    setPendingImages((prev) => [...prev, { b64, type: file.type, name: file.name || "screenshot.png" }]);
  }, []);

  // 파일 선택 (paperclip 버튼)
  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    for (const file of files) {
      if (file.type.startsWith("image/")) {
        const b64 = await fileToBase64(file);
        setPendingImages((prev) => [...prev, { b64, type: file.type, name: file.name }]);
      }
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, []);

  // URL 첨부 — 채팅 메시지에 URL 포함 시 자동 처리
  const extractUrls = (text: string): string[] =>
    (text.match(/https?:\/\/[^\s]+/g) ?? []);

  // 메시지 전송 시 pending 이미지 + URL 먼저 처리
  const handleChatSend = useCallback(async () => {
    if (!chatInput.trim() && pendingImages.length === 0) return;
    setResourceLoading(true);

    // 1) pending 이미지 병렬 업로드 → Vision 분석 (N 장이면 N × 2-5초 → 한 라운드로)
    const addedResources: UserResource[] = [];
    if (pendingImages.length > 0) {
      // 업로드 시작 안내 — 여러 장일 때 사용자 체감 시간 단축
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `📎 ${pendingImages.length}장의 이미지를 병렬 분석 중... (Vision AI)`,
        },
      ]);
      const results = await Promise.allSettled(
        pendingImages.map((img) => addImageResource(img.b64, img.type, img.name))
      );
      for (let i = 0; i < results.length; i++) {
        const r = results[i];
        if (r.status === "fulfilled") {
          addedResources.push(r.value.resource);
          setUserResources((prev) => [...prev, r.value.resource]);
        } else {
          setChatMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: `이미지 ${i + 1} (${pendingImages[i].name}) 분석 실패: ${
                (r.reason as Error).message
              }`,
            },
          ]);
        }
      }
    }
    setPendingImages([]);

    // 2) 메시지 내 URL 병렬 크롤링
    const urls = extractUrls(chatInput);
    if (urls.length > 0) {
      const urlResults = await Promise.allSettled(urls.map((u) => addUrlResource(u)));
      for (let i = 0; i < urlResults.length; i++) {
        const r = urlResults[i];
        if (r.status === "fulfilled") {
          addedResources.push(r.value.resource);
          setUserResources((prev) => [...prev, r.value.resource]);
        } else {
          setChatMessages((prev) => [
            ...prev,
            { role: "assistant", content: `URL 접근 실패 (${urls[i]}): ${(r.reason as Error).message}` },
          ]);
        }
      }
    }
    setResourceLoading(false);

    // 3) 리소스가 추가됐으면 채팅 메시지에 요약 표시
    if (addedResources.length > 0) {
      const imageCount = addedResources.filter((r) => r.type === "image").length;
      const urlCount = addedResources.filter((r) => r.type === "url").length;
      const summary = addedResources
        .map((r) => `📎 [${r.type === "url" ? "URL" : "이미지"}] ${r.title}`)
        .join("\n");
      const countSummary = [
        imageCount > 0 ? `이미지 ${imageCount}장` : "",
        urlCount > 0 ? `URL ${urlCount}건` : "",
      ].filter(Boolean).join(" + ");
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            `${countSummary}을 리서치 라이브러리에 추가했습니다:\n${summary}\n\n` +
            `이 내용에서 벤치마킹 사례를 자동 추출해 벤치마킹 테이블에 반영하겠습니다. ` +
            `설계에 적용하려면 [기본 설계 재생성] 버튼을 눌러주세요.`,
        },
      ]);
      if (showResources === false) setShowResources(true);
    }

    // 4) 실제 채팅 전송 (원본 텍스트 그대로)
    if (chatInput.trim()) {
      const msg = chatInput;
      setChatInput("");
      setChatMessages((prev) => [...prev, { role: "user", content: msg }]);
      setLoading(true);
      try {
        const result = await chatWorkflowStep1(msg, activeSheet ?? undefined);
        setChatMessages((prev) => [...prev, { role: "assistant", content: result.message }]);
        if (result.updated && result.result) setStep1Result(result.result);
        if (result.benchmark_table && Object.keys(result.benchmark_table).length > 0) {
          setBenchmarkTableBySheet((prev) => ({ ...prev, ...result.benchmark_table }));
        }
      } catch (e) {
        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", content: `오류: ${(e as Error).message}` },
        ]);
      } finally {
        setLoading(false);
      }
    } else {
      setChatInput("");
    }
  }, [chatInput, pendingImages, activeSheet, showResources]);

  const handleDeleteResource = useCallback(async (idx: number) => {
    try {
      await deleteWorkflowResource(idx);
      setUserResources((prev) => prev.filter((_, i) => i !== idx));
    } catch (e) {
      console.error("리소스 삭제 실패", e);
    }
  }, []);

  /* ── Gap 분석 ───────────────────────────────────────────── */
  const handleGapAnalysis = useCallback(async () => {
    setGapLoading(true);
    setError(null);
    try {
      // bmSheetId 우선: 벤치마킹 완료된 시트가 분석 스코프
      const result = await generateGapAnalysis(bmSheetId ?? activeSheet ?? undefined);
      setGapAnalysis(result);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setGapLoading(false);
    }
  }, [bmSheetId, activeSheet]);

  /* ── To-Be Swim Lane 생성 ───────────────────────────────── */
  const handleGenerateTobeFlow = useCallback(async () => {
    setTobeLoading(true);
    setError(null);
    try {
      const tobeSheet = bmSheetId ?? activeSheet;
      const result = await generateTobeFlow(tobeSheet ? { sheet_id: tobeSheet } : undefined);
      setTobeFlow(result);
      setTobeActiveSheet(0);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setTobeLoading(false);
    }
  }, [bmSheetId, activeSheet]);

  /* ── Step 3: Step 2 상세 설계 생성 ──────────────────────── */
  const handleGenerateStep2 = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const step2Sheet = bmSheetId ?? activeSheet;
      const result = await generateWorkflowStep2({
        ...(step2Sheet ? { sheet_id: step2Sheet } : {}),
      });
      setStep2Result(result);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [bmSheetId, activeSheet]);

  const hasAsIs = summary || pptResult;
  const currentSheet = summary?.sheets.find((s) => s.sheet_id === activeSheet);
  // 분석 스코프 시트 (벤치마킹 완료 시트 → Gap/기본설계 고정 스코프)
  const analysisSheet = summary?.sheets.find((s) => s.sheet_id === bmSheetId);
  // 현재 시트의 벤치마킹 결과 (테이블 표시용) — bmSheetId 기준
  // L3 전체 scope면 "__default__" 키 fallback, 없으면 전체 시트 합산
  const benchmarkTable = bmSheetId
    ? (benchmarkTableBySheet[bmSheetId] ?? benchmarkTableBySheet[activeSheet ?? ""] ?? [])
    : (activeSheet
        ? (benchmarkTableBySheet[activeSheet]
            ?? benchmarkTableBySheet["__default__"]
            ?? Object.values(benchmarkTableBySheet).flat())
        : (benchmarkTableBySheet["__default__"] ?? Object.values(benchmarkTableBySheet).flat()));
  // 전체 시트 벤치마킹 건수 합산 (기본 설계 활성화 조건)
  const totalBenchmarkCount = Object.values(benchmarkTableBySheet).reduce((s, r) => s + r.length, 0);

  return (
    <div className="space-y-6">
      {/* ═══ 헤더 + 스텝 네비게이션 ═══ */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: PWC.primary }}>
            Workflow 설계
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            엑셀 업로드 → As-Is 워크플로우 연결 → 벤치마킹 기본 설계 → 상세 설계
          </p>
        </div>
        {/* 우상단 사용자 표시 */}
        <div
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold"
          style={{ borderColor: "#d1d5db", color: "#374151" }}
        >
          <span>👤</span>
          <span>{teamId && userId ? `${teamId} / ${userId}` : (userId || "로그인 필요")}</span>
        </div>
      </div>

      {/* ═══ 프로젝트 관리 바 ═══ */}
      <div className="rounded-xl border border-gray-200 bg-gray-50 overflow-hidden">
        {/* 헤더 행 */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-white">
          <span className="text-xs font-bold text-gray-600">📁 프로젝트</span>
          <div className="flex items-center gap-2">
            {/* PM 전체 보기 버튼 */}
            <button
              onClick={handleOpenPMDashboard}
              className="flex items-center gap-1 px-3 py-1 rounded-lg text-[11px] font-bold border transition hover:bg-gray-100"
              style={{ borderColor: "#6b7280", color: "#374151", backgroundColor: "#f9fafb" }}
              title="전체 사용자 프로젝트 현황 보기"
            >
              👥 전체 보기
            </button>
            {/* 저장 토스트 */}
            {saveToast && (
              <span className="text-[10px] font-semibold text-green-600 bg-green-50 px-2 py-0.5 rounded-full border border-green-200 animate-pulse">
                {saveToast}
              </span>
            )}
            {/* 현재 세션 저장 버튼 */}
            {currentSessionId && (
              <button
                onClick={handleSaveSession}
                className="flex items-center gap-1 px-3 py-1 rounded-lg text-[11px] font-bold border transition"
                style={{ borderColor: "#2563EB", color: "#2563EB", backgroundColor: "#EFF6FF" }}
                title="현재 작업 상태를 저장합니다"
              >
                💾 저장
              </button>
            )}
            {/* 새 프로젝트 버튼 */}
            <button
              onClick={handleNewProject}
              className="flex items-center gap-1 px-3 py-1 rounded-lg text-[11px] font-bold border-2 transition"
              style={{ borderColor: PWC.primary, color: PWC.primary, backgroundColor: PWC.bg }}
              title="현재 작업은 세션에 보관됩니다. 새 프로젝트를 시작합니다."
            >
              + 새 프로젝트
            </button>
          </div>
        </div>

        {/* 세션 목록 */}
        <div className="flex items-center gap-2 px-4 py-2.5 flex-wrap">
          {sessions.length === 0 && (
            <span className="text-[11px] text-gray-400">저장된 프로젝트가 없습니다. 엑셀/JSON을 업로드하면 자동 생성됩니다.</span>
          )}
          {sessions.map((s) => {
            const isCurrent = s.id === currentSessionId;
            const isEditing = editingSessionId === s.id;
            return (
              <div
                key={s.id}
                className="flex items-center gap-1 rounded-lg border text-xs px-2 py-1 group"
                style={{
                  background: isCurrent ? PWC.bg : "#fff",
                  borderColor: isCurrent ? PWC.primary : "#d1d5db",
                }}
              >
                {isEditing ? (
                  /* 이름 편집 모드 */
                  <input
                    autoFocus
                    value={editingSessionName}
                    onChange={(e) => setEditingSessionName(e.target.value)}
                    onBlur={() => handleConfirmRename(s.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleConfirmRename(s.id);
                      if (e.key === "Escape") setEditingSessionId(null);
                    }}
                    className="w-28 border-b border-blue-400 bg-transparent text-xs outline-none text-gray-800 font-semibold"
                  />
                ) : (
                  /* 일반 표시 모드 */
                  <button
                    onClick={() => isCurrent ? handleStartRename(s) : handleLoadSession(s.id)}
                    disabled={sessionLoading}
                    className="max-w-[140px] truncate text-left"
                    style={{ color: isCurrent ? PWC.primary : "#374151", fontWeight: isCurrent ? 700 : 400 }}
                    title={isCurrent ? "클릭하여 이름 편집" : s.name}
                  >
                    {isCurrent ? "✏️ " : ""}{s.name || s.id}
                  </button>
                )}
                {/* 삭제 버튼 (현재 세션 제외) */}
                {!isCurrent && (
                  <button
                    onClick={() => handleDeleteSession(s.id)}
                    className="ml-0.5 text-gray-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition leading-none"
                    title="삭제"
                  >×</button>
                )}
              </div>
            );
          })}
          {sessionLoading && <span className="text-[11px] text-gray-400 animate-pulse ml-2">불러오는 중…</span>}
        </div>
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

          {/* 이전 파일 불러오기 (세션이 있을 때만) */}
          {!excelResult && currentSessionId && (
            <div className="mt-2">
              {!showFilePicker ? (
                <button
                  onClick={handleOpenFilePicker}
                  disabled={filePickerLoading}
                  className="w-full py-2.5 rounded-lg border border-dashed border-gray-300 text-sm text-gray-500 hover:border-red-300 hover:text-red-600 hover:bg-red-50 transition disabled:opacity-50"
                >
                  {filePickerLoading ? "파일 목록 불러오는 중…" : "↑ 이 세션에 저장된 파일 불러오기"}
                </button>
              ) : (
                <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gray-50">
                    <span className="text-sm font-semibold text-gray-700">
                      [{currentSessionId}] 저장된 파일
                    </span>
                    <button
                      onClick={() => setShowFilePicker(false)}
                      className="text-gray-400 hover:text-gray-600 text-lg leading-none"
                    >
                      ×
                    </button>
                  </div>
                  {sessionFiles.length === 0 ? (
                    <p className="px-4 py-6 text-sm text-gray-400 text-center">저장된 Excel 파일이 없습니다.</p>
                  ) : (
                    <ul className="divide-y divide-gray-100">
                      {sessionFiles.map((f) => (
                        <li key={f.filename} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                          <div>
                            <p className="text-sm font-medium text-gray-800">{f.filename}</p>
                            <p className="text-xs text-gray-400">{f.size_kb} KB · {f.modified}</p>
                          </div>
                          <button
                            onClick={() => handleSelectFile(f.filename)}
                            className="px-3 py-1.5 rounded-lg text-xs font-bold text-white transition"
                            style={{ backgroundColor: f.is_current ? "#6b7280" : PWC.primary }}
                          >
                            {f.is_current ? "현재 파일" : "선택"}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
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
                          <span className="flex items-center gap-1.5">
                            {s.sheet_name || s.sheet_id}
                            {(benchmarkTableBySheet[s.sheet_id]?.length ?? 0) > 0 && (
                              <span className="inline-flex items-center justify-center px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-green-100 text-green-700">
                                {benchmarkTableBySheet[s.sheet_id].length}
                              </span>
                            )}
                          </span>
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
          {/* 헤더 카드 */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            {/* 타이틀 + 액션 버튼 행 */}
            <div className="flex items-start justify-between mb-5">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0" style={{ backgroundColor: PWC.primary }}>1</div>
                <div>
                  <div className="font-bold text-gray-800">선도사례 벤치마킹 기반 Workflow 기본 설계</div>
                  <div className="text-xs text-gray-500 mt-0.5 flex items-center gap-1.5">
                    <span className={`flex items-center gap-1 ${totalBenchmarkCount > 0 ? "text-green-600 font-semibold" : ""}`}>
                      {totalBenchmarkCount > 0 ? "✓" : "①"} 벤치마킹
                    </span>
                    <span className="text-gray-300">→</span>
                    <span className={`flex items-center gap-1 ${gapAnalysis ? "text-green-600 font-semibold" : totalBenchmarkCount > 0 ? "text-purple-600 font-semibold" : ""}`}>
                      {gapAnalysis ? "✓" : "②"} Gap 분석
                    </span>
                    <span className="text-gray-300">→</span>
                    <span className={`flex items-center gap-1 ${step1Result ? "text-green-600 font-semibold" : gapAnalysis ? "text-red-600 font-semibold" : ""}`}>
                      {step1Result ? "✓" : "③"} 기본 설계 생성
                    </span>
                  </div>
                </div>
              </div>
              {/* 분석 범위 배지 — bmSheetId 고정 시 표시 */}
              {analysisSheet && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-50 border border-blue-200 text-xs text-blue-700 font-semibold shrink-0" title="벤치마킹이 완료된 시트 — Gap 분석·기본 설계의 고정 분석 범위">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500 inline-block" />
                  분석 범위: {analysisSheet.sheet_name || analysisSheet.sheet_id}
                </div>
              )}
              {/* 버튼 그룹 — 스코프 토글 · 벤치마킹 · 기본 설계 생성 */}
              <div className="flex items-center gap-2 flex-shrink-0 ml-4">
                {/* L3/L4 스코프 토글 */}
                <div
                  className="flex items-center rounded-lg border border-gray-200 bg-gray-100 p-0.5"
                  title="L3: JSON 파일 전체 프로세스 | L4: 현재 탭 하나"
                >
                  <button
                    onClick={() => setBmScope("l3")}
                    className={`px-3 py-1 rounded-md text-xs font-semibold transition ${
                      bmScope === "l3" ? "bg-white text-blue-700 shadow-sm" : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    L3 전체
                  </button>
                  <button
                    onClick={() => setBmScope("l4")}
                    className={`px-3 py-1 rounded-md text-xs font-semibold transition ${
                      bmScope === "l4" ? "bg-white text-blue-700 shadow-sm" : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    L4 단위
                  </button>
                </div>
                {/* 벤치마킹 버튼 */}
                <button
                  onClick={() => handleBenchmark()}
                  disabled={bmLoading || loading}
                  className="px-4 py-2 rounded-lg text-sm font-bold border-2 transition disabled:opacity-50 whitespace-nowrap"
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
                    `✓ 벤치마킹 완료 (${benchmarkTable.length}건)${totalBenchmarkCount > benchmarkTable.length ? ` / 전체 ${totalBenchmarkCount}건` : ""}`
                  ) : (
                    "\uD83D\uDD0D 벤치마킹 수행"
                  )}
                </button>
                {/* 기본 설계 생성 버튼 — 벤치마킹+Gap분석 완료 시 활성화, 없으면 Step 2로 이동 */}
                {totalBenchmarkCount > 0 ? (
                  <button
                    onClick={() => handleGenerateStep1()}
                    disabled={loading || bmLoading || !gapAnalysis}
                    title={!gapAnalysis ? "Gap 분석을 먼저 수행해주세요" : ""}
                    className="px-4 py-2 rounded-lg text-sm font-bold text-white transition disabled:opacity-50 whitespace-nowrap"
                    style={{ backgroundColor: step1Result ? "#15803D" : gapAnalysis ? PWC.primary : "#9CA3AF" }}
                  >
                    {loading ? (
                      <span className="flex items-center gap-2">
                        <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-red-300 border-t-white" />
                        설계 중...
                      </span>
                    ) : step1Result ? (
                      "↺ 기본 설계 재생성"
                    ) : !gapAnalysis ? (
                      "✏️ 기본 설계 생성 (Gap 분석 필요)"
                    ) : (
                      "✏️ 기본 설계 생성"
                    )}
                  </button>
                ) : (
                  <button
                    onClick={() => setCurrentStep(3)}
                    disabled={loading || bmLoading}
                    className="px-4 py-2 rounded-lg text-sm font-bold text-white transition disabled:opacity-50 whitespace-nowrap"
                    style={{ backgroundColor: "#7C3AED" }}
                  >
                    Step 2 Bottom-up 분석으로 이동 →
                  </button>
                )}
              </div>
            </div>

            {/* 검색 과정 — 실시간 라이브 로그 (검색 중) or 완료 후 토글 */}
            {(bmLoading || searchLog.length > 0) && (
              <div className="mb-4 rounded-lg border overflow-hidden"
                style={{ borderColor: bmLoading ? "#6366F1" : "#E5E7EB" }}>
                <button
                  onClick={() => !bmLoading && setShowSearchLog((v) => !v)}
                  className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium transition"
                  style={{
                    background: bmLoading ? "#EEF2FF" : "#F9FAFB",
                    color: bmLoading ? "#4338CA" : "#4B5563",
                    cursor: bmLoading ? "default" : "pointer",
                  }}
                >
                  <span className="flex items-center gap-2">
                    {bmLoading && (
                      <span className="inline-block h-3 w-3 rounded-full border-2 border-indigo-300 border-t-indigo-600 animate-spin" />
                    )}
                    {bmLoading
                      ? (() => {
                          const last = bmProgressLog[bmProgressLog.length - 1];
                          if (!last) return "검색 엔진 초기화 중...";
                          if (last.type === "engine") return `${last.text}`;
                          if (last.type === "plan") return `${last.text}`;
                          if (last.type === "queries") return `R${last.round} 쿼리 ${last.count}개 생성 완료 — 병렬 검색 시작`;
                          if (last.type === "round_start") return `R${last.round} 병렬 검색 중 (${last.count}개 쿼리)...`;
                          if (last.type === "query_done") return `R${last.round} 검색 중 — ${last.idx}/${last.total} 완료 (+${last.found}건)`;
                          if (last.type === "round_end") return `R${last.round} 완료 — ${last.collected}건 수집`;
                          if (last.type === "embed") return last.text ?? "임베딩 재랭킹 중...";
                          if (last.type === "done_search") return `검색 완료 — 총 ${last.total}건 수집, Claude AI 분석 중...`;
                          if (last.type === "llm_analyze") return `Claude AI 분석 중 (${last.total}건 처리)...`;
                          return "처리 중...";
                        })()
                      : `검색 과정 보기 (${searchLog.length}단계)`}
                  </span>
                  {!bmLoading && <span>{showSearchLog ? "▲" : "▼"}</span>}
                </button>

                {/* 실시간 로그 (검색 중에는 항상 표시) */}
                {(bmLoading || showSearchLog) && (
                  <div className="max-h-[300px] overflow-y-auto px-3 py-2 space-y-0.5 bg-white font-mono text-[11px]">
                    {bmProgressLog.map((ev, i) => {
                      if (ev.type === "engine") {
                        return (
                          <div key={i} className="text-blue-700 font-bold py-0.5">
                            🔍 {ev.text}
                          </div>
                        );
                      }
                      if (ev.type === "plan") {
                        return (
                          <div key={i} className="text-indigo-700 font-semibold py-0.5 mt-1">
                            ◆ {ev.text}
                          </div>
                        );
                      }
                      if (ev.type === "queries") {
                        return (
                          <div key={i} className="pl-3 py-0.5">
                            <div className="text-indigo-500 font-semibold mb-0.5">R{ev.round} 쿼리 {ev.count}개:</div>
                            {ev.queries?.map((q, qi) => (
                              <div key={qi} className="text-gray-500 pl-2 leading-snug">· {q}</div>
                            ))}
                          </div>
                        );
                      }
                      if (ev.type === "round_start") {
                        return (
                          <div key={i} className="text-indigo-600 font-semibold py-0.5 mt-1">
                            ▶ Round {ev.round} 시작 — {ev.count}개 쿼리 병렬 검색
                          </div>
                        );
                      }
                      if (ev.type === "query_done") {
                        return (
                          <div key={i} className="pl-3 text-gray-500 leading-snug py-0.5">
                            <span className="text-indigo-400">[R{ev.round} {ev.idx}/{ev.total}]</span>{" "}
                            {ev.query}{" "}
                            <span className={ev.found && ev.found > 0 ? "text-green-600 font-semibold" : "text-gray-400"}>
                              → {ev.found}건
                            </span>
                          </div>
                        );
                      }
                      if (ev.type === "round_end") {
                        return (
                          <div key={i} className="text-indigo-700 font-semibold py-0.5">
                            ◀ Round {ev.round} 완료 — 누적 {ev.collected}건
                          </div>
                        );
                      }
                      if (ev.type === "embed") {
                        return (
                          <div key={i} className="text-purple-600 py-0.5">
                            ✦ {ev.text}
                          </div>
                        );
                      }
                      if (ev.type === "done_search") {
                        return (
                          <div key={i} className="text-green-700 font-bold py-0.5 mt-1">
                            ✅ 검색 완료 — 총 {ev.total}건 수집 (상위 {ev.final}건 분석)
                          </div>
                        );
                      }
                      if (ev.type === "llm_analyze") {
                        return (
                          <div key={i} className="text-orange-600 font-semibold py-0.5">
                            🤖 Claude AI 분석 중 — {ev.total}건 처리...
                          </div>
                        );
                      }
                      return null;
                    })}
                    {bmLoading && (
                      <div className="text-gray-400 animate-pulse py-0.5">▌</div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* 벤치마킹 결과 테이블 */}
            {benchmarkTable.length > 0 && (
              <div className="mb-5">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-xs font-bold text-gray-700">벤치마킹 결과표</div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={async () => {
                        try { await downloadBenchmarkTableXlsx(); }
                        catch (e) { alert((e as Error).message); }
                      }}
                      className="flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-bold text-green-700 border border-green-300 bg-green-50 hover:bg-green-100 transition whitespace-nowrap"
                    >
                      ⬇ xlsx
                    </button>
                  </div>
                </div>
                <div className="overflow-x-auto rounded-lg border border-blue-200">
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
                        <th className="text-left px-3 py-2 font-medium text-blue-800 whitespace-nowrap">출처</th>
                        <th className="px-2 py-2 text-blue-800 whitespace-nowrap"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {benchmarkTable.map((row, i) => (
                        <tr key={i} className="border-b border-blue-100 hover:bg-blue-50/50 group">
                          <td className="px-3 py-2 font-medium text-gray-800 whitespace-nowrap">{row.source}</td>
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
                          <td className="px-3 py-2 whitespace-nowrap">
                            {row.url ? (
                              <a href={row.url} target="_blank" rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-blue-600 hover:underline text-[10px]">
                                🔗 링크
                              </a>
                            ) : (
                              <span className="text-gray-300 text-[10px]">없음</span>
                            )}
                          </td>
                          <td className="px-2 py-2 text-center">
                            <button
                              title={`"${row.source}" 행 삭제`}
                              onClick={async () => {
                                if (!confirm(`"${row.source}" 행을 삭제하시겠습니까?`)) return;
                                try {
                                  const res = await deleteBenchmarkRow(row.source, activeSheet ?? undefined);
                                  setBenchmarkTableBySheet(res.benchmark_table);
                                } catch (e) {
                                  alert((e as Error).message);
                                }
                              }}
                              className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-red-50 text-red-400 hover:text-red-600"
                            >
                              ✕
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Gap 분석 섹션 */}
            {totalBenchmarkCount > 0 && (
              <div className="mb-5">
                <div className="border-t border-gray-200 pt-4 mt-2">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-gray-700">Gap 분석</span>
                      <span className="text-[10px] text-gray-400">— 선도사 To-Be vs 두산 As-Is 비교</span>
                    </div>
                    <button
                      onClick={handleGapAnalysis}
                      disabled={gapLoading || bmLoading || loading}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold border-2 transition disabled:opacity-50 whitespace-nowrap"
                      style={{
                        borderColor: gapAnalysis ? "#16A34A" : "#7C3AED",
                        color: gapAnalysis ? "#16A34A" : "#7C3AED",
                        backgroundColor: gapAnalysis ? "#F0FDF4" : "#F5F3FF",
                      }}
                    >
                      {gapLoading ? (
                        <span className="flex items-center gap-1.5">
                          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-purple-300 border-t-purple-600" />
                          분석 중...
                        </span>
                      ) : gapAnalysis ? (
                        "↺ Gap 분석 재수행"
                      ) : (
                        "⚡ Gap 분석 수행"
                      )}
                    </button>
                  </div>

                  {gapAnalysis && (
                    <div className="space-y-4">
                      {/* Executive Summary 카드 */}
                      <div className="rounded-lg border border-purple-200 bg-purple-50 px-4 py-3">
                        <div className="flex items-center gap-2 mb-1.5">
                          <span className="text-xs font-bold text-purple-800">종합 요약</span>
                          {/* Gap 유형 분포 배지 */}
                          {gapAnalysis.gap_items && (() => {
                            const counts = { A: 0, B: 0, C: 0 };
                            gapAnalysis.gap_items.forEach((it) => {
                              if (it.gap_type?.startsWith("A")) counts.A++;
                              else if (it.gap_type?.startsWith("B")) counts.B++;
                              else if (it.gap_type?.startsWith("C")) counts.C++;
                            });
                            return (
                              <div className="flex gap-1">
                                {counts.A > 0 && <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-700">A.신규 {counts.A}</span>}
                                {counts.B > 0 && <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-700">B.전환 {counts.B}</span>}
                                {counts.C > 0 && <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-gray-200 text-gray-600">C.폐기/통합 {counts.C}</span>}
                              </div>
                            );
                          })()}
                        </div>
                        <p className="text-xs text-purple-900 leading-relaxed">{gapAnalysis.executive_summary}</p>
                      </div>

                      {/* Gap 유형 범례 */}
                      <div className="flex gap-3 text-[10px] text-gray-500">
                        <span className="flex items-center gap-1"><span className="px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-bold">A. 신규</span> 벤치마킹에만 존재 — 도입 검토</span>
                        <span className="flex items-center gap-1"><span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-bold">B. 전환</span> 양쪽 존재, 방식 차이 — AI 전환 검토</span>
                        <span className="flex items-center gap-1"><span className="px-1.5 py-0.5 rounded bg-gray-200 text-gray-600 font-bold">C. 폐기/통합</span> As-Is에만 존재 — 존치 재검토</span>
                      </div>

                      {/* Gap 항목 카드 */}
                      {gapAnalysis.gap_items && gapAnalysis.gap_items.length > 0 && (
                        <div className="grid grid-cols-2 gap-3">
                          {[...gapAnalysis.gap_items]
                            .sort((a, b) => a.priority - b.priority)
                            .map((item, i) => {
                              const isA = item.gap_type?.startsWith("A");
                              const isB = item.gap_type?.startsWith("B");
                              const typeColor = isA
                                ? { bar: "bg-blue-500", badge: "bg-blue-100 text-blue-700", light: "bg-blue-50", border: "border-blue-200" }
                                : isB
                                ? { bar: "bg-amber-500", badge: "bg-amber-100 text-amber-700", light: "bg-amber-50", border: "border-amber-200" }
                                : { bar: "bg-gray-400", badge: "bg-gray-100 text-gray-600", light: "bg-gray-50", border: "border-gray-200" };
                              const priColor = item.priority === 1
                                ? "bg-red-500 text-white"
                                : item.priority === 2
                                ? "bg-amber-400 text-white"
                                : "bg-gray-300 text-gray-600";
                              return (
                                <div key={i} className={`rounded-xl border ${typeColor.border} overflow-hidden`}>
                                  {/* 상단 헤더 */}
                                  <div className={`${typeColor.bar} h-1`} />
                                  <div className="flex items-center justify-between px-4 py-2.5 bg-white border-b border-gray-100">
                                    <span className="text-sm font-bold text-gray-800">{item.l4_activity}</span>
                                    <div className="flex items-center gap-1.5">
                                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${typeColor.badge}`}>
                                        {item.gap_type ?? "-"}
                                      </span>
                                      <span className={`inline-flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-bold ${priColor}`}>
                                        P{item.priority}
                                      </span>
                                    </div>
                                  </div>
                                  {/* As-Is / To-Be */}
                                  <div className="grid grid-cols-2 divide-x divide-gray-100 bg-white">
                                    <div className="px-4 py-2.5">
                                      <div className="text-[9px] font-bold text-gray-400 uppercase tracking-wide mb-1">As-Is</div>
                                      <p className="text-[11px] text-gray-600 leading-snug">{item.as_is}</p>
                                    </div>
                                    <div className="px-4 py-2.5">
                                      <div className="text-[9px] font-bold text-blue-400 uppercase tracking-wide mb-1">To-Be</div>
                                      <p className="text-[11px] text-blue-700 leading-snug">{item.to_be}</p>
                                    </div>
                                  </div>
                                  {/* 원인 + Action Plan */}
                                  <div className={`${typeColor.light} px-4 py-2.5 space-y-1.5`}>
                                    <div className="flex items-start gap-2">
                                      <span className="text-[9px] font-bold text-gray-400 uppercase tracking-wide whitespace-nowrap mt-0.5">원인</span>
                                      <span className="text-[11px] text-gray-600">{item.root_cause}</span>
                                    </div>
                                    <div className="flex items-start gap-2">
                                      <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wide whitespace-nowrap mt-0.5">Action</span>
                                      <span className="text-[11px] text-gray-800 font-medium">{item.action_plan}</span>
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                        </div>
                      )}

                      {/* Gap Wrap-up: 프로세스 / 인프라 / 데이터 — MBB 스타일 */}
                      {gapAnalysis.gap_wrap_up && (() => {
                        const wu = gapAnalysis.gap_wrap_up!;
                        type DimCfg = {
                          key: "process_gap" | "infra_gap" | "data_gap";
                          label: string;
                          icon: string;
                          accent: string;
                          headlineBg: string;
                          headlineText: string;
                          border: string;
                          bg: string;
                        };
                        const dimCfg: DimCfg[] = [
                          { key: "process_gap", label: "프로세스 Gap", icon: "⚙️",
                            accent: "violet", headlineBg: "bg-violet-600", headlineText: "text-white",
                            border: "border-violet-200", bg: "bg-violet-50" },
                          { key: "infra_gap", label: "인프라 Gap", icon: "🏗️",
                            accent: "orange", headlineBg: "bg-orange-500", headlineText: "text-white",
                            border: "border-orange-200", bg: "bg-orange-50" },
                          { key: "data_gap", label: "데이터 Gap", icon: "📊",
                            accent: "cyan", headlineBg: "bg-cyan-600", headlineText: "text-white",
                            border: "border-cyan-200", bg: "bg-cyan-50" },
                        ];
                        const activeDims = dimCfg.filter(d => wu[d.key]);
                        if (activeDims.length === 0) return null;

                        return (
                          <div>
                            <div className="text-xs font-bold text-gray-700 mb-2">Gap 종합 분석</div>
                            <div className={`grid gap-3 ${activeDims.length === 1 ? "grid-cols-1" : activeDims.length === 2 ? "grid-cols-2" : "grid-cols-3"}`}>
                              {activeDims.map(d => {
                                const raw = wu[d.key];
                                // 구조화된 객체인지 판별
                                const isObj = raw && typeof raw === "object" && !Array.isArray(raw) && "headline" in raw;
                                const dim = isObj ? (raw as { headline: string; as_is: string; to_be: string; gaps: string[]; implication: string }) : null;

                                return (
                                  <div key={d.key} className={`rounded-xl border ${d.border} overflow-hidden`}>
                                    {/* 헤더 — 컬러 배너 */}
                                    <div className={`${d.headlineBg} px-4 py-2.5`}>
                                      <div className={`text-[10px] font-semibold ${d.headlineText} opacity-80 mb-0.5`}>
                                        {d.icon} {d.label}
                                      </div>
                                      <div className={`text-sm font-bold ${d.headlineText} leading-snug`}>
                                        {dim ? dim.headline : (typeof raw === "string" ? raw.slice(0, 40) : "")}
                                      </div>
                                    </div>

                                    {/* 바디 */}
                                    {dim ? (
                                      <div className={`${d.bg} px-4 py-3 space-y-2.5`}>
                                        {/* As-Is / To-Be */}
                                        <div className="grid grid-cols-2 gap-2">
                                          <div>
                                            <div className="text-[9px] font-bold text-gray-500 uppercase tracking-wide mb-0.5">As-Is</div>
                                            <p className="text-[11px] text-gray-700 leading-snug">{dim.as_is}</p>
                                          </div>
                                          <div>
                                            <div className="text-[9px] font-bold text-gray-500 uppercase tracking-wide mb-0.5">To-Be</div>
                                            <p className="text-[11px] text-gray-700 leading-snug">{dim.to_be}</p>
                                          </div>
                                        </div>
                                        {/* 핵심 Gap 포인트 */}
                                        <div>
                                          <div className="text-[9px] font-bold text-gray-500 uppercase tracking-wide mb-1">핵심 Gap</div>
                                          <div className="flex flex-wrap gap-1.5">
                                            {dim.gaps.map((g, gi) => (
                                              <span key={gi} className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-white border border-gray-300 text-gray-700">
                                                {g}
                                              </span>
                                            ))}
                                          </div>
                                        </div>
                                        {/* 시사점 */}
                                        <div className="border-t border-gray-200 pt-2">
                                          <div className="text-[9px] font-bold text-gray-500 uppercase tracking-wide mb-0.5">시사점</div>
                                          <p className="text-[11px] text-gray-800 font-medium leading-snug">{dim.implication}</p>
                                        </div>
                                      </div>
                                    ) : (
                                      <div className={`${d.bg} px-4 py-3`}>
                                        <p className="text-xs text-gray-700 leading-relaxed">{typeof raw === "string" ? raw : ""}</p>
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        );
                      })()}

                      {/* Quick Wins & Strategic Actions */}
                      <div className="grid grid-cols-2 gap-3">
                        {gapAnalysis.quick_wins && gapAnalysis.quick_wins.length > 0 && (
                          <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3">
                            <div className="text-xs font-bold text-green-800 mb-2">Quick Wins — 단기 (6개월 내)</div>
                            <ul className="space-y-1">
                              {gapAnalysis.quick_wins.map((w: string, i: number) => (
                                <li key={i} className="flex items-start gap-1.5 text-xs text-green-900">
                                  <span className="text-green-500 shrink-0 mt-0.5">✓</span>
                                  <span>{w}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {gapAnalysis.strategic_actions && gapAnalysis.strategic_actions.length > 0 && (
                          <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
                            <div className="text-xs font-bold text-blue-800 mb-2">Strategic Actions — 장기 (5년)</div>
                            <ul className="space-y-1">
                              {gapAnalysis.strategic_actions.map((a: string, i: number) => (
                                <li key={i} className="flex items-start gap-1.5 text-xs text-blue-900">
                                  <span className="text-blue-500 shrink-0 mt-0.5">→</span>
                                  <span>{a}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 채팅 영역 — 항상 리서치·질문 전용 */}
            <div className="border border-gray-200 rounded-lg bg-gray-50" style={{ display: "flex", flexDirection: "column" }}>
              {/* 채팅 헤더 레이블 */}
              <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-white rounded-t-lg">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-gray-500">리서치 채팅</span>
                  <span className="text-[10px] text-gray-400">— URL·이미지 첨부 가능, 벤치마킹 질문·추가 사례 요청</span>
                </div>
                {userResources.length > 0 && (
                  <button
                    onClick={() => setShowResources((v) => !v)}
                    className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-semibold text-blue-600 bg-blue-50 border border-blue-200 hover:bg-blue-100 transition"
                  >
                    📚 리서치 자료 {userResources.length}건 {showResources ? "▲" : "▼"}
                  </button>
                )}
              </div>
              {/* 누적 리서치 자료 패널 */}
              {showResources && userResources.length > 0 && (
                <div className="border-b border-gray-200 bg-white px-4 py-3 space-y-2 max-h-48 overflow-y-auto">
                  <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wide mb-1">누적 리서치 자료</p>
                  {userResources.map((res, idx) => (
                    <div key={idx} className="flex items-start gap-2 p-2 rounded-lg border border-gray-100 bg-gray-50 group">
                      <span className="text-lg shrink-0">{res.type === "url" ? "🔗" : "🖼"}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-gray-700 truncate">{res.title}</p>
                        <p className="text-[10px] text-gray-400 truncate">{res.source}</p>
                        <p className="text-[10px] text-gray-500 mt-0.5 line-clamp-2">{res.content.slice(0, 120)}...</p>
                      </div>
                      <button
                        onClick={() => handleDeleteResource(idx)}
                        className="shrink-0 opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-400 transition text-sm"
                        title="삭제"
                      >✕</button>
                    </div>
                  ))}
                </div>
              )}

              {/* 메시지 목록 */}
              <div className="overflow-y-auto p-4 space-y-3" style={{ height: "260px" }}>
                {chatMessages.length === 0 && (
                  <div className="text-center py-6 text-gray-400 text-sm">
                    <div className="text-2xl mb-2">&#128269;</div>
                    <p className="text-xs">벤치마킹 결과 질문, 추가 사례 요청, 또는 리서치 자료를 첨부하세요.</p>
                    <p className="text-xs mt-1 text-gray-300">📎 URL 붙여넣기 → 자동 크롤링 &nbsp;|&nbsp; 🖼 이미지 Ctrl+V 또는 파일 첨부 → Vision 분석</p>
                    <p className="text-xs mt-2 text-gray-300">충분히 검토한 뒤 오른쪽 위 <strong className="text-gray-400">기본 설계 생성</strong> 버튼을 누르세요.</p>
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
                      <div className="whitespace-pre-wrap">{msg.content}</div>
                    </div>
                  </div>
                ))}
                {(loading || bmLoading || resourceLoading) && currentStep === 2 && (
                  <div className="flex justify-start">
                    <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
                      <div className="flex items-center gap-2 text-sm text-gray-500">
                        <div className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-red-600" />
                        {resourceLoading ? "자료 분석 중 (URL 크롤링 / 이미지 Vision)..." : bmLoading ? "벤치마킹 검색 중..." : loading ? "AI 처리 중..." : ""}
                      </div>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* 입력 영역 */}
              <div className="border-t border-gray-200 p-3 bg-white rounded-b-lg space-y-2">
                {/* pending 이미지 미리보기 */}
                {pendingImages.length > 0 && (
                  <div className="flex gap-2 flex-wrap">
                    {pendingImages.map((img, i) => (
                      <div key={i} className="relative group">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={`data:${img.type};base64,${img.b64}`}
                          alt={img.name}
                          className="h-14 w-14 object-cover rounded-lg border border-gray-200"
                        />
                        <button
                          onClick={() => setPendingImages((prev) => prev.filter((_, j) => j !== i))}
                          className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center opacity-0 group-hover:opacity-100 transition"
                        >✕</button>
                        <p className="text-[9px] text-gray-400 text-center truncate w-14">{img.name}</p>
                      </div>
                    ))}
                  </div>
                )}
                <div className="flex gap-2 items-end">
                  {/* 파일 첨부 버튼 */}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    multiple
                    className="hidden"
                    onChange={handleFileSelect}
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    title="이미지 파일 첨부"
                    className="shrink-0 p-2 rounded-lg border border-gray-200 text-gray-400 hover:text-blue-500 hover:border-blue-300 transition"
                  >
                    📎
                  </button>
                  <textarea
                    rows={2}
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onPaste={handleChatPaste}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleChatSend();
                      }
                    }}
                    placeholder="질문, URL 붙여넣기, 또는 이미지 Ctrl+V... (Shift+Enter 줄바꿈)"
                    className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-red-300 resize-none"
                    disabled={loading || bmLoading || resourceLoading}
                  />
                  <button
                    onClick={handleChatSend}
                    disabled={loading || bmLoading || resourceLoading || (!chatInput.trim() && pendingImages.length === 0)}
                    className="shrink-0 px-4 py-2 rounded-lg text-sm font-bold text-white transition disabled:opacity-50"
                    style={{ backgroundColor: PWC.primary }}
                  >
                    전송
                  </button>
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
              <div className="flex justify-end items-center">
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
                    {/* Senior AI를 맨 위에 풀 스팬으로 표시 */}
                    {step2Result.agents.filter((a) => a.agent_type === "Senior AI").map((agent) => (
                      <div key={agent.agent_id} className="rounded-xl p-4 border-2" style={{ borderColor: "#8B1A1A", backgroundColor: "#FFF5F5" }}>
                        <div className="flex items-center gap-2 mb-2 flex-wrap">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white" style={{ backgroundColor: "#8B1A1A" }}>
                            Senior AI · 오케스트레이터
                          </span>
                          <span className="text-sm font-bold" style={{ color: "#8B1A1A" }}>{agent.agent_name}</span>
                          <span className="text-[10px] text-gray-400">{agent.ai_technique}</span>
                        </div>
                        <p className="text-xs mb-3" style={{ color: "#8B1A1A" }}>{agent.description}</p>
                        {/* 담당 Junior AI 목록 표시 */}
                        <div className="flex flex-wrap gap-1 mt-1">
                          {step2Result.agents.filter((a) => a.agent_type === "Junior AI").map((j, idx) => (
                            <span key={j.agent_id} className="text-[9px] font-semibold px-2 py-0.5 rounded border" style={{ borderColor: "#8B1A1A", color: "#8B1A1A" }}>
                              {"①②③④⑤⑥⑦⑧⑨⑩"[idx]} {j.agent_name} 지시
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                    {/* Junior AI 및 나머지 */}
                    {step2Result.agents.filter((a) => a.agent_type !== "Senior AI").map((agent) => (
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

              {/* ── To-Be Workflow Swim Lane ── */}
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <span className="text-sm font-bold text-gray-800">To-Be Workflow 다이어그램</span>
                    <span className="ml-2 text-xs text-gray-400">— 상세 설계 기반 L4(시트) 단위 Swim Lane</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {tobeFlow && (
                      <>
                        <button
                          onClick={async () => {
                            try {
                              const { downloadTobeDesignExcel } = await import("@/lib/api");
                              await downloadTobeDesignExcel();
                            } catch (e) {
                              setError((e as Error).message);
                            }
                          }}
                          className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-bold border-2 border-amber-600 text-amber-700 bg-amber-50 hover:bg-amber-100 transition whitespace-nowrap"
                        >
                          ⬇ 템플릿 Excel
                        </button>
                        <button
                          onClick={async () => {
                            try {
                              const { downloadTobeFlowJson } = await import("@/lib/api");
                              await downloadTobeFlowJson();
                            } catch (e) {
                              setError((e as Error).message);
                            }
                          }}
                          className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-bold border-2 border-green-600 text-green-700 bg-green-50 hover:bg-green-100 transition whitespace-nowrap"
                        >
                          ⬇ hr-workflow-ai JSON
                        </button>
                      </>
                    )}
                    <button
                      onClick={handleGenerateTobeFlow}
                      disabled={tobeLoading}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-bold border-2 transition disabled:opacity-50 whitespace-nowrap"
                      style={{
                        borderColor: tobeFlow ? "#16A34A" : "#7C3AED",
                        color: tobeFlow ? "#16A34A" : "#7C3AED",
                        backgroundColor: tobeFlow ? "#F0FDF4" : "#F5F3FF",
                      }}
                    >
                      {tobeLoading ? (
                        <span className="flex items-center gap-1.5">
                          <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-purple-300 border-t-purple-600" />
                          생성 중...
                        </span>
                      ) : tobeFlow ? "↺ 재생성" : "⚡ Swim Lane 생성"}
                    </button>
                  </div>
                </div>

                {tobeFlow && tobeFlow.tobe_sheets && tobeFlow.tobe_sheets.length > 0 && (
                  <div className="space-y-3">
                    {tobeFlow.tobe_sheets.length > 1 && (
                      <div className="flex gap-1 flex-wrap">
                        {tobeFlow.tobe_sheets.map((sheet, idx) => (
                          <button
                            key={sheet.l4_id}
                            onClick={() => setTobeActiveSheet(idx)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition border ${
                              tobeActiveSheet === idx
                                ? "bg-purple-700 text-white border-purple-700"
                                : "bg-white text-gray-600 border-gray-200 hover:border-purple-300"
                            }`}
                          >
                            {sheet.l4_name}
                          </button>
                        ))}
                      </div>
                    )}
                    {(() => {
                      const sheet = tobeFlow.tobe_sheets[tobeActiveSheet] ?? tobeFlow.tobe_sheets[0];
                      return (
                        <div>
                          <div className="flex items-center gap-1.5 mb-2 flex-wrap">
                            <span className="text-[10px] text-gray-400">등장 액터:</span>
                            {sheet.actors_used.map(a => (
                              <span key={a} className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gray-100 text-gray-600 border border-gray-200">
                                {a}
                              </span>
                            ))}
                          </div>
                          <ToBeSwimlaneRF sheet={sheet} />
                        </div>
                      );
                    })()}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ═══ 새 프로젝트 이름 입력 모달 ═══ */}
      {showNewProjectModal && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-2xl shadow-xl w-[460px] p-6">
            <h3 className="text-base font-bold text-gray-900 mb-1">+ 새 프로젝트</h3>
            <p className="text-xs text-gray-500 mb-4">
              현재 작업은 자동 저장됩니다. 새 프로젝트의 이름을 입력하세요.
            </p>
            <input
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleConfirmNewProject();
                if (e.key === "Escape") setShowNewProjectModal(false);
              }}
              autoFocus
              placeholder="예: 2026 Q1 채용 혁신"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-200 focus:border-red-400"
            />
            <div className="flex items-center justify-end gap-2 mt-5">
              <button
                onClick={() => setShowNewProjectModal(false)}
                className="px-4 py-2 rounded-lg text-sm font-semibold text-gray-600 hover:bg-gray-100"
              >
                취소
              </button>
              <button
                onClick={handleConfirmNewProject}
                disabled={!newProjectName.trim()}
                className="px-4 py-2 rounded-lg text-sm font-bold text-white disabled:opacity-40"
                style={{ backgroundColor: PWC.primary }}
              >
                프로젝트 시작
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ PM 대시보드 모달 ═══ */}
      {showPMDashboard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl shadow-xl w-[780px] max-h-[80vh] flex flex-col overflow-hidden">
            {/* 모달 헤더 */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h2 className="text-base font-bold text-gray-800">👥 전체 프로젝트 현황</h2>
              <button
                onClick={() => setShowPMDashboard(false)}
                className="text-gray-400 hover:text-gray-600 text-xl leading-none"
              >
                ×
              </button>
            </div>
            {/* 모달 바디 */}
            <div className="overflow-y-auto flex-1 px-6 py-4 space-y-6">
              {pmLoading && (
                <p className="text-sm text-gray-400 animate-pulse">불러오는 중…</p>
              )}
              {!pmLoading && pmData.length === 0 && (
                <p className="text-sm text-gray-400">세션이 없습니다.</p>
              )}
              {!pmLoading && pmData.map((user) => (
                <div key={user.user_id}>
                  <h3 className="text-xs font-bold text-gray-500 uppercase mb-2 tracking-wide">
                    👤 {user.user_id}
                  </h3>
                  <div className="rounded-xl border border-gray-200 overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 text-xs text-gray-500 font-semibold">
                          <th className="text-left px-4 py-2">프로젝트명</th>
                          <th className="text-left px-4 py-2">수정일</th>
                          <th className="text-center px-3 py-2">벤치마킹</th>
                          <th className="text-center px-3 py-2">Gap분석</th>
                          <th className="text-center px-3 py-2">기본설계</th>
                          <th className="text-center px-3 py-2">상세설계</th>
                          <th className="px-3 py-2"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {user.sessions.map((sess) => (
                          <tr key={sess.id} className="border-t border-gray-100 hover:bg-gray-50">
                            <td className="px-4 py-2 font-medium text-gray-800 max-w-[180px] truncate">
                              {sess.name || sess.id}
                            </td>
                            <td className="px-4 py-2 text-xs text-gray-400">
                              {sess.updated_at
                                ? new Date(sess.updated_at).toLocaleDateString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })
                                : "-"}
                            </td>
                            <td className="px-3 py-2 text-center">
                              <span className={`text-[11px] font-bold px-1.5 py-0.5 rounded-full ${sess.has_benchmark ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-400"}`}>
                                {sess.has_benchmark ? "✓" : "-"}
                              </span>
                            </td>
                            <td className="px-3 py-2 text-center">
                              <span className={`text-[11px] font-bold px-1.5 py-0.5 rounded-full ${sess.has_gap ? "bg-orange-100 text-orange-700" : "bg-gray-100 text-gray-400"}`}>
                                {sess.has_gap ? "✓" : "-"}
                              </span>
                            </td>
                            <td className="px-3 py-2 text-center">
                              <span className={`text-[11px] font-bold px-1.5 py-0.5 rounded-full ${sess.has_step1 ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-400"}`}>
                                {sess.has_step1 ? "✓" : "-"}
                              </span>
                            </td>
                            <td className="px-3 py-2 text-center">
                              <span className={`text-[11px] font-bold px-1.5 py-0.5 rounded-full ${sess.has_step2 ? "bg-purple-100 text-purple-700" : "bg-gray-100 text-gray-400"}`}>
                                {sess.has_step2 ? "✓" : "-"}
                              </span>
                            </td>
                            <td className="px-3 py-2">
                              <button
                                onClick={() => {
                                  setShowPMDashboard(false);
                                  handleLoadSession(sess.id);
                                }}
                                className="px-2 py-1 rounded text-[11px] font-semibold border border-gray-300 text-gray-600 hover:bg-gray-100 transition"
                              >
                                열기
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          </div>
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
