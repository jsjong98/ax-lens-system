"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getTasks, getResults, getStats, updateResult, deleteAllResults, downloadExport,
  type Task, type ClassificationResult, type StatsResponse, type LabelType,
} from "@/lib/api";
import TaskTable from "@/components/TaskTable";
import StatusBadge from "@/components/StatusBadge";
import { Download, Trash2, RefreshCw, BarChart3 } from "lucide-react";

const PAGE_SIZE = 50;

export default function ResultsPage() {
  const [tasks, setTasks]         = useState<Task[]>([]);
  const [results, setResults]     = useState<ClassificationResult[]>([]);
  const [stats, setStats]         = useState<StatsResponse | null>(null);
  const [total, setTotal]         = useState(0);
  const [page, setPage]           = useState(1);
  const [labelFilter, setLabelFilter] = useState("");
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);

  const taskMap = Object.fromEntries(tasks.map((t) => [t.id, t]));
  const resultMap = Object.fromEntries(results.map((r) => [r.task_id, r]));

  const fetchAll = useCallback(async (p = 1) => {
    setLoading(true);
    setError(null);
    try {
      const [tasksRes, resultsRes, statsRes] = await Promise.all([
        getTasks({ page_size: 500 }),
        getResults({ label: labelFilter || undefined, page: p, page_size: PAGE_SIZE }),
        getStats(),
      ]);
      setTasks(tasksRes.tasks);
      setResults(resultsRes.results);
      setTotal(resultsRes.total);
      setStats(statsRes);
      setPage(p);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [labelFilter]);

  useEffect(() => {
    fetchAll(1);
  }, [fetchAll]);

  const handleLabelChange = async (taskId: string, label: LabelType, reason: string) => {
    await updateResult(taskId, { label, reason });
    await fetchAll(page);
  };

  const handleDeleteAll = async () => {
    if (!confirm("모든 분류 결과를 초기화하시겠습니까?")) return;
    await deleteAllResults();
    await fetchAll(1);
  };

  const rows = results.map((r) => ({
    ...(taskMap[r.task_id] ?? {
      id: r.task_id, l2: "", l2_id: "", l3: "", l3_id: "", l4: "", l4_id: "",
      name: r.task_id, description: "", performer: "",
    }),
    result: r,
  }));

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">결과 확인</h1>
          <p className="mt-1 text-xs text-gray-500">분류 결과를 확인하고 수동으로 수정할 수 있습니다.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => fetchAll(page)} className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50">
            <RefreshCw className="h-4 w-4" /> 새로고침
          </button>
          <button onClick={downloadExport} className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50">
            <Download className="h-4 w-4" /> 엑셀 다운로드
          </button>
          <button onClick={handleDeleteAll} className="flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50">
            <Trash2 className="h-4 w-4" /> 초기화
          </button>
        </div>
      </div>

      {/* 에러 */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          오류: {error}
        </div>
      )}

      {/* 통계 카드 */}
      {stats && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {([
            { label: "전체 Task",    value: stats.total,                              cardStyle: { background: "#fff", border: "1px solid #E2E8F0" }, valueStyle: { color: "#171717" } },
            { label: "AI 수행 가능", value: `${stats.ai_count} (${stats.ai_ratio}%)`, cardStyle: { background: "#FFF5F7", border: "1px solid #F2A0AF" }, valueStyle: { color: "#A62121" } },
            { label: "인간 수행 필요", value: `${stats.human_count} (${stats.human_ratio}%)`, cardStyle: { background: "#ECFDF5", border: "1px solid #A7F3D0" }, valueStyle: { color: "#065F46" } },
            { label: "미분류",        value: stats.unclassified_count,                 cardStyle: { background: "#fff", border: "1px solid #E2E8F0" }, valueStyle: { color: "#6B7280" } },
          ] as const).map((s) => (
            <div key={s.label} className="rounded-xl p-4 shadow-sm" style={s.cardStyle}>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">{s.label}</p>
              <p className="mt-1.5 text-xl font-bold" style={s.valueStyle}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* L3별 통계 (접기 가능) */}
      {stats && stats.by_l3.length > 0 && (
        <details className="rounded-xl border border-gray-200 bg-white shadow-sm">
          <summary className="flex cursor-pointer items-center gap-2 px-5 py-4 text-xs font-semibold text-gray-600 hover:bg-gray-50">
            <BarChart3 className="h-4 w-4" />
            L3 Unit Process별 분류 현황
          </summary>
          <div className="px-5 pb-5">
            <div className="space-y-2">
              {stats.by_l3.map((row) => {
                const aiPct = row.total > 0 ? Math.round((row.ai / row.total) * 100) : 0;
                return (
                  <div key={row.l3} className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-4 text-sm">
                    <span className="truncate text-gray-700">{row.l3}</span>
                    <span className="w-16 text-right text-xs text-emerald-600">AI {row.ai}</span>
                    <span className="w-16 text-right text-xs text-orange-600">인간 {row.human}</span>
                    <div className="w-28 flex items-center gap-1">
                      <div className="flex-1 h-1.5 rounded-full bg-gray-200">
                        <div className="h-1.5 rounded-full bg-emerald-500" style={{ width: `${aiPct}%` }} />
                      </div>
                      <span className="text-xs text-gray-500 w-8 text-right">{aiPct}%</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </details>
      )}

      {/* 필터 */}
      <div className="flex items-center gap-3">
        <label className="text-xs font-medium text-gray-500">레이블 필터:</label>
        {(["", "AI 수행 가능", "인간 수행 필요", "미분류"] as const).map((l) => (
          <button
            key={l || "all"}
            onClick={() => setLabelFilter(l)}
            className="rounded-full px-3 py-1 text-xs font-medium transition-colors"
            style={labelFilter === l
              ? { backgroundColor: "#A62121", color: "#ffffff" }
              : { backgroundColor: "#F3F4F6", color: "#4B5563" }}
            onMouseEnter={(e) => { if (labelFilter !== l) (e.currentTarget as HTMLElement).style.backgroundColor = "#F2DCE0"; }}
            onMouseLeave={(e) => { if (labelFilter !== l) (e.currentTarget as HTMLElement).style.backgroundColor = "#F3F4F6"; }}
          >
            {l || "전체"}
          </button>
        ))}
      </div>

      {/* 테이블 */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full" style={{ border: "4px solid #A62121", borderTopColor: "transparent" }} />
        </div>
      ) : (
        <TaskTable rows={rows} showResult onLabelChange={handleLabelChange} />
      )}

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-gray-600">
          <span>전체 {total}개 중 {(page-1)*PAGE_SIZE + 1}–{Math.min(page*PAGE_SIZE, total)}개 표시</span>
          <div className="flex gap-2">
            <button disabled={page === 1} onClick={() => fetchAll(page - 1)} className="rounded-lg border border-gray-300 px-3 py-1.5 hover:bg-gray-50 disabled:opacity-40">이전</button>
            <span className="flex items-center px-2">{page} / {totalPages}</span>
            <button disabled={page === totalPages} onClick={() => fetchAll(page + 1)} className="rounded-lg border border-gray-300 px-3 py-1.5 hover:bg-gray-50 disabled:opacity-40">다음</button>
          </div>
        </div>
      )}

      {rows.length === 0 && !loading && (
        <div className="rounded-xl border border-dashed border-gray-300 py-16 text-center text-sm text-gray-500">
          아직 분류 결과가 없습니다.{" "}
          <a href="/classify" className="hover:underline" style={{ color: "#A62121" }}>분류 실행 페이지</a>에서 분류를 시작하세요.
        </div>
      )}
    </div>
  );
}
