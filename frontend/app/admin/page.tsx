"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getAdminDashboard,
  getAdminAuditLog,
  adminForceLogout,
  getAdminUploads,
  getAdminUploadsAll,
  downloadAdminFile,
  deleteAdminWorkflowSession,
  deleteAdminUpload,
  deleteAdminWorkflowFile,
  type AdminUser,
  type AdminSession,
  type AuditLogEntry,
  type UploadedFile,
  type AdminUploadsAll,
} from "@/lib/api";

const PWC = { primary: "#A62121", primaryLight: "#D95578" };

type Tab = "overview" | "sessions" | "audit" | "login" | "files";

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("overview");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [sessions, setSessions] = useState<AdminSession[]>([]);
  const [loginHistory, setLoginHistory] = useState<AuditLogEntry[]>([]);
  const [dataActivity, setDataActivity] = useState<AuditLogEntry[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [auditFilter, setAuditFilter] = useState({ email: "", event: "", ip: "" });
  const [usage, setUsage] = useState<Record<string, { total_calls: number; input_tokens: number; output_tokens: number; estimated_cost_usd: number; last_used: string | null }>>({});
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [uploadDir, setUploadDir] = useState("");
  const [uploadsAll, setUploadsAll] = useState<AdminUploadsAll["categories"] | null>(null);
  const [fileSubTab, setFileSubTab] = useState<"task_excel" | "wf_excel" | "wf_json" | "wf_ppt" | "new_workflow">("task_excel");

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getAdminDashboard();
      setUsers(data.users);
      setSessions(data.active_sessions);
      setLoginHistory(data.login_history);
      setDataActivity(data.data_activity);
      if ((data as Record<string, unknown>).usage) setUsage((data as Record<string, unknown>).usage as typeof usage);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAuditLog = useCallback(async () => {
    try {
      const data = await getAdminAuditLog({
        limit: 200,
        email: auditFilter.email,
        event: auditFilter.event,
        ip: auditFilter.ip,
      });
      setAuditLogs(data.logs);
      setAuditTotal(data.total);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [auditFilter]);

  useEffect(() => { loadDashboard(); }, [loadDashboard]);
  useEffect(() => { if (tab === "audit") loadAuditLog(); }, [tab, loadAuditLog]);

  const loadFiles = useCallback(async () => {
    try {
      const [basic, all] = await Promise.all([getAdminUploads(), getAdminUploadsAll()]);
      setUploadedFiles(basic.files);
      setUploadDir(basic.directory);
      setUploadsAll(all.categories);
    } catch {}
  }, []);

  useEffect(() => { if (tab === "files") loadFiles(); }, [tab, loadFiles]);

  const handleForceLogout = async (email: string) => {
    if (!confirm(`${email}의 모든 세션을 강제 종료하시겠습니까?`)) return;
    try {
      const r = await adminForceLogout(email);
      alert(`${r.sessions_removed}개 세션이 종료되었습니다.`);
      loadDashboard();
    } catch (e) {
      alert((e as Error).message);
    }
  };

  const eventColor = (event: string) => {
    if (event.includes("failed") || event.includes("denied")) return "bg-red-100 text-red-700";
    if (event.includes("success") || event.includes("login")) return "bg-green-100 text-green-700";
    if (event.includes("logout") || event.includes("evict")) return "bg-yellow-100 text-yellow-700";
    if (event.includes("admin")) return "bg-purple-100 text-purple-700";
    if (event.includes("upload") || event.includes("generate")) return "bg-blue-100 text-blue-700";
    return "bg-gray-100 text-gray-700";
  };

  if (error && error.includes("403")) {
    return (
      <div className="text-center py-20">
        <div className="text-5xl mb-4">&#128274;</div>
        <h2 className="text-xl font-bold text-gray-800 mb-2">접근 권한이 없습니다</h2>
        <p className="text-sm text-gray-500">관리자 계정으로 로그인하세요.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold" style={{ color: PWC.primary }}>Admin Console</h1>
        <p className="mt-1 text-sm text-gray-500">사용자 관리, 접속 기록, 감사 로그</p>
      </div>

      {/* 탭 */}
      <div className="flex gap-1 border-b border-gray-200">
        {([
          ["overview", "대시보드"],
          ["sessions", "활성 세션"],
          ["login", "접속 기록"],
          ["audit", "감사 로그"],
          ["files", "업로드 파일"],
        ] as [Tab, string][]).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition ${
              tab === key ? "border-red-600 text-red-700" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {label}
          </button>
        ))}
        <button onClick={loadDashboard} className="ml-auto text-xs text-gray-400 hover:text-red-500 px-3">
          새로고침
        </button>
      </div>

      {loading && (
        <div className="text-center py-10">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-red-200 border-t-red-600" />
        </div>
      )}

      {error && !error.includes("403") && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">{error}</div>
      )}

      {/* ═══ 대시보드 ═══ */}
      {tab === "overview" && !loading && (
        <div className="space-y-6">
          {/* 통계 */}
          <div className="flex gap-4 flex-wrap">
            <Stat label="등록 사용자" value={users.length} />
            <Stat label="활성 세션" value={sessions.length} accent />
            <Stat label="최근 로그인 시도" value={loginHistory.length} />
            <Stat label="데이터 활동" value={dataActivity.length} />
          </div>

          {/* 진단 카드 */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl px-5 py-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-bold text-blue-800 mb-1">🔍 매핑 진단 (연결률 0% 문제 확인)</div>
                <div className="text-xs text-blue-600">엑셀 Task ID와 As-Is L5 task_id 포맷을 직접 비교합니다. Railway Volume 경로도 확인 가능.</div>
              </div>
              <a
                href={`${process.env.NEXT_PUBLIC_BACKEND_URL || ""}/api/workflow/debug-ids`}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-xs font-bold hover:bg-blue-700 transition whitespace-nowrap"
              >
                진단 JSON 열기 →
              </a>
            </div>
          </div>

          {/* 사용자 목록 */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 text-sm font-bold text-gray-700">사용자 목록</div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50/50">
                  <th className="text-left px-4 py-2 font-medium text-gray-600">이메일</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">이름</th>
                  <th className="text-center px-4 py-2 font-medium text-gray-600">세션</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">접속 IP</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">프로젝트</th>
                  <th className="text-center px-4 py-2 font-medium text-gray-600">상태</th>
                  <th className="text-center px-4 py-2 font-medium text-gray-600">액션</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.email} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-xs">{u.email}</td>
                    <td className="px-4 py-2">{u.name}</td>
                    <td className="px-4 py-2 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                        u.active_sessions > 0 ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                      }`}>
                        {u.active_sessions}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-500">{u.session_ips.join(", ") || "-"}</td>
                    <td className="px-4 py-2 text-xs">
                      {u.project ? (
                        <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-bold">{u.project}</span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-bold">공통</span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {u.must_change_password && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] bg-yellow-100 text-yellow-700">비번 변경 필요</span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {u.active_sessions > 0 && (
                        <button
                          onClick={() => handleForceLogout(u.email)}
                          className="text-xs text-red-500 hover:text-red-700 underline"
                        >
                          강제 로그아웃
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 토큰 사용량 */}
          {Object.keys(usage).length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 text-sm font-bold text-gray-700">API 토큰 사용량</div>
              <div className="p-4">
                <div className="grid grid-cols-3 gap-4">
                  {Object.entries(usage).map(([provider, u]) => (
                    <div key={provider} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <span className={`text-sm font-bold ${
                          provider === "openai" ? "text-green-700"
                          : provider === "anthropic" ? "text-orange-700"
                          : "text-purple-700"
                        }`}>
                          {provider === "openai" ? "OpenAI (Model A)"
                          : provider === "anthropic" ? "Anthropic (Model B)"
                          : "Perplexity (Sonar Pro)"}
                        </span>
                        <span className="text-lg font-bold text-gray-800">${u.estimated_cost_usd.toFixed(4)}</span>
                      </div>
                      <div className="grid grid-cols-3 gap-3 text-xs">
                        <div>
                          <div className="text-gray-500">API 호출</div>
                          <div className="font-bold text-gray-800">{u.total_calls.toLocaleString()}회</div>
                        </div>
                        <div>
                          <div className="text-gray-500">Input 토큰</div>
                          <div className="font-bold text-gray-800">{u.input_tokens.toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-gray-500">Output 토큰</div>
                          <div className="font-bold text-gray-800">{u.output_tokens.toLocaleString()}</div>
                        </div>
                      </div>
                      {u.last_used && (
                        <div className="text-[10px] text-gray-400 mt-2">
                          마지막 사용: {u.last_used.replace("T", " ").slice(0, 19)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 최근 데이터 활동 */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 text-sm font-bold text-gray-700">최근 데이터 활동</div>
            <div className="max-h-[300px] overflow-y-auto">
              {dataActivity.length === 0 ? (
                <div className="text-center py-8 text-gray-400 text-sm">기록 없음</div>
              ) : (
                <table className="w-full text-xs">
                  <tbody>
                    {dataActivity.map((log, i) => (
                      <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="px-4 py-2 text-gray-400 whitespace-nowrap">{log.timestamp.replace("T", " ").slice(0, 19)}</td>
                        <td className="px-4 py-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${eventColor(log.event)}`}>{log.event}</span>
                        </td>
                        <td className="px-4 py-2 text-gray-500">{log.email || "-"}</td>
                        <td className="px-4 py-2 text-gray-600">{log.detail}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ═══ 활성 세션 ═══ */}
      {tab === "sessions" && !loading && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 text-sm font-bold text-gray-700">
            활성 세션 ({sessions.length}개) — 최대 2기기/사용자
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50/50">
                <th className="text-left px-4 py-2 font-medium text-gray-600">이메일</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">IP</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">User-Agent</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">로그인 시각</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">토큰</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s, i) => (
                <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs">{s.email}</td>
                  <td className="px-4 py-2 font-mono text-xs text-blue-600">{s.ip || "-"}</td>
                  <td className="px-4 py-2 text-xs text-gray-500 max-w-[300px] truncate">{s.user_agent || "-"}</td>
                  <td className="px-4 py-2 text-xs text-gray-500">{s.login_at?.replace("T", " ").slice(0, 19) || "-"}</td>
                  <td className="px-4 py-2 font-mono text-xs text-gray-400">{s.token_prefix}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ═══ 접속 기록 ═══ */}
      {tab === "login" && !loading && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 text-sm font-bold text-gray-700">로그인/로그아웃 기록</div>
          <div className="max-h-[500px] overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-gray-50">
                <tr className="border-b border-gray-200">
                  <th className="text-left px-4 py-2 font-medium text-gray-600">시각</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">이벤트</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">이메일</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">IP</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">상세</th>
                </tr>
              </thead>
              <tbody>
                {loginHistory.map((log, i) => (
                  <tr key={i} className={`border-b border-gray-100 ${log.event.includes("failed") ? "bg-red-50/50" : ""}`}>
                    <td className="px-4 py-2 text-gray-400 whitespace-nowrap">{log.timestamp.replace("T", " ").slice(0, 19)}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${eventColor(log.event)}`}>{log.event}</span>
                    </td>
                    <td className="px-4 py-2 font-mono">{log.email}</td>
                    <td className="px-4 py-2 font-mono text-blue-600">{log.ip || "-"}</td>
                    <td className="px-4 py-2 text-gray-500">{log.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ═══ 감사 로그 ═══ */}
      {tab === "audit" && (
        <div className="space-y-4">
          {/* 필터 */}
          <div className="flex gap-3 items-end">
            <div>
              <label className="text-xs text-gray-500 block mb-1">이메일</label>
              <input
                value={auditFilter.email}
                onChange={(e) => setAuditFilter((p) => ({ ...p, email: e.target.value }))}
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-48"
                placeholder="필터..."
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">이벤트</label>
              <input
                value={auditFilter.event}
                onChange={(e) => setAuditFilter((p) => ({ ...p, event: e.target.value }))}
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-40"
                placeholder="login, upload..."
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">IP</label>
              <input
                value={auditFilter.ip}
                onChange={(e) => setAuditFilter((p) => ({ ...p, ip: e.target.value }))}
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-36"
                placeholder="IP 주소..."
              />
            </div>
            <button
              onClick={loadAuditLog}
              className="px-4 py-1.5 rounded-lg text-sm font-medium text-white"
              style={{ backgroundColor: PWC.primary }}
            >
              검색
            </button>
            <span className="text-xs text-gray-400">전체 {auditTotal}건</span>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="max-h-[500px] overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-gray-50">
                  <tr className="border-b border-gray-200">
                    <th className="text-left px-4 py-2 font-medium text-gray-600">시각</th>
                    <th className="text-left px-4 py-2 font-medium text-gray-600">이벤트</th>
                    <th className="text-left px-4 py-2 font-medium text-gray-600">이메일</th>
                    <th className="text-left px-4 py-2 font-medium text-gray-600">IP</th>
                    <th className="text-left px-4 py-2 font-medium text-gray-600">상세</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLogs.map((log, i) => (
                    <tr key={i} className={`border-b border-gray-100 hover:bg-gray-50 ${log.event.includes("failed") ? "bg-red-50/30" : ""}`}>
                      <td className="px-4 py-2 text-gray-400 whitespace-nowrap">{log.timestamp.replace("T", " ").slice(0, 19)}</td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${eventColor(log.event)}`}>{log.event}</span>
                      </td>
                      <td className="px-4 py-2 font-mono">{log.email}</td>
                      <td className="px-4 py-2 font-mono text-blue-600">{log.ip || "-"}</td>
                      <td className="px-4 py-2 text-gray-500 max-w-[300px] truncate">{log.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ═══ 업로드 파일 ═══ */}
      {tab === "files" && (
        <div className="space-y-3">
          {/* 헤더 */}
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm font-bold text-gray-700">서버 파일 현황</span>
              <span className="text-xs text-gray-400 ml-2">{uploadDir}</span>
            </div>
            <button onClick={loadFiles} className="text-xs text-gray-400 hover:text-red-500 px-3 py-1.5 border border-gray-200 rounded-lg">새로고침</button>
          </div>

          {/* 서브탭 */}
          <div className="flex gap-0.5 bg-gray-100 p-1 rounded-xl">
            {([
              ["task_excel",    "Task 목록",       uploadedFiles.length],
              ["wf_excel",      "Workflow-Excel",  uploadsAll?.wf_excel.length ?? 0],
              ["wf_json",       "Workflow-JSON",   uploadsAll?.wf_json.length ?? 0],
              ["wf_ppt",        "Workflow-PPTX",   uploadsAll?.wf_ppt.length ?? 0],
              ["new_workflow",  "New Workflow",     uploadsAll?.new_workflow.length ?? 0],
            ] as [typeof fileSubTab, string, number][]).map(([key, label, cnt]) => (
              <button
                key={key}
                onClick={() => setFileSubTab(key)}
                className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition ${
                  fileSubTab === key
                    ? "bg-white shadow text-red-700 font-bold"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                {label}
                <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-bold ${
                  cnt > 0 ? "bg-red-100 text-red-700" : "bg-gray-200 text-gray-400"
                }`}>{cnt}</span>
              </button>
            ))}
          </div>

          {/* 서브탭 설명 */}
          <div className="text-[11px] text-gray-400 px-1">
            {fileSubTab === "task_excel"   && "Task 분류 실행용 엑셀 파일 (분류 탭에서 업로드)"}
            {fileSubTab === "wf_excel"     && "Workflow 설계용 분류 결과 엑셀 (Workflow 탭 > 엑셀 업로드)"}
            {fileSubTab === "wf_json"      && "As-Is 워크플로우 JSON (Workflow 탭 > JSON 업로드) — 서버 재시작 후 자동 복구됨"}
            {fileSubTab === "wf_ppt"       && "As-Is 워크플로우 PPT (Workflow 탭 > PPT 업로드) — 서버 재시작 후 자동 복구됨"}
            {fileSubTab === "new_workflow"  && "New Workflow 생성 결과 및 프로젝트 정의서 JSON"}
          </div>

          {/* 파일 테이블 */}
          <FileTable
            files={
              fileSubTab === "task_excel"   ? uploadedFiles :
              fileSubTab === "wf_excel"     ? (uploadsAll?.wf_excel ?? []) :
              fileSubTab === "wf_json"      ? (uploadsAll?.wf_json ?? []) :
              fileSubTab === "wf_ppt"       ? (uploadsAll?.wf_ppt ?? []) :
                                              (uploadsAll?.new_workflow ?? [])
            }
            onDownload={downloadAdminFile}
            onDelete={async (file) => {
              const sid = (file as { session_id?: string }).session_id;
              const isWfTab = ["wf_excel", "wf_json", "wf_ppt"].includes(fileSubTab);
              try {
                if (fileSubTab === "task_excel") {
                  if (!confirm(`"${file.filename}" 파일을 삭제할까요?`)) return;
                  await deleteAdminUpload(file.filename);
                } else if (isWfTab && sid) {
                  // 세션 기반 파일 → 세션 전체 삭제
                  if (!confirm(`세션 "${sid}" 전체 (Excel + JSON + PPT + 설계 결과)를 삭제할까요?`)) return;
                  await deleteAdminWorkflowSession(sid);
                } else if (isWfTab && !sid) {
                  // 세션 없는 레거시 파일 → 단일 파일만 삭제
                  if (!confirm(`"${file.filename}" 파일을 삭제할까요?`)) return;
                  await deleteAdminWorkflowFile(file.filename);
                } else {
                  return;
                }
                await loadFiles();
              } catch (e) {
                alert(`삭제 실패: ${(e as Error).message}`);
              }
            }}
            showDelete={fileSubTab === "task_excel" || ["wf_excel", "wf_json", "wf_ppt"].includes(fileSubTab)}
          />
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div className={`rounded-lg border px-5 py-4 min-w-[130px] ${accent ? "bg-red-50 border-red-200" : "bg-white border-gray-200"}`}>
      <div className="text-xs text-gray-500">{label}</div>
      <div className={`text-2xl font-bold mt-0.5 ${accent ? "text-red-700" : "text-gray-800"}`}>{value}</div>
    </div>
  );
}

type FileRow = { filename: string; size_kb: number; modified: string; display_name?: string; session_id?: string };

function FileTable({
  files, onDownload, onDelete, showDelete,
}: {
  files: FileRow[];
  onDownload: (name: string) => Promise<void>;
  onDelete?: (file: FileRow) => Promise<void>;
  showDelete?: boolean;
}) {
  if (files.length === 0) {
    return <div className="text-center py-10 text-gray-400 text-sm bg-white rounded-xl border border-gray-200">파일이 없습니다.</div>;
  }
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50/50">
            <th className="text-left px-4 py-2 font-medium text-gray-600">파일명</th>
            <th className="text-right px-4 py-2 font-medium text-gray-600">크기</th>
            <th className="text-left px-4 py-2 font-medium text-gray-600">수정일</th>
            <th className="text-center px-4 py-2 font-medium text-gray-600">다운로드</th>
            {showDelete && <th className="text-center px-4 py-2 font-medium text-gray-600">삭제</th>}
          </tr>
        </thead>
        <tbody>
          {files.map((f) => (
            <tr key={f.filename} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="px-4 py-2 text-xs font-medium text-gray-800 font-mono">
                {f.display_name || f.filename}
              </td>
              <td className="px-4 py-2 text-xs text-gray-500 text-right">{f.size_kb.toLocaleString()} KB</td>
              <td className="px-4 py-2 text-xs text-gray-500">{f.modified.replace("T", " ").slice(0, 19)}</td>
              <td className="px-4 py-2 text-center">
                <button
                  onClick={async () => { try { await onDownload(f.filename); } catch (e) { alert((e as Error).message); } }}
                  className="text-xs text-blue-600 hover:text-blue-800 underline"
                >
                  다운로드
                </button>
              </td>
              {showDelete && (
                <td className="px-4 py-2 text-center">
                  <button
                    onClick={async () => {
                      try {
                        if (onDelete) await onDelete(f);
                      } catch (e) { alert((e as Error).message); }
                    }}
                    className="text-xs text-red-500 hover:text-red-700 underline"
                  >
                    삭제
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
