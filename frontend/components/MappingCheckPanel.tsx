"use client";

import { useState, useCallback, useEffect } from "react";
import {
  getMappingCheck, setManualMatch, deleteManualMatch,
  getWorkflowExcelTasks,
  type MappingCheckResult, type MappingL4Node, type WorkflowExcelTask,
} from "@/lib/api";
import { RefreshCw, ChevronDown, ChevronRight, CheckCircle, XCircle, AlertCircle, Link2, Pencil, Trash2, X } from "lucide-react";

// ── 분류 스타일 ────────────────────────────────────────────────────────────
const CLS: Record<string, { bg: string; text: string; bar: string }> = {
  "AI":         { bg: "#DCFCE7", text: "#15803D", bar: "#22C55E" },
  "AI + Human": { bg: "#FEF9C3", text: "#A16207", bar: "#EAB308" },
  "Human":      { bg: "#FEE2E2", text: "#DC2626", bar: "#EF4444" },
  "미분류":     { bg: "#F3F4F6", text: "#6B7280", bar: "#9CA3AF" },
};
const CLS_ORDER = ["AI", "AI + Human", "Human", "미분류"];

function LabelBadge({ label }: { label: string }) {
  const s = CLS[label] || CLS["미분류"];
  return (
    <span className="px-1.5 py-0.5 rounded text-[9px] font-bold" style={{ backgroundColor: s.bg, color: s.text }}>
      {label}
    </span>
  );
}

function PainBadge({ points }: { points: string[] }) {
  if (!points.length) return null;
  return (
    <span className="px-1.5 py-0.5 rounded text-[9px] bg-orange-50 text-orange-600 border border-orange-200">
      ⚡ {points[0]}{points.length > 1 ? ` +${points.length - 1}` : ""}
    </span>
  );
}

// ── 분류 집계 미니 바 ──────────────────────────────────────────────────────
function ClsSummaryBar({ counts, total }: { counts: Record<string, number>; total: number }) {
  if (!total) return null;
  return (
    <div className="flex items-center gap-1.5">
      {/* 스택 바 */}
      <div className="flex h-2 rounded overflow-hidden" style={{ width: 60 }}>
        {CLS_ORDER.map((k) => {
          const n = counts[k] || 0;
          if (!n) return null;
          return (
            <div key={k} style={{ width: `${(n / total) * 100}%`, backgroundColor: CLS[k].bar }} title={`${k}: ${n}`} />
          );
        })}
      </div>
      {/* 숫자 뱃지 */}
      {CLS_ORDER.map((k) => {
        const n = counts[k] || 0;
        if (!n) return null;
        return (
          <span key={k} className="text-[9px] font-bold px-1.5 py-0.5 rounded" style={{ backgroundColor: CLS[k].bg, color: CLS[k].text }}>
            {k === "AI + Human" ? "A+H" : k} {n}
          </span>
        );
      })}
    </div>
  );
}

// ── L4 노드 행 ─────────────────────────────────────────────────────────────
function L4Row({
  node, excelTasks, onManualMatch, onDeleteMatch,
}: {
  node: MappingL4Node;
  excelTasks: WorkflowExcelTask[];
  onManualMatch: (jsonTaskId: string, excelTaskId: string) => Promise<void>;
  onDeleteMatch: (jsonTaskId: string) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [editingL5, setEditingL5] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const hasAnyMatch = node.matched_l5 > 0;
  const cls = node.cls_summary || {};

  const filteredTasks = excelTasks.filter((t) =>
    !searchQuery || t.name.toLowerCase().includes(searchQuery.toLowerCase()) || t.id.includes(searchQuery)
  );

  const handleSelect = async (l5TaskId: string, excelTaskId: string) => {
    await onManualMatch(l5TaskId, excelTaskId);
    setEditingL5(null);
    setSearchQuery("");
  };

  const handleDelete = async (l5TaskId: string) => {
    await onDeleteMatch(l5TaskId);
  };

  return (
    <div className={`border rounded-lg mb-1 ${hasAnyMatch ? "border-green-200 bg-green-50/30" : "border-gray-200 bg-gray-50/30"}`}>
      <button
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-white/60 transition-colors rounded-lg"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <ChevronDown className="h-3.5 w-3.5 text-gray-400 shrink-0" /> : <ChevronRight className="h-3.5 w-3.5 text-gray-400 shrink-0" />}
        {hasAnyMatch
          ? <CheckCircle className="h-3.5 w-3.5 text-green-500 shrink-0" />
          : <XCircle className="h-3.5 w-3.5 text-red-400 shrink-0" />}
        <span className="font-mono text-[10px] text-gray-400 shrink-0">{node.task_id}</span>
        <span className="text-xs font-medium text-gray-700 flex-1 truncate">{node.label}</span>

        <div className="flex items-center gap-2 shrink-0">
          {hasAnyMatch && <ClsSummaryBar counts={cls} total={node.matched_l5} />}
          <span className={`text-[10px] font-bold ${hasAnyMatch ? "text-green-600" : "text-gray-400"}`}>
            {node.matched_l5}/{node.total_l5} L5
          </span>
        </div>
      </button>

      {open && node.l5_nodes.length > 0 && (
        <div className="px-3 pb-3 space-y-1">
          <div className="text-[10px] font-semibold text-gray-500 mb-1 flex items-center gap-1">
            <Link2 className="h-3 w-3" /> L5 노드 ({node.total_l5}개 · 연결 {node.matched_l5}개)
          </div>
          {node.l5_nodes.map((l5) => (
            <div key={l5.task_id} className="space-y-1">
              <div
                className={`rounded border px-2.5 py-1.5 flex items-start gap-2 ${
                  !l5.matched ? "bg-gray-50 border-gray-200"
                  : l5.manual_matched ? "bg-blue-50 border-blue-200"
                  : l5.fuzzy_matched ? "bg-yellow-50 border-yellow-200"
                  : "bg-white border-green-100"
                }`}
              >
                {!l5.matched
                  ? <XCircle className="h-3.5 w-3.5 text-gray-300 shrink-0 mt-0.5" />
                  : l5.manual_matched
                  ? <Link2 className="h-3.5 w-3.5 text-blue-500 shrink-0 mt-0.5" />
                  : l5.fuzzy_matched
                  ? <AlertCircle className="h-3.5 w-3.5 text-yellow-400 shrink-0 mt-0.5" />
                  : <CheckCircle className="h-3.5 w-3.5 text-green-400 shrink-0 mt-0.5" />}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono text-[9px] text-gray-400">{l5.task_id}</span>
                    <span className="text-xs text-gray-700 font-medium truncate">{l5.label}</span>
                  </div>
                  {l5.matched && l5.excel_name && (
                    <div className={`text-[10px] mt-0.5 truncate ${
                      l5.manual_matched ? "text-blue-700" : l5.fuzzy_matched ? "text-yellow-700" : "text-gray-500"
                    }`}>
                      {l5.manual_matched ? `⚙ ${l5.excel_name}` : l5.fuzzy_matched ? `≈ ${l5.excel_name}` : `↳ ${l5.excel_name}`}
                      {l5.fuzzy_matched && !l5.manual_matched && (
                        <span className="ml-1 text-yellow-500">(유사 {Math.round(l5.fuzzy_score * 100)}%)</span>
                      )}
                    </div>
                  )}
                  {l5.matched && l5.description && (
                    <div className="text-[10px] text-gray-400 mt-0.5 line-clamp-1">{l5.description}</div>
                  )}
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {l5.matched && l5.cls_label && <LabelBadge label={l5.cls_label} />}
                  {l5.matched && <PainBadge points={l5.pain_points} />}
                  {/* 수동 매칭된 경우: 연결 해제 버튼 */}
                  {l5.manual_matched && (
                    <button
                      onClick={() => handleDelete(l5.task_id)}
                      className="p-0.5 rounded hover:bg-red-100 text-gray-400 hover:text-red-500 transition"
                      title="수동 연결 해제"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  )}
                  {/* 미연결 또는 퍼지 매칭: 직접 연결 버튼 */}
                  {(!l5.matched || l5.fuzzy_matched) && editingL5 !== l5.task_id && (
                    <button
                      onClick={(e) => { e.stopPropagation(); setEditingL5(l5.task_id); setSearchQuery(""); }}
                      className="flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-bold bg-blue-100 text-blue-600 hover:bg-blue-200 transition"
                      title="직접 연결"
                    >
                      <Pencil className="h-2.5 w-2.5" /> 직접 연결
                    </button>
                  )}
                  {/* 닫기 */}
                  {editingL5 === l5.task_id && (
                    <button
                      onClick={() => { setEditingL5(null); setSearchQuery(""); }}
                      className="p-0.5 rounded hover:bg-gray-200 text-gray-400 transition"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  )}
                </div>
              </div>

              {/* 인라인 검색 패널 */}
              {editingL5 === l5.task_id && (
                <div className="ml-5 border border-blue-200 rounded-lg bg-blue-50 p-2 space-y-1.5">
                  <div className="text-[10px] font-bold text-blue-700">엑셀 Task 검색 후 선택하세요</div>
                  <input
                    autoFocus
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Task명 또는 ID 검색..."
                    className="w-full text-xs border border-blue-200 rounded px-2 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
                  />
                  <div className="max-h-40 overflow-y-auto space-y-0.5">
                    {filteredTasks.slice(0, 30).map((t) => (
                      <button
                        key={t.id}
                        onClick={() => handleSelect(l5.task_id, t.id)}
                        className="w-full text-left px-2 py-1 rounded hover:bg-blue-100 transition"
                      >
                        <span className="font-mono text-[9px] text-gray-400 mr-1">{t.id}</span>
                        <span className="text-[11px] text-gray-700">{t.name}</span>
                        {t.l4 && <span className="ml-1 text-[9px] text-gray-400">({t.l4})</span>}
                      </button>
                    ))}
                    {filteredTasks.length === 0 && (
                      <div className="text-[10px] text-gray-400 text-center py-2">검색 결과 없음</div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── 전체 분류 현황 바 ──────────────────────────────────────────────────────
function ClsOverviewBar({ counts, total, title }: { counts: Record<string, number>; total: number; title: string }) {
  if (!total) return null;
  return (
    <div>
      <div className="text-[10px] text-gray-500 mb-1">{title} ({total}개)</div>
      <div className="flex h-4 rounded-full overflow-hidden border border-gray-200 mb-1">
        {CLS_ORDER.map((k) => {
          const n = counts[k] || 0;
          if (!n) return null;
          return (
            <div
              key={k}
              style={{ width: `${(n / total) * 100}%`, backgroundColor: CLS[k].bar }}
              className="relative group"
              title={`${k}: ${n}개 (${Math.round((n / total) * 100)}%)`}
            />
          );
        })}
      </div>
      <div className="flex flex-wrap gap-2">
        {CLS_ORDER.map((k) => {
          const n = counts[k] || 0;
          if (!n) return null;
          return (
            <div key={k} className="flex items-center gap-1">
              <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: CLS[k].bar }} />
              <span className="text-[10px] text-gray-600">{k} <strong>{n}</strong> ({Math.round((n / total) * 100)}%)</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── 메인 패널 ──────────────────────────────────────────────────────────────
interface MappingCheckPanelProps {
  hasExcel: boolean;
  hasAsIs: boolean;
  activeSheetId?: string | null;  // 페이지 레벨에서 선택된 시트 ID
}

export default function MappingCheckPanel({ hasExcel, hasAsIs, activeSheetId }: MappingCheckPanelProps) {
  const [result, setResult] = useState<MappingCheckResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showExcelOnly, setShowExcelOnly] = useState(false);
  const [excelTasks, setExcelTasks] = useState<WorkflowExcelTask[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [r, et] = await Promise.all([getMappingCheck(), getWorkflowExcelTasks()]);
      setResult(r);
      setExcelTasks(et.tasks || []);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleManualMatch = useCallback(async (jsonTaskId: string, excelTaskId: string) => {
    await setManualMatch(jsonTaskId, excelTaskId);
    await load();
  }, [load]);

  const handleDeleteMatch = useCallback(async (jsonTaskId: string) => {
    await deleteManualMatch(jsonTaskId);
    await load();
  }, [load]);

  // 엑셀 + As-Is 모두 있으면 자동 로드
  useEffect(() => {
    if (hasExcel && hasAsIs && !result && !loading) {
      load();
    }
  }, [hasExcel, hasAsIs, result, loading, load]);

  const canCheck = hasExcel || hasAsIs;
  const clsMatched = result?.stats.cls_matched || {};
  const clsTotal = result?.stats.cls_total || {};
  const totalMatched = result?.stats.matched_excel_tasks || 0;
  const totalExcel = result?.stats.total_excel_tasks || 0;
  const totalL5 = result?.stats.total_l5_nodes || 0;
  const matchedL5 = result?.stats.matched_l5_nodes || 0;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* 헤더 */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100 bg-gray-50">
        <div className="flex items-center gap-2">
          <Link2 className="h-4 w-4 text-gray-500" />
          <span className="text-sm font-bold text-gray-700">AI/Human 분류 ↔ As-Is 노드 연결 확인</span>
          {!hasExcel && <span className="px-2 py-0.5 rounded text-[10px] bg-yellow-100 text-yellow-700">엑셀 없음</span>}
          {!hasAsIs && <span className="px-2 py-0.5 rounded text-[10px] bg-yellow-100 text-yellow-700">As-Is 없음</span>}
        </div>
        <button
          onClick={load}
          disabled={loading || !canCheck}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-gray-300 text-gray-600 hover:bg-white transition disabled:opacity-40"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          {loading ? "분석 중..." : result ? "새로고침" : "연결 확인"}
        </button>
      </div>

      {error && <div className="px-5 py-2 text-xs text-red-600 bg-red-50 border-b border-red-100">{error}</div>}

      {/* 로딩 */}
      {loading && (
        <div className="px-5 py-8 text-center">
          <div className="inline-block h-7 w-7 animate-spin rounded-full border-2 border-gray-200 border-t-red-600 mb-2" />
          <p className="text-sm text-gray-400">엑셀 분류 결과와 As-Is 노드 연결 분석 중...</p>
        </div>
      )}

      {/* 안내 */}
      {!result && !loading && (
        <div className="px-5 py-8 text-center text-gray-400 text-sm">
          {canCheck
            ? <><div className="text-2xl mb-2">🔗</div><p>버튼을 눌러 AI/Human 분류가 각 As-Is 노드에 제대로 연결됐는지 확인하세요.</p></>
            : <><div className="text-2xl mb-2">⚠️</div><p>엑셀 파일과 As-Is 워크플로우를 먼저 업로드하세요.</p></>
          }
        </div>
      )}

      {/* 결과 */}
      {result && !loading && (
        <div className="p-5 space-y-5">

          {/* ① 전체 분류 현황 (엑셀 전체 vs 매핑된 Task) */}
          <div className="grid grid-cols-2 gap-4 p-4 rounded-xl bg-gray-50 border border-gray-200">
            <ClsOverviewBar counts={clsTotal} total={totalExcel} title="전체 엑셀 분류 현황" />
            <ClsOverviewBar counts={clsMatched} total={totalMatched} title="As-Is 노드에 연결된 분류" />
          </div>

          {/* ② 매핑 요약 카드 3개 */}
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-xl border-2 p-3 text-center"
              style={{
                borderColor: result.stats.match_rate >= 80 ? "#86EFAC" : result.stats.match_rate >= 50 ? "#FDE047" : "#FCA5A5",
                backgroundColor: result.stats.match_rate >= 80 ? "#F0FDF4" : result.stats.match_rate >= 50 ? "#FEFCE8" : "#FFF1F2",
              }}>
              <div className="text-2xl font-black" style={{ color: result.stats.match_rate >= 80 ? "#15803D" : result.stats.match_rate >= 50 ? "#A16207" : "#DC2626" }}>
                {result.stats.match_rate}%
              </div>
              <div className="text-[10px] text-gray-500 mt-0.5">연결률 (JSON L5 기준)</div>
            </div>
            <div className="rounded-xl border border-gray-200 p-3 text-center bg-white">
              <div className="text-lg font-bold text-gray-800">
                {matchedL5}
                <span className="text-xs font-normal text-gray-400"> / {totalL5}</span>
              </div>
              <div className="text-[10px] text-gray-500 mt-0.5">JSON L5 노드 연결됨</div>
              {result.stats.unmatched_l5_nodes > 0 && (
                <div className="text-[10px] text-red-500 mt-0.5">미연결 {result.stats.unmatched_l5_nodes}개</div>
              )}
            </div>
            <div className="rounded-xl border border-gray-200 p-3 text-center bg-white">
              <div className="text-lg font-bold text-gray-800">
                {result.stats.matched_l4_nodes}
                <span className="text-xs font-normal text-gray-400"> / {result.stats.total_l4_nodes}</span>
              </div>
              <div className="text-[10px] text-gray-500 mt-0.5">L4 노드 연결됨</div>
              {result.stats.unmatched_l4_nodes > 0 && (
                <div className="text-[10px] text-red-500 mt-0.5">미연결 {result.stats.unmatched_l4_nodes}개</div>
              )}
            </div>
          </div>

          {/* ③ 연결 상태 메시지 */}
          {result.has_excel && result.has_asis && (
            <div className={`flex items-start gap-2 px-4 py-3 rounded-lg text-sm ${
              result.stats.match_rate >= 80 ? "bg-green-50 text-green-700 border border-green-200" :
              result.stats.match_rate >= 40 ? "bg-yellow-50 text-yellow-700 border border-yellow-200" :
              "bg-red-50 text-red-700 border border-red-200"
            }`}>
              {result.stats.match_rate >= 80
                ? <CheckCircle className="h-4 w-4 shrink-0 mt-0.5" />
                : result.stats.match_rate >= 40
                ? <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                : <XCircle className="h-4 w-4 shrink-0 mt-0.5" />
              }
              <div>
                {result.stats.match_rate >= 80
                  ? "AI/Human 분류 결과가 As-Is 노드에 잘 연결되어 있습니다. 벤치마킹·기본 설계에 분류 결과가 반영됩니다."
                  : result.stats.match_rate >= 40
                  ? `부분 연결 — JSON L5 노드 ${result.stats.unmatched_l5_nodes}개가 엑셀 Task와 연결되지 않았습니다. 엑셀 Task ID와 JSON L5 task_id가 일치하는지 확인하세요.`
                  : `연결률이 낮습니다 (${result.stats.match_rate}%). 엑셀 Task ID와 JSON/PPT의 L5 task_id 체계가 다를 수 있습니다. 아래 미연결 목록을 확인하세요.`
                }
              </div>
            </div>
          )}

          {/* ④ L4 노드별 분류 현황 */}
          {result.sheets.length > 0 && (() => {
            const sheetIdx = activeSheetId
              ? Math.max(0, result.sheets.findIndex((s) => s.sheet_id === activeSheetId))
              : 0;
            const activeSheetData = result.sheets[sheetIdx];
            return (
            <div>
              <div className="text-xs font-bold text-gray-600 mb-2">L4 노드별 AI/Human 분류 연결 현황</div>

              {activeSheetData && (
                <div className="space-y-4 max-h-[480px] overflow-y-auto pr-1">
                  {activeSheetData.l3_groups.map((g, gi) => (
                    <div key={gi}>
                      {g.task_id && (
                        <div className="flex items-center gap-2 px-2 py-1.5 mb-1">
                          <span className="text-[10px] font-mono text-gray-400">{g.task_id}</span>
                          <span className="text-xs font-bold text-gray-700">{g.label}</span>
                          <span className="text-[10px] text-gray-400 ml-auto">
                            L4 {g.l4_nodes.length} · L5 {g.total_l5}개 (연결 {g.matched_l5})
                          </span>
                        </div>
                      )}
                      {g.l4_nodes
                        .filter((n) => n.total_l5 > 0)  // phantom L4 (L5 자식 없는 cross-sheet 참조) 숨김
                        .map((n) => (
                        <L4Row
                          key={n.task_id}
                          node={n}
                          excelTasks={excelTasks}
                          onManualMatch={handleManualMatch}
                          onDeleteMatch={handleDeleteMatch}
                        />
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </div>
            );
          })()}

          {/* ⑤ 미연결 엑셀 Task */}
          {result.excel_only.length > 0 && (
            <div>
              <button
                className="flex items-center gap-2 text-xs font-semibold text-red-600 hover:text-red-700 transition"
                onClick={() => setShowExcelOnly((v) => !v)}
              >
                {showExcelOnly ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                <XCircle className="h-3.5 w-3.5" />
                As-Is와 미연결 엑셀 Task ({result.excel_only.length}행) — 이 분류 결과는 설계에 반영 안 됩니다
              </button>
              {showExcelOnly && (
                <div className="mt-2 max-h-[240px] overflow-y-auto rounded-lg border border-red-200">
                  <table className="w-full text-xs">
                    <thead className="sticky top-0 bg-red-50 border-b border-red-200">
                      <tr>
                        <th className="text-left px-3 py-2 font-medium text-red-700">Task ID</th>
                        <th className="text-left px-3 py-2 font-medium text-red-700">Task명</th>
                        <th className="text-left px-3 py-2 font-medium text-red-700">l4_id</th>
                        <th className="text-left px-3 py-2 font-medium text-red-700">L4</th>
                        <th className="text-left px-3 py-2 font-medium text-red-700">분류</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.excel_only.map((t) => (
                        <tr key={t.id} className="border-b border-red-100 hover:bg-red-50/50">
                          <td className="px-3 py-1.5 font-mono text-gray-400">{t.id}</td>
                          <td className="px-3 py-1.5 text-gray-700 max-w-[180px] truncate">{t.name}</td>
                          <td className="px-3 py-1.5 font-mono text-red-500 text-[10px]">{t.l4_id || "—"}</td>
                          <td className="px-3 py-1.5 text-gray-500 max-w-[120px] truncate">{t.l4}</td>
                          <td className="px-3 py-1.5"><LabelBadge label={t.label} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

        </div>
      )}
    </div>
  );
}
