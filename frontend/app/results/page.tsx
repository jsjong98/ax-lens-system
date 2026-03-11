"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getTasks, getResults, getStats, getComparisonResults,
  updateResult, deleteAllResults, downloadExport, downloadCompareExport,
  type Task, type ClassificationResult, type StatsResponse, type LabelType,
  type ProviderType, type ComparisonItem,
} from "@/lib/api";
import TaskTable from "@/components/TaskTable";
import StatusBadge from "@/components/StatusBadge";
import { Download, Trash2, RefreshCw, BarChart3, GitCompare } from "lucide-react";

const PAGE_SIZE = 50;

type ViewMode = "openai" | "anthropic" | "compare";

const PROVIDER_META: Record<ProviderType, { label: string; model: string; color: string; bg: string; border: string }> = {
  openai:    { label: "O 모델", model: "O 모델", color: "#10a37f", bg: "#f0fdf4", border: "#86efac" },
  anthropic: { label: "A 모델", model: "A 모델", color: "#c96442", bg: "#fff7ed", border: "#fdba74" },
};

// ── 비교 테이블 ───────────────────────────────────────────────────────────────

function CompareTable({
  tasks, comparison, total, page, onPageChange,
}: {
  tasks: Task[];
  comparison: ComparisonItem[];
  total: number;
  page: number;
  onPageChange: (p: number) => void;
}) {
  const taskMap = Object.fromEntries(tasks.map((t) => [t.id, t]));
  const totalPages = Math.ceil(total / PAGE_SIZE);

  const labelBadge = (label: LabelType | null) => {
    if (!label) return <span className="text-xs text-gray-400">-</span>;
    return <StatusBadge label={label} />;
  };

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Task</th>
              <th className="px-4 py-3 text-center text-xs font-semibold" style={{ color: "#10a37f" }}>O 모델</th>
              <th className="px-4 py-3 text-center text-xs font-semibold" style={{ color: "#c96442" }}>A 모델</th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500">일치</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {comparison.map((item) => {
              const task = taskMap[item.task_id];
              const isMatch = item.match === true;
              const isMismatch = item.match === false;
              return (
                <tr
                  key={item.task_id}
                  className="hover:bg-gray-50 transition-colors"
                  style={isMismatch ? { backgroundColor: "#fff7f7" } : undefined}
                >
                  <td className="px-4 py-3 max-w-xs">
                    <p className="font-medium text-gray-800 truncate">{task?.name ?? item.task_id}</p>
                    {task && (
                      <p className="text-xs text-gray-400 truncate mt-0.5">{task.l3} › {task.l4}</p>
                    )}
                    <p className="text-[11px] text-gray-300 mt-0.5">{item.task_id}</p>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex flex-col items-center gap-1">
                      {labelBadge(item.openai_label)}
                      {item.openai_confidence != null && (
                        <span className="text-[10px] text-gray-400">{Math.round(item.openai_confidence * 100)}%</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex flex-col items-center gap-1">
                      {labelBadge(item.anthropic_label)}
                      {item.anthropic_confidence != null && (
                        <span className="text-[10px] text-gray-400">{Math.round(item.anthropic_confidence * 100)}%</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {item.match === null ? (
                      <span className="text-xs text-gray-300">-</span>
                    ) : isMatch ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 border border-emerald-200">
                        ✓ 일치
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700 border border-red-200">
                        ✗ 불일치
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {comparison.length === 0 && (
          <div className="py-12 text-center text-sm text-gray-400">
            비교할 데이터가 없습니다. OpenAI와 Claude 각각 분류를 먼저 실행해 주세요.
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-gray-600">
          <span>전체 {total}개</span>
          <div className="flex gap-2">
            <button disabled={page === 1} onClick={() => onPageChange(page - 1)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 hover:bg-gray-50 disabled:opacity-40">이전</button>
            <span className="flex items-center px-2">{page} / {totalPages}</span>
            <button disabled={page === totalPages} onClick={() => onPageChange(page + 1)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 hover:bg-gray-50 disabled:opacity-40">다음</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── 메인 페이지 ───────────────────────────────────────────────────────────────

export default function ResultsPage() {
  const [viewMode, setViewMode]   = useState<ViewMode>("openai");
  const [tasks, setTasks]         = useState<Task[]>([]);
  const [results, setResults]     = useState<ClassificationResult[]>([]);
  const [stats, setStats]         = useState<StatsResponse | null>(null);
  const [total, setTotal]         = useState(0);
  const [page, setPage]           = useState(1);
  const [labelFilter, setLabelFilter] = useState("");
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);

  // 비교 뷰 상태
  const [compareData, setCompareData] = useState<ComparisonItem[]>([]);
  const [compareTotal, setCompareTotal] = useState(0);
  const [compareMeta, setCompareMeta] = useState({ both_classified: 0, matching: 0, match_rate: 0 });
  const [comparePage, setComparePage] = useState(1);

  const taskMap = Object.fromEntries(tasks.map((t) => [t.id, t]));
  const resultMap = Object.fromEntries(results.map((r) => [r.task_id, r]));

  const fetchProviderData = useCallback(async (mode: ProviderType, p = 1) => {
    setLoading(true);
    setError(null);
    try {
      const [tasksRes, resultsRes, statsRes] = await Promise.all([
        getTasks({ page_size: 500 }),
        getResults({ label: labelFilter || undefined, provider: mode, page: p, page_size: PAGE_SIZE }),
        getStats(mode),
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

  const fetchCompareData = useCallback(async (p = 1) => {
    setLoading(true);
    setError(null);
    try {
      const [tasksRes, compareRes] = await Promise.all([
        getTasks({ page_size: 500 }),
        getComparisonResults({ page: p, page_size: PAGE_SIZE }),
      ]);
      setTasks(tasksRes.tasks);
      setCompareData(compareRes.comparison);
      setCompareTotal(compareRes.total);
      setCompareMeta({
        both_classified: compareRes.both_classified,
        matching: compareRes.matching,
        match_rate: compareRes.match_rate,
      });
      setComparePage(p);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAll = useCallback(async (p = 1) => {
    if (viewMode === "compare") {
      await fetchCompareData(p);
    } else {
      await fetchProviderData(viewMode, p);
    }
  }, [viewMode, fetchProviderData, fetchCompareData]);

  useEffect(() => {
    fetchAll(1);
  }, [fetchAll]);

  const handleLabelChange = async (taskId: string, label: LabelType, reason: string) => {
    if (viewMode === "compare") return;
    await updateResult(taskId, { label, reason }, viewMode);
    await fetchAll(page);
  };

  const handleDeleteAll = async () => {
    if (viewMode === "compare") {
      if (!confirm("OpenAI와 Claude 결과를 모두 초기화하시겠습니까?")) return;
      await deleteAllResults("all");
    } else {
      const providerLabel = PROVIDER_META[viewMode].label;
      if (!confirm(`${providerLabel} 분류 결과를 초기화하시겠습니까?`)) return;
      await deleteAllResults(viewMode);
    }
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

  const tabs: { id: ViewMode; label: string; icon?: React.ReactNode }[] = [
    { id: "openai",    label: "O 모델" },
    { id: "anthropic", label: "A 모델" },
    { id: "compare",   label: "비교" },
  ];

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
          {viewMode !== "compare" ? (
            <button
              onClick={() => downloadExport(viewMode)}
              className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
            >
              <Download className="h-4 w-4" />
              {PROVIDER_META[viewMode].label} 엑셀
            </button>
          ) : (
            <button
              onClick={downloadCompareExport}
              className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
            >
              <GitCompare className="h-4 w-4" /> 비교 엑셀
            </button>
          )}
          <button onClick={handleDeleteAll} className="flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50">
            <Trash2 className="h-4 w-4" /> 초기화
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          오류: {error}
        </div>
      )}

      {/* Provider 탭 */}
      <div className="flex gap-1 rounded-xl border border-gray-200 bg-gray-50 p-1">
        {tabs.map((tab) => {
          const isActive = viewMode === tab.id;
          const meta = tab.id !== "compare" ? PROVIDER_META[tab.id as ProviderType] : null;
          return (
            <button
              key={tab.id}
              onClick={() => { setViewMode(tab.id); setLabelFilter(""); }}
              className="flex-1 flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all"
              style={isActive
                ? { backgroundColor: meta?.color ?? "#374151", color: "#fff", boxShadow: "0 1px 3px rgba(0,0,0,0.12)" }
                : { color: "#6B7280" }}
            >
              {tab.id === "compare" && <GitCompare className="h-3.5 w-3.5" />}
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* ── 비교 뷰 ── */}
      {viewMode === "compare" && !loading && (
        <>
          {/* 비교 요약 카드 */}
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "비교 대상 Task", value: compareTotal, sub: "두 모델 모두 분류된 것" },
              { label: "일치", value: compareMeta.matching, sub: `${compareMeta.match_rate}%`, valueColor: "#065F46" },
              { label: "불일치", value: compareMeta.both_classified - compareMeta.matching, sub: "재검토 권장", valueColor: "#991B1B" },
            ].map((s) => (
              <div key={s.label} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">{s.label}</p>
                <p className="mt-1.5 text-2xl font-bold" style={{ color: s.valueColor ?? "#171717" }}>{s.value}</p>
                <p className="mt-0.5 text-xs text-gray-400">{s.sub}</p>
              </div>
            ))}
          </div>

          <CompareTable
            tasks={tasks}
            comparison={compareData}
            total={compareTotal}
            page={comparePage}
            onPageChange={(p) => fetchCompareData(p)}
          />
        </>
      )}

      {/* ── 개별 provider 뷰 ── */}
      {viewMode !== "compare" && (
        <>
          {/* 통계 카드 */}
          {stats && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
              {([
                { label: "전체 Task",     value: stats.total,                                        cardStyle: { background: "#fff", border: "1px solid #E2E8F0" },      valueStyle: { color: "#171717" } },
                { label: "AI 수행 가능",  value: `${stats.ai_count} (${stats.ai_ratio}%)`,           cardStyle: { background: "#FFF5F7", border: "1px solid #F2A0AF" },   valueStyle: { color: "#A62121" } },
                { label: "AI + Human",   value: `${stats.hybrid_count} (${stats.hybrid_ratio}%)`,   cardStyle: { background: "#FFFBEB", border: "1px solid #FCD34D" },   valueStyle: { color: "#92400E" } },
                { label: "인간 수행 필요", value: `${stats.human_count} (${stats.human_ratio}%)`,    cardStyle: { background: "#ECFDF5", border: "1px solid #A7F3D0" },   valueStyle: { color: "#065F46" } },
                { label: "미분류",         value: stats.unclassified_count,                          cardStyle: { background: "#fff", border: "1px solid #E2E8F0" },      valueStyle: { color: "#6B7280" } },
              ] as const).map((s) => (
                <div key={s.label} className="rounded-xl p-4 shadow-sm" style={s.cardStyle}>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">{s.label}</p>
                  <p className="mt-1.5 text-xl font-bold" style={s.valueStyle}>{s.value}</p>
                </div>
              ))}
            </div>
          )}

          {/* L3별 통계 */}
          {stats && stats.by_l3.length > 0 && (
            <details className="rounded-xl border border-gray-200 bg-white shadow-sm">
              <summary className="flex cursor-pointer items-center gap-2 px-5 py-4 text-xs font-semibold text-gray-600 hover:bg-gray-50">
                <BarChart3 className="h-4 w-4" />
                L3 Unit Process별 분류 현황
              </summary>
              <div className="px-5 pb-5">
                <div className="space-y-2">
                  {stats.by_l3.map((row) => {
                    const aiPct  = row.total > 0 ? Math.round((row.ai / row.total) * 100) : 0;
                    const hybPct = row.total > 0 ? Math.round(((row.hybrid ?? 0) / row.total) * 100) : 0;
                    return (
                      <div key={row.l3} className="grid grid-cols-[1fr_auto_auto_auto_auto] items-center gap-4 text-sm">
                        <span className="truncate text-gray-700">{row.l3}</span>
                        <span className="w-16 text-right text-xs text-red-600">AI {row.ai}</span>
                        <span className="w-20 text-right text-xs text-amber-600">AI+H {row.hybrid ?? 0}</span>
                        <span className="w-16 text-right text-xs text-emerald-600">인간 {row.human}</span>
                        <div className="w-28 flex items-center gap-1">
                          <div className="flex-1 h-1.5 rounded-full bg-gray-200 overflow-hidden flex">
                            <div className="h-1.5 bg-red-400" style={{ width: `${aiPct}%` }} />
                            <div className="h-1.5 bg-amber-400" style={{ width: `${hybPct}%` }} />
                          </div>
                          <span className="text-xs text-gray-500 w-8 text-right">{aiPct + hybPct}%</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </details>
          )}

          {/* 레이블 필터 */}
          <div className="flex items-center gap-3">
            <label className="text-xs font-medium text-gray-500">레이블 필터:</label>
            {(["", "AI 수행 가능", "AI + Human", "인간 수행 필요", "미분류"] as const).map((l) => (
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
        </>
      )}

      {viewMode === "compare" && loading && (
        <div className="flex items-center justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full" style={{ border: "4px solid #A62121", borderTopColor: "transparent" }} />
        </div>
      )}
    </div>
  );
}
