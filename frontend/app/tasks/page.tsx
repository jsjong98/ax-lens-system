"use client";

import { useEffect, useState, useCallback } from "react";
import { getTasks, getFilterOptions, getProjectList, loadProject, type Task, type FilterOptions, type ProjectInfo } from "@/lib/api";
import TaskTable from "@/components/TaskTable";
import ExcelUploader from "@/components/ExcelUploader";
import { Search, SlidersHorizontal, RefreshCw, FolderOpen, Clock, FileSpreadsheet, CheckCircle2 } from "lucide-react";

const PAGE_SIZE = 50;

export default function TasksPage() {
  const [tasks, setTasks]         = useState<Task[]>([]);
  const [total, setTotal]         = useState(0);
  const [page, setPage]           = useState(1);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [filters, setFilters]     = useState<FilterOptions>({ l2: [], l3: [], l4: [] });
  const [search, setSearch]       = useState("");
  const [selL3, setSelL3]         = useState("");
  const [selL4, setSelL4]         = useState("");

  // 이전 프로젝트
  const [projects, setProjects]   = useState<ProjectInfo[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [loadingProject, setLoadingProject] = useState<string | null>(null);

  const fetchData = useCallback(async (p = 1) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getTasks({ search: search || undefined, l3: selL3 || undefined, l4: selL4 || undefined, page: p, page_size: PAGE_SIZE });
      setTasks(res.tasks);
      setTotal(res.total);
      setPage(p);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [search, selL3, selL4]);

  useEffect(() => {
    getFilterOptions().then(setFilters).catch(() => {});
    getProjectList().then((r) => setProjects(r.projects)).catch(() => {});
  }, []);

  const handleLoadProject = async (filename: string) => {
    setLoadingProject(filename);
    try {
      await loadProject(filename);
      await fetchData(1);
      getFilterOptions().then(setFilters).catch(() => {});
      setShowHistory(false);
    } catch {
    } finally {
      setLoadingProject(null);
    }
  };

  useEffect(() => {
    const t = setTimeout(() => fetchData(1), 300);
    return () => clearTimeout(t);
  }, [fetchData]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Task 목록</h1>
          <p className="mt-1 text-xs text-gray-500">
            HR As-Is 프로세스의 L5 Task를 탐색합니다.
            {total > 0 && <span className="ml-1 font-medium" style={{ color: "#A62121" }}>{total}개</span>}
          </p>
        </div>
        <button onClick={() => fetchData(1)} className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50">
          <RefreshCw className="h-4 w-4" /> 새로고침
        </button>
      </div>

      {/* 엑셀 업로드 */}
      <ExcelUploader onUploaded={() => {
        fetchData(1);
        getProjectList().then((r) => setProjects(r.projects)).catch(() => {});
      }} />

      {/* 이전 프로젝트 불러오기 */}
      {projects.length > 0 && (
        <div className="rounded-xl border bg-white shadow-sm overflow-hidden">
          <button
            onClick={() => setShowHistory((v) => !v)}
            className="w-full flex items-center justify-between px-5 py-3 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <FolderOpen className="h-4 w-4" style={{ color: "#A62121" }} />
              <span className="text-sm font-semibold text-gray-900">이전 프로젝트 불러오기</span>
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
                            <Clock className="h-3 w-3" />
                            {new Date(p.created_at).toLocaleDateString("ko-KR")}
                          </span>
                        )}
                        {p.task_count && (
                          <span className="text-[10px] text-gray-400">{p.task_count}개 Task</span>
                        )}
                        {p.has_any_result && (
                          <span className="flex items-center gap-0.5 text-[10px] text-green-600">
                            <CheckCircle2 className="h-3 w-3" /> 결과 있음
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleLoadProject(p.filename || p.dirname)}
                    disabled={loadingProject === (p.filename || p.dirname)}
                    className="flex-shrink-0 rounded-lg px-3 py-1.5 text-xs font-semibold text-white transition-opacity disabled:opacity-50"
                    style={{ backgroundColor: "#A62121" }}
                  >
                    {loadingProject === (p.filename || p.dirname) ? "로딩..." : "불러오기"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 필터 바 */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Task명 또는 설명 검색..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-300 py-2 pl-9 pr-4 text-sm focus:outline-none"
            onFocus={(e) => { e.currentTarget.style.borderColor = "#A62121"; e.currentTarget.style.boxShadow = "0 0 0 1px #A62121"; }}
            onBlur={(e) => { e.currentTarget.style.borderColor = ""; e.currentTarget.style.boxShadow = ""; }}
          />
        </div>

        <div className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-gray-400" />
          <select
            value={selL3}
            onChange={(e) => setSelL3(e.target.value)}
            className="rounded-lg border border-gray-300 py-2 px-3 text-sm focus:outline-none"
            onFocus={(e) => (e.currentTarget.style.borderColor = "#A62121")}
            onBlur={(e) => (e.currentTarget.style.borderColor = "")}
          >
            <option value="">L3 전체</option>
            {filters.l3.map((o) => (
              <option key={o.id} value={o.name}>{o.name}</option>
            ))}
          </select>

          <select
            value={selL4}
            onChange={(e) => setSelL4(e.target.value)}
            className="rounded-lg border border-gray-300 py-2 px-3 text-sm focus:outline-none"
            onFocus={(e) => (e.currentTarget.style.borderColor = "#A62121")}
            onBlur={(e) => (e.currentTarget.style.borderColor = "")}
          >
            <option value="">L4 전체</option>
            {filters.l4.map((o) => (
              <option key={o.id} value={o.name}>{o.name}</option>
            ))}
          </select>

          {(search || selL3 || selL4) && (
            <button
              onClick={() => { setSearch(""); setSelL3(""); setSelL4(""); }}
              className="text-sm hover:underline"
              style={{ color: "#A62121" }}
            >
              초기화
            </button>
          )}
        </div>
      </div>

      {/* 에러 */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          백엔드 연결 실패: {error}. FastAPI 서버가 실행 중인지 확인해 주세요.
        </div>
      )}

      {/* 테이블 */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full" style={{ border: "4px solid #A62121", borderTopColor: "transparent" }} />
        </div>
      ) : total === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-200 bg-gray-50 py-20 text-center">
          <svg className="mb-4 h-12 w-12 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-sm font-medium text-gray-500">엑셀 파일을 먼저 업로드해 주세요</p>
          <p className="mt-1 text-xs text-gray-400">위의 업로드 영역에 HR As-Is 템플릿 .xlsx 파일을 올리면 Task 목록이 표시됩니다.</p>
        </div>
      ) : (
        <TaskTable rows={tasks} showResult={false} />
      )}

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-gray-600">
          <span>전체 {total}개 중 {(page-1)*PAGE_SIZE + 1}–{Math.min(page*PAGE_SIZE, total)}개 표시</span>
          <div className="flex gap-2">
            <button
              disabled={page === 1}
              onClick={() => fetchData(page - 1)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 hover:bg-gray-50 disabled:opacity-40"
            >
              이전
            </button>
            <span className="flex items-center px-2">{page} / {totalPages}</span>
            <button
              disabled={page === totalPages}
              onClick={() => fetchData(page + 1)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 hover:bg-gray-50 disabled:opacity-40"
            >
              다음
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
