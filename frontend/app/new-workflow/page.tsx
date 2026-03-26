"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  uploadNewWorkflowExcel,
  selectNewWorkflowSheet,
  getNewWorkflowFilters,
  generateNewWorkflow,
  generateNewWorkflowFreeform,
  benchmarkNewWorkflow,
  saveEditedWorkflow,
  downloadNewWorkflowAsHtml,
  downloadNewWorkflowAsHrJson,
  type ExcelSheet,
  type NewWorkflowResult,
  type BenchmarkInsight,
  getProjectList,
  loadProject,
  getNewWorkflowResult,
  type ProjectInfo,
} from "@/lib/api";
import WorkflowEditor from "@/components/WorkflowEditor";
import {
  Sparkles, Loader2,
  Zap, Download, Upload, FileSpreadsheet, ArrowRight,
  FolderKanban, FolderOpen, Clock, CheckCircle2,
} from "lucide-react";

/* ── 색상 ────────────────────────────────────────────────────────────────── */
const PWC = { primary: "#A62121", bg: "#FFF5F7", cardBg: "#FFFFFF" };

const AUTO_COLOR: Record<string, { bg: string; text: string; border: string }> = {
  "Human-on-the-Loop":        { bg: "#D6F5E3", text: "#1a7a45", border: "#6fcf97" },
  "Human-in-Loop":    { bg: "#FFF9DB", text: "#7a5c00", border: "#f2c94c" },
  "Human-Supervised": { bg: "#FFE0E0", text: "#A62121", border: "#eb5757" },
};

/* ══════════════════════════════════════════════════════════════════════════ */
/* ── 메인 페이지 ─────────────────────────────────────────────────────────── */
/* ══════════════════════════════════════════════════════════════════════════ */

type InputMode = "excel" | "form";

export default function NewWorkflowPage() {
  const router = useRouter();

  // 입력 모드
  const [inputMode, setInputMode] = useState<InputMode>("form");

  // 엑셀 업로드 상태
  const [uploading, setUploading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const [taskCount, setTaskCount] = useState(0);
  const [sheets, setSheets] = useState<ExcelSheet[]>([]);
  const [selectedSheet, setSelectedSheet] = useState("");
  const [l3Options, setL3Options] = useState<{ id: string; name: string }[]>([]);
  const [selectedL3, setSelectedL3] = useState("");

  // 직접 입력 상태 (과제 엑셀 양식과 동일)
  const [formData, setFormData] = useState({
    process_name: "",       // 이름
    overview: "",           // 과제개요
    as_is: "",              // 업무 현황(As-Is)
    pain_points: "",        // Pain-Point
    needs: "",              // Needs
    to_be: "",              // 개선모습(To-Be)
    level: "",              // 과제 수준
    considerations: "",     // 과제 추진 시 고려사항
    effect_quant: "",       // 정량적 효과
    effect_qual: "",        // 정성적 효과
    input_internal: "",     // Input(내부)
    input_external: "",     // Input(외부)
    output: "",             // Output
  });

  // 생성 상태
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<NewWorkflowResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  // 벤치마킹 상태
  const [benchmarking, setBenchmarking] = useState(false);
  const [benchmarkInsights, setBenchmarkInsights] = useState<BenchmarkInsight[]>([]);
  const [improvementSummary, setImprovementSummary] = useState("");
  const [isBenchmarked, setIsBenchmarked] = useState(false);

  // 이전 프로젝트
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [loadingProject, setLoadingProject] = useState<string | null>(null);

  const updateForm = (key: string, value: string) =>
    setFormData((prev) => ({ ...prev, [key]: value }));

  // 이전 프로젝트 목록 로드
  useEffect(() => {
    getProjectList()
      .then((r) => setProjects(r.projects.filter((p) => p.source === "new_workflow")))
      .catch(() => {});
  }, []);

  // 이전 프로젝트 불러오기
  const handleLoadProject = async (filename: string) => {
    setLoadingProject(filename);
    try {
      await loadProject(filename);
      const nwResult = await getNewWorkflowResult();
      setResult(nwResult);
    } catch {
    } finally {
      setLoadingProject(null);
      setShowHistory(false);
    }
  };

  // 업로드 형식 (project vs l5_tasks)
  const [uploadFormat, setUploadFormat] = useState<string>("");
  const [projectCount, setProjectCount] = useState(0);
  const [projectList, setProjectList] = useState<Array<{ no: string; name: string }>>([]);
  const [selectedProjectIdx, setSelectedProjectIdx] = useState<number | null>(null);

  // 파일 업로드
  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      const res = await uploadNewWorkflowExcel(file) as any;
      setUploadedFile(res.filename);
      setUploadFormat(res.format || "");
      setProjectCount(res.project_count || 0);
      setProjectList(res.projects || []);
      setSelectedProjectIdx(null);
      setTaskCount(res.task_count || 0);
      setSheets(res.sheets || []);
      setResult(null);
      // 필터 옵션 로드 (L5 형식일 때만)
      if (res.format !== "project") {
        const filters = await getNewWorkflowFilters();
        setL3Options(filters.l3_options);
      }
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

  // Workflow 생성 (엑셀 모드)
  const handleGenerateFromExcel = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (selectedL3) params.l3 = selectedL3;
      if (uploadFormat === "project" && selectedProjectIdx !== null) {
        params.project_index = String(selectedProjectIdx);
      }
      const res = await generateNewWorkflow(params as any);
      setResult(res);
      // result updated
    } catch (e) {
      setError(e instanceof Error ? e.message : "생성 중 오류 발생");
    } finally {
      setLoading(false);
    }
  };

  // Workflow 생성 (직접 입력 모드) — 과제 양식 필드를 freeform API에 매핑
  const handleGenerateFromForm = async () => {
    if (!formData.process_name.trim()) {
      setError("과제명을 입력해 주세요.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const additional = [
        formData.overview && `과제개요: ${formData.overview}`,
        formData.as_is && `현황(As-Is): ${formData.as_is}`,
        formData.needs && `Needs: ${formData.needs}`,
        formData.to_be && `개선방향(To-Be): ${formData.to_be}`,
        formData.level && `과제 수준: ${formData.level}`,
        formData.considerations && `고려사항: ${formData.considerations}`,
        formData.effect_quant && `정량적 효과: ${formData.effect_quant}`,
        formData.effect_qual && `정성적 효과: ${formData.effect_qual}`,
      ].filter(Boolean).join("\n");

      const res = await generateNewWorkflowFreeform({
        process_name: formData.process_name,
        inputs: [formData.input_internal && `내부: ${formData.input_internal}`, formData.input_external && `외부: ${formData.input_external}`].filter(Boolean).join("\n"),
        outputs: formData.output,
        pain_points: formData.pain_points,
        additional_info: additional,
      });
      setResult(res);
      // result updated
    } catch (e) {
      setError(e instanceof Error ? e.message : "생성 중 오류 발생");
    } finally {
      setLoading(false);
    }
  };

  // 벤치마킹
  // 벤치마킹 전 상태 저장 (롤백용)
  const [preBenchmarkResult, setPreBenchmarkResult] = useState<NewWorkflowResult | null>(null);

  const handleBenchmark = async () => {
    setBenchmarking(true);
    setError(null);
    // 벤치마킹 전 상태 저장
    if (result && !preBenchmarkResult) {
      setPreBenchmarkResult({ ...result });
    }
    try {
      const res = await benchmarkNewWorkflow();
      setResult(res);
      setBenchmarkInsights(res.benchmark_insights || []);
      setImprovementSummary(res.improvement_summary || "");
      setIsBenchmarked(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "벤치마킹 중 오류 발생");
    } finally {
      setBenchmarking(false);
    }
  };

  // 벤치마킹 롤백 (벤치마킹 전 상태로 복원)
  const handleBenchmarkRollback = async () => {
    if (preBenchmarkResult) {
      setResult(preBenchmarkResult);
      setBenchmarkInsights([]);
      setImprovementSummary("");
      setIsBenchmarked(false);
      setPreBenchmarkResult(null);
      try {
        await saveEditedWorkflow(preBenchmarkResult as unknown as Record<string, unknown>);
      } catch {}
    }
  };

  // 특정 인사이트 제외
  const handleRemoveInsight = (index: number) => {
    setBenchmarkInsights((prev) => prev.filter((_, i) => i !== index));
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
    a.assigned_tasks.filter((t) => t.automation_level === "Human-on-the-Loop")
  ) ?? [];
  const humanTasks = result?.agents.flatMap((a) =>
    a.assigned_tasks.filter((t) => t.automation_level !== "Human-on-the-Loop")
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

        {/* ── 이전 프로젝트 불러오기 ───────────────────────────────────────── */}
        {projects.length > 0 && (
          <div className="rounded-xl border bg-white shadow-sm overflow-hidden mb-6">
            <button onClick={() => setShowHistory((v) => !v)}
              className="w-full flex items-center justify-between px-5 py-3 hover:bg-gray-50 transition-colors">
              <div className="flex items-center gap-2">
                <FolderOpen className="h-4 w-4" style={{ color: "#A62121" }} />
                <span className="text-sm font-semibold text-gray-900">이전 Workflow 불러오기</span>
                <span className="rounded-full px-2 py-0.5 text-[10px] font-semibold bg-gray-100 text-gray-500">{projects.length}</span>
              </div>
              <span className="text-xs text-gray-400">{showHistory ? "접기" : "펼치기"}</span>
            </button>
            {showHistory && (
              <div className="border-t divide-y">
                {projects.map((p) => (
                  <div key={p.dirname} className="flex items-center justify-between px-5 py-3 hover:bg-gray-50">
                    <div className="flex items-center gap-3 min-w-0">
                      <FileSpreadsheet className="h-4 w-4 text-gray-400 flex-shrink-0" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{p.filename || p.dirname}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          {p.created_at && (
                            <span className="flex items-center gap-1 text-[10px] text-gray-400">
                              <Clock className="h-3 w-3" />{new Date(p.created_at).toLocaleDateString("ko-KR")}
                            </span>
                          )}
                          {p.saved_data?.new_workflow_result && (
                            <span className="flex items-center gap-0.5 text-[10px] text-green-600">
                              <CheckCircle2 className="h-3 w-3" /> Workflow 있음
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <button onClick={() => handleLoadProject(p.filename || p.dirname)}
                      disabled={loadingProject === (p.filename || p.dirname)}
                      className="flex-shrink-0 rounded-lg px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                      style={{ backgroundColor: "#A62121" }}>
                      {loadingProject === (p.filename || p.dirname) ? "로딩..." : "불러오기"}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── 입력 모드 선택 ────────────────────────────────────────────────── */}
        <div className="rounded-xl shadow-sm overflow-hidden mb-6" style={{ backgroundColor: PWC.cardBg, border: "1px solid #f0e0e0" }}>
          {/* 모드 탭 */}
          <div className="flex border-b" style={{ borderColor: "#f0e0e0" }}>
            {([
              { key: "form" as InputMode, label: "직접 입력", icon: Zap },
              { key: "excel" as InputMode, label: "엑셀 업로드", icon: FileSpreadsheet },
            ]).map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setInputMode(key)}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold transition-colors ${
                  inputMode === key ? "text-white" : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
                }`}
                style={inputMode === key ? { backgroundColor: PWC.primary } : undefined}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </div>

          <div className="p-5">
            {/* ── 직접 입력 모드 ──────────────────────────────────────────── */}
            {inputMode === "form" && (
              <div className="space-y-4">
                {/* 과제명 + 과제개요 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      이름 (과제명) <span className="text-red-500">*</span>
                    </label>
                    <input type="text" value={formData.process_name}
                      onChange={(e) => updateForm("process_name", e.target.value)}
                      placeholder="예: 의료비 판독 Agent, 채용 프로세스 자동화"
                      className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-[#A62121] focus:ring-1 focus:ring-[#A62121] outline-none" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">과제 수준</label>
                    <select value={formData.level} onChange={(e) => updateForm("level", e.target.value)}
                      className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-[#A62121] focus:ring-1 focus:ring-[#A62121] outline-none">
                      <option value="">선택</option>
                      <option value="Level 1">Level 1</option>
                      <option value="Level 2">Level 2</option>
                      <option value="Level 3">Level 3</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">과제 개요 (주요 과제 내용)</label>
                  <textarea value={formData.overview} onChange={(e) => updateForm("overview", e.target.value)}
                    placeholder="표준화된 병명과 진료 내역을 기준으로 의료비 지급 요건·한도·중복 규정을 검증해..."
                    rows={3} className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-[#A62121] focus:ring-1 focus:ring-[#A62121] outline-none resize-none" />
                </div>

                {/* 현황 및 Pain Point vs. 개선 방향 */}
                <div className="rounded-lg border border-gray-200 p-4 space-y-3">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">현황 및 Pain Point vs. 개선 방향</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">업무 현황 (As-Is)</label>
                      <textarea value={formData.as_is} onChange={(e) => updateForm("as_is", e.target.value)}
                        placeholder="구성원의 의료비 지원 신청 내역을 건별 수기 검토하여..."
                        rows={3} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#A62121] focus:ring-1 focus:ring-[#A62121] outline-none resize-none" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-red-600 mb-1">Pain-Point</label>
                      <textarea value={formData.pain_points} onChange={(e) => updateForm("pain_points", e.target.value)}
                        placeholder="명확하지 않은 검토 기준으로 판단의 일관성 부족, 검토 공수 증가..."
                        rows={3} className="w-full rounded-lg border border-red-200 px-3 py-2 text-sm focus:border-red-500 focus:ring-1 focus:ring-red-500 outline-none resize-none bg-red-50/30" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Needs</label>
                      <textarea value={formData.needs} onChange={(e) => updateForm("needs", e.target.value)}
                        placeholder="지급 기준을 명확히 정의하고 일관되게 적용할 수 있는 체계..."
                        rows={3} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#A62121] focus:ring-1 focus:ring-[#A62121] outline-none resize-none" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-green-700 mb-1">개선모습 (To-Be)</label>
                      <textarea value={formData.to_be} onChange={(e) => updateForm("to_be", e.target.value)}
                        placeholder="Agent가 기존 처리 사례를 기반으로 모호한 규정의 해석·판단 방향성을 자동 제안..."
                        rows={3} className="w-full rounded-lg border border-green-200 px-3 py-2 text-sm focus:border-green-500 focus:ring-1 focus:ring-green-500 outline-none resize-none bg-green-50/30" />
                    </div>
                  </div>
                </div>

                {/* 기대효과 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">정량적 효과</label>
                    <textarea value={formData.effect_quant} onChange={(e) => updateForm("effect_quant", e.target.value)}
                      placeholder="의료비 검토 및 승인 공수 nn% 이상 절감..."
                      rows={2} className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-[#A62121] focus:ring-1 focus:ring-[#A62121] outline-none resize-none" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">정성적 효과</label>
                    <textarea value={formData.effect_qual} onChange={(e) => updateForm("effect_qual", e.target.value)}
                      placeholder="지급 기준 표준화로 판단 일관성 확보..."
                      rows={2} className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-[#A62121] focus:ring-1 focus:ring-[#A62121] outline-none resize-none" />
                  </div>
                </div>

                {/* 활용 Data/System */}
                <div className="rounded-lg border border-gray-200 p-4 space-y-3">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">활용 Data / System (Input/Output)</p>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Input (내부)</label>
                      <textarea value={formData.input_internal} onChange={(e) => updateForm("input_internal", e.target.value)}
                        placeholder="의료비 청구 병명, 진료 항목·금액, 지급 기준..."
                        rows={3} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#A62121] focus:ring-1 focus:ring-[#A62121] outline-none resize-none" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Input (외부)</label>
                      <textarea value={formData.input_external} onChange={(e) => updateForm("input_external", e.target.value)}
                        placeholder="표준 질병분류 코드 (KCD/ICD)..."
                        rows={3} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#A62121] focus:ring-1 focus:ring-[#A62121] outline-none resize-none" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Output</label>
                      <textarea value={formData.output} onChange={(e) => updateForm("output", e.target.value)}
                        placeholder="지급 가능 여부 판정 결과, 지급 가능 금액..."
                        rows={3} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#A62121] focus:ring-1 focus:ring-[#A62121] outline-none resize-none" />
                    </div>
                  </div>
                </div>

                {/* 고려사항 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">과제 추진 시 고려사항</label>
                  <textarea value={formData.considerations} onChange={(e) => updateForm("considerations", e.target.value)}
                    placeholder="의료비 증빙서류의 형식이 다양하여 데이터 추출 정확도 확보 필요..."
                    rows={2} className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-[#A62121] focus:ring-1 focus:ring-[#A62121] outline-none resize-none" />
                </div>

                <button
                  onClick={handleGenerateFromForm}
                  disabled={loading || !formData.process_name.trim()}
                  className="w-full flex items-center justify-center gap-2 rounded-lg px-5 py-3 text-sm font-semibold text-white transition-opacity disabled:opacity-60"
                  style={{ backgroundColor: PWC.primary }}
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  {loading ? "AI가 새 Workflow를 설계하고 있습니다..." : "AI Workflow 설계 시작"}
                </button>
              </div>
            )}

            {/* ── 엑셀 업로드 모드 ───────────────────────────────────────── */}
            {inputMode === "excel" && (
              <div className="space-y-4">
                {!uploadedFile ? (
                  <label className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 py-10 cursor-pointer hover:border-[#A62121] transition-colors">
                    <input
                      type="file" accept=".xlsx" className="hidden"
                      onChange={(e) => { if (e.target.files?.[0]) handleUpload(e.target.files[0]); }}
                      disabled={uploading}
                    />
                    {uploading ? <Loader2 className="h-8 w-8 animate-spin text-gray-400 mb-2" /> : <Upload className="h-8 w-8 text-gray-400 mb-2" />}
                    <p className="text-sm text-gray-600 font-medium">
                      {uploading ? "업로드 중..." : "클릭하거나 파일을 드래그해서 업로드"}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">As-Is 프로세스 .xlsx 파일</p>
                  </label>
                ) : (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <FileSpreadsheet className="h-5 w-5 text-green-600" />
                      <div>
                        <p className="text-sm font-medium text-gray-900">{uploadedFile}</p>
                        <p className="text-xs text-gray-500">
                          {uploadFormat === "project"
                            ? `${projectCount}개 과제 로드됨`
                            : `${taskCount}개 Task 로드됨`}
                        </p>
                      </div>
                    </div>
                    <label className="text-sm cursor-pointer font-medium" style={{ color: PWC.primary }}>
                      <input type="file" accept=".xlsx" className="hidden"
                        onChange={(e) => { if (e.target.files?.[0]) handleUpload(e.target.files[0]); }} />
                      다른 파일
                    </label>
                  </div>
                )}

                {sheets.length > 1 && (
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">시트 선택</label>
                    <select className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                      value={selectedSheet} onChange={(e) => handleSelectSheet(e.target.value)}>
                      {sheets.map((s) => (
                        <option key={s.name} value={s.name}>
                          {s.name} ({s.l5_count} tasks){s.recommended ? " ★ 추천" : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {uploadedFile && (taskCount > 0 || projectCount > 0) && (
                  <div className="pt-2 space-y-3">
                    {uploadFormat !== "project" && (
                      <div className="flex flex-col sm:flex-row gap-3 items-end">
                        <div className="flex-1">
                          <label className="block text-sm font-medium text-gray-700 mb-1">L3 필터 (선택)</label>
                          <select className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#A62121]"
                            value={selectedL3} onChange={(e) => setSelectedL3(e.target.value)}>
                            <option value="">전체</option>
                            {l3Options.map((o) => <option key={o.id} value={o.name}>{o.name}</option>)}
                          </select>
                        </div>
                        <button onClick={handleGenerateFromExcel} disabled={loading}
                          className="flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold text-white transition-opacity disabled:opacity-60"
                          style={{ backgroundColor: PWC.primary }}>
                          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                          {loading ? "설계 중..." : "AI Workflow 설계 시작"}
                        </button>
                      </div>
                    )}

                    {/* 과제 형식: 개별 과제 선택 */}
                    {uploadFormat === "project" && projectList.length > 0 && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          과제 선택 ({projectCount}개)
                        </label>
                        <div className="space-y-2 max-h-[300px] overflow-y-auto">
                          {projectList.map((p, i) => (
                            <div key={i}
                              onClick={() => setSelectedProjectIdx(i)}
                              className={`flex items-center gap-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                                selectedProjectIdx === i
                                  ? "border-[#A62121] bg-red-50/50"
                                  : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                              }`}>
                              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                                selectedProjectIdx === i
                                  ? "bg-[#A62121] text-white"
                                  : "bg-gray-100 text-gray-500"
                              }`}>
                                {p.no || i + 1}
                              </div>
                              <span className="text-sm font-medium text-gray-900">{p.name}</span>
                            </div>
                          ))}
                        </div>
                        <button
                          onClick={handleGenerateFromExcel}
                          disabled={loading || selectedProjectIdx === null}
                          className="w-full mt-3 flex items-center justify-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold text-white transition-opacity disabled:opacity-60"
                          style={{ backgroundColor: PWC.primary }}>
                          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                          {loading
                            ? "AI가 새 Workflow를 설계하고 있습니다..."
                            : selectedProjectIdx !== null
                              ? `"${projectList[selectedProjectIdx]?.name}" Workflow 설계 시작`
                              : "과제를 선택해 주세요"}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* 에러 */}
        {error && (
          <div className="mb-6 rounded-lg p-4 text-sm" style={{ backgroundColor: "#FFE0E0", color: PWC.primary, border: `1px solid ${PWC.primary}` }}>
            {error}
          </div>
        )}

        {/* ── 결과: 스윔레인 메인 뷰 + 단계 컨트롤 ─────────────────────────── */}
        {result && (
          <>
            {/* 요약 + 통계 바 */}
            <div className="rounded-xl p-4 mb-4 shadow-sm" style={{ backgroundColor: PWC.cardBg, border: "1px solid #f0e0e0" }}>
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div className="flex-1 min-w-0">
                  <h2 className="text-base font-semibold text-gray-900">{result.process_name} — AI Service Flow</h2>
                  <p className="text-xs text-gray-500 mt-0.5 truncate">{result.blueprint_summary}</p>
                </div>
                <div className="flex gap-2">
                  <div className="rounded-lg px-3 py-1.5 text-center" style={{ backgroundColor: "#f5f5f5" }}>
                    <span className="text-lg font-bold text-gray-900">{result.total_tasks}</span>
                    <span className="text-[10px] text-gray-500 ml-1">Task</span>
                  </div>
                  <div className="rounded-lg px-3 py-1.5 text-center" style={{ backgroundColor: AUTO_COLOR["Human-on-the-Loop"].bg }}>
                    <span className="text-lg font-bold" style={{ color: AUTO_COLOR["Human-on-the-Loop"].text }}>{aiTasks.length}</span>
                    <span className="text-[10px] ml-1" style={{ color: AUTO_COLOR["Human-on-the-Loop"].text }}>AI</span>
                  </div>
                  <div className="rounded-lg px-3 py-1.5 text-center" style={{ backgroundColor: AUTO_COLOR["Human-in-Loop"].bg }}>
                    <span className="text-lg font-bold" style={{ color: AUTO_COLOR["Human-in-Loop"].text }}>{humanTasks.length}</span>
                    <span className="text-[10px] ml-1" style={{ color: AUTO_COLOR["Human-in-Loop"].text }}>Human</span>
                  </div>
                  <button onClick={handleExport} disabled={exporting}
                    className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium disabled:opacity-60"
                    style={{ borderColor: PWC.primary, color: PWC.primary }}>
                    {exporting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Download className="h-3 w-3" />}
                    JSON
                  </button>
                  <button onClick={async () => { try { await downloadNewWorkflowAsHtml(); } catch (e) { setError(e instanceof Error ? e.message : "HTML 내보내기 실패"); } }}
                    className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium"
                    style={{ borderColor: "#1A5CB0", color: "#1A5CB0" }}>
                    <Download className="h-3 w-3" />
                    HTML
                  </button>
                </div>
              </div>
            </div>

            {/* ★ 메인 스윔레인 — 항상 보임 ★ */}
            <div className="mb-6">
              <WorkflowEditor
                key={`editor-${result.total_tasks}-${isBenchmarked}`}
                result={result}
                onSave={async (swimlaneData) => {
                  try {
                    await saveEditedWorkflow(swimlaneData as unknown as Record<string, unknown>);
                  } catch {}
                }}
              />
            </div>

            {/* ── 단계별 액션 바 ──────────────────────────────────────────── */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">

              {/* 1단계: 완료 */}
              <div className="rounded-xl p-4 shadow-sm" style={{ backgroundColor: PWC.cardBg, border: "2px solid #6fcf97" }}>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center">
                    <span className="text-xs font-bold text-green-700">1</span>
                  </div>
                  <span className="text-sm font-semibold text-gray-900">AI 설계</span>
                  <span className="rounded-full px-2 py-0.5 text-[10px] font-semibold bg-green-100 text-green-700">완료</span>
                </div>
                <p className="text-xs text-gray-500">Pain Point 기반 To-Be Workflow 생성됨</p>
              </div>

              {/* 2단계: 벤치마킹 */}
              <div className="rounded-xl p-4 shadow-sm" style={{ backgroundColor: PWC.cardBg, border: isBenchmarked ? "2px solid #6fcf97" : "1px solid #f0e0e0" }}>
                <div className="flex items-center gap-2 mb-2">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center ${isBenchmarked ? "bg-green-100" : "bg-gray-100"}`}>
                    <span className={`text-xs font-bold ${isBenchmarked ? "text-green-700" : "text-gray-500"}`}>2</span>
                  </div>
                  <span className="text-sm font-semibold text-gray-900">벤치마킹</span>
                  {isBenchmarked && <span className="rounded-full px-2 py-0.5 text-[10px] font-semibold bg-green-100 text-green-700">적용됨</span>}
                </div>
                <button onClick={handleBenchmark} disabled={benchmarking}
                  className="w-full mt-1 flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-white disabled:opacity-60"
                  style={{ backgroundColor: isBenchmarked ? "#1a7a45" : PWC.primary }}>
                  {benchmarking ? <Loader2 className="h-3 w-3 animate-spin" /> : <span>🔍</span>}
                  {benchmarking ? "검색 중..." : isBenchmarked ? "다시 벤치마킹" : "벤치마킹 시작"}
                </button>
              </div>

              {/* 3단계: 편집 안내 */}
              <div className="rounded-xl p-4 shadow-sm" style={{ backgroundColor: PWC.cardBg, border: "1px solid #f0e0e0" }}>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center">
                    <span className="text-xs font-bold text-gray-500">3</span>
                  </div>
                  <span className="text-sm font-semibold text-gray-900">직접 편집</span>
                </div>
                <p className="text-xs text-gray-500">위 스윔레인의 박스를 클릭하여 직접 수정하세요. + 버튼으로 추가, 휴지통으로 삭제.</p>
              </div>
            </div>

            {/* 벤치마킹 인사이트 (접힘 가능) */}
            {isBenchmarked && (improvementSummary || benchmarkInsights.length > 0) && (
              <div className="rounded-xl p-4 mb-6 shadow-sm" style={{ backgroundColor: "#F0FFF4", border: "1px solid #C6F6D5" }}>
                <p className="text-sm font-semibold text-green-800 mb-2">벤치마킹 개선 요약</p>
                {improvementSummary && <p className="text-sm text-green-700 mb-3">{improvementSummary}</p>}
                {benchmarkInsights.length > 0 && (
                  <div className="space-y-2 mt-3">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-semibold text-green-700">참고 벤치마킹 사례 ({benchmarkInsights.length}건)</p>
                      {preBenchmarkResult && (
                        <button onClick={handleBenchmarkRollback}
                          className="text-[10px] font-medium text-red-600 hover:text-red-800 underline">
                          벤치마킹 전으로 되돌리기
                        </button>
                      )}
                    </div>
                    {benchmarkInsights.map((insight, i) => (
                      <div key={i} className="rounded-lg border border-green-200 bg-white p-3">
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <span className="rounded-full bg-green-100 text-green-700 text-[10px] font-bold w-5 h-5 flex items-center justify-center flex-shrink-0">{i + 1}</span>
                            <span className="text-sm font-semibold text-gray-900">{insight.source}</span>
                            {insight.url && (
                              <a href={insight.url} target="_blank" rel="noopener noreferrer"
                                className="text-[10px] text-blue-600 hover:underline">
                                출처 확인 ↗
                              </a>
                            )}
                          </div>
                          <button onClick={() => handleRemoveInsight(i)}
                            className="text-[10px] text-gray-400 hover:text-red-600 transition-colors">
                            제외
                          </button>
                        </div>
                        <p className="text-xs text-gray-600 ml-7">{insight.insight}</p>
                        <p className="text-xs mt-1 ml-7" style={{ color: PWC.primary }}>→ {insight.application}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* ── 과제 관리로 연결 ────────────────────────────────────────────── */}
            <div className="rounded-xl p-5 shadow-sm text-center"
              style={{ backgroundColor: PWC.cardBg, border: "2px solid #f0e0e0" }}>
              <FolderKanban className="mx-auto h-7 w-7 mb-2" style={{ color: PWC.primary }} />
              <h3 className="text-base font-semibold text-gray-900 mb-1">과제 관리로 이어서 진행</h3>
              <p className="text-xs text-gray-500 mb-3">Workflow 설계 결과를 기반으로 과제 정의서/설계서를 자동 생성합니다.</p>
              <button
                onClick={() => router.push("/project-management?source=new-workflow")}
                className="inline-flex items-center gap-2 rounded-lg px-5 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90"
                style={{ backgroundColor: PWC.primary }}>
                <FolderKanban className="h-4 w-4" />
                과제 정의서 / 설계서 생성
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </>
        )}

        {/* 빈 상태 */}
        {!result && !loading && (
          <div className="rounded-xl py-16 text-center" style={{ backgroundColor: PWC.cardBg, border: "1px dashed #d9a0a0" }}>
            <Sparkles className="mx-auto h-10 w-10 mb-4" style={{ color: "#d9a0a0" }} />
            <p className="text-gray-500 text-sm">
              위에서 업무 정보를 입력하거나 엑셀을 업로드한 뒤, Workflow 설계를 시작해 주세요.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
