"use client";

import { useState, useCallback } from "react";
import { getMappingCheck, type MappingCheckResult, type MappingL4Node } from "@/lib/api";
import { RefreshCw, ChevronDown, ChevronRight, CheckCircle, XCircle, AlertCircle, Link2 } from "lucide-react";

const LABEL_STYLE: Record<string, { bg: string; text: string }> = {
  "AI":         { bg: "#DCFCE7", text: "#15803D" },
  "AI + Human": { bg: "#FEF9C3", text: "#A16207" },
  "Human":      { bg: "#FEE2E2", text: "#DC2626" },
  "미분류":     { bg: "#F3F4F6", text: "#6B7280" },
};

function labelBadge(label: string) {
  const s = LABEL_STYLE[label] || LABEL_STYLE["미분류"];
  return (
    <span className="px-1.5 py-0.5 rounded text-[9px] font-bold" style={{ backgroundColor: s.bg, color: s.text }}>
      {label}
    </span>
  );
}

function PainBadge({ points }: { points: string[] }) {
  if (!points.length) return null;
  return (
    <span className="ml-1 px-1.5 py-0.5 rounded text-[9px] bg-orange-50 text-orange-600 border border-orange-200">
      ⚡ {points[0]}{points.length > 1 ? ` +${points.length - 1}` : ""}
    </span>
  );
}

// L4 노드 한 개 행 (접기/펼치기)
function L4Row({ node }: { node: MappingL4Node }) {
  const [open, setOpen] = useState(false);
  const hasExcel = node.excel_tasks.length > 0;

  return (
    <div className={`border rounded-lg mb-1 transition-colors ${hasExcel ? "border-green-200 bg-green-50/30" : "border-red-200 bg-red-50/20"}`}>
      {/* L4 헤더 */}
      <button
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-white/60 transition-colors rounded-lg"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <ChevronDown className="h-3.5 w-3.5 text-gray-400 shrink-0" /> : <ChevronRight className="h-3.5 w-3.5 text-gray-400 shrink-0" />}

        {/* 매핑 상태 아이콘 */}
        {hasExcel
          ? <CheckCircle className="h-3.5 w-3.5 text-green-500 shrink-0" />
          : <XCircle className="h-3.5 w-3.5 text-red-400 shrink-0" />
        }

        <span className="font-mono text-[10px] text-gray-400 shrink-0">{node.task_id}</span>
        <span className="text-xs font-medium text-gray-700 flex-1 truncate">{node.label}</span>

        {/* 엑셀 Task 개수 */}
        <span className={`shrink-0 px-2 py-0.5 rounded-full text-[10px] font-bold ${
          hasExcel ? "bg-green-100 text-green-700" : "bg-red-100 text-red-500"
        }`}>
          엑셀 {node.excel_tasks.length}행
        </span>

        {/* L5 개수 */}
        {node.l5_nodes.length > 0 && (
          <span className="shrink-0 px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-600">
            L5 {node.l5_nodes.length}
          </span>
        )}
      </button>

      {/* 펼쳤을 때: 엑셀 Task 목록 + L5 노드 목록 */}
      {open && (
        <div className="px-3 pb-3 space-y-2">
          {/* 엑셀 Task 목록 */}
          {hasExcel ? (
            <div className="space-y-1">
              <div className="text-[10px] font-semibold text-gray-500 mb-1 flex items-center gap-1">
                <Link2 className="h-3 w-3" /> 매핑된 엑셀 Task ({node.excel_tasks.length}행)
              </div>
              {node.excel_tasks.map((t) => (
                <div key={t.id} className="bg-white rounded border border-green-100 px-2.5 py-1.5 flex items-start gap-2">
                  <span className="font-mono text-[9px] text-gray-400 shrink-0 mt-0.5">{t.id}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs text-gray-800 font-medium truncate">{t.name}</div>
                    {t.description && (
                      <div className="text-[10px] text-gray-400 truncate mt-0.5">{t.description}</div>
                    )}
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {labelBadge(t.label)}
                    <PainBadge points={t.pain_points} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-[11px] text-red-500 bg-red-50 rounded px-2.5 py-1.5">
              <XCircle className="h-3.5 w-3.5 shrink-0" />
              이 L4 노드(task_id: <span className="font-mono">{node.task_id}</span>)와 일치하는 엑셀 행이 없습니다.
            </div>
          )}

          {/* L5 노드 목록 */}
          {node.l5_nodes.length > 0 && (
            <div>
              <div className="text-[10px] font-semibold text-blue-600 mb-1">L5 하위 노드</div>
              <div className="space-y-0.5">
                {node.l5_nodes.map((n) => (
                  <div key={n.task_id} className="flex items-center gap-2 text-[10px] text-gray-600 bg-blue-50/50 rounded px-2 py-1">
                    <span className="font-mono text-gray-400">{n.task_id}</span>
                    <span>{n.label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface MappingCheckPanelProps {
  hasExcel: boolean;
  hasAsIs: boolean;
}

export default function MappingCheckPanel({ hasExcel, hasAsIs }: MappingCheckPanelProps) {
  const [result, setResult] = useState<MappingCheckResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeSheet, setActiveSheet] = useState(0);
  const [showExcelOnly, setShowExcelOnly] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await getMappingCheck();
      setResult(r);
      setActiveSheet(0);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  const canCheck = hasExcel || hasAsIs;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* 헤더 */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100 bg-gray-50">
        <div className="flex items-center gap-2">
          <Link2 className="h-4 w-4 text-gray-500" />
          <span className="text-sm font-bold text-gray-700">엑셀 ↔ As-Is 노드 매핑 확인</span>
          {!hasExcel && (
            <span className="px-2 py-0.5 rounded text-[10px] bg-yellow-100 text-yellow-700">엑셀 없음</span>
          )}
          {!hasAsIs && (
            <span className="px-2 py-0.5 rounded text-[10px] bg-yellow-100 text-yellow-700">As-Is 없음</span>
          )}
        </div>
        <button
          onClick={load}
          disabled={loading || !canCheck}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-gray-300 text-gray-600 hover:bg-white transition disabled:opacity-40"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          {result ? "새로고침" : "매핑 확인"}
        </button>
      </div>

      {/* 오류 */}
      {error && (
        <div className="px-5 py-2 text-xs text-red-600 bg-red-50 border-b border-red-100">{error}</div>
      )}

      {/* 안내 (미실행) */}
      {!result && !loading && (
        <div className="px-5 py-8 text-center text-gray-400 text-sm">
          {canCheck
            ? <><div className="text-2xl mb-2">🔗</div><p>버튼을 눌러 엑셀과 As-Is JSON의 매핑 상태를 확인하세요.</p></>
            : <><div className="text-2xl mb-2">⚠️</div><p>엑셀 파일과 As-Is 워크플로우를 먼저 업로드하세요.</p></>
          }
        </div>
      )}

      {/* 로딩 */}
      {loading && (
        <div className="px-5 py-8 text-center">
          <div className="inline-block h-7 w-7 animate-spin rounded-full border-3 border-gray-200 border-t-red-600 mb-2" />
          <p className="text-sm text-gray-400">매핑 분석 중...</p>
        </div>
      )}

      {/* 결과 */}
      {result && !loading && (
        <div className="p-5 space-y-4">
          {/* 통계 카드 */}
          <div className="grid grid-cols-3 gap-3">
            {/* 매핑률 */}
            <div className="rounded-xl border-2 p-3 text-center"
              style={{ borderColor: result.stats.match_rate >= 80 ? "#86EFAC" : result.stats.match_rate >= 50 ? "#FDE047" : "#FCA5A5",
                       backgroundColor: result.stats.match_rate >= 80 ? "#F0FDF4" : result.stats.match_rate >= 50 ? "#FEFCE8" : "#FFF1F2" }}>
              <div className="text-2xl font-black" style={{ color: result.stats.match_rate >= 80 ? "#15803D" : result.stats.match_rate >= 50 ? "#A16207" : "#DC2626" }}>
                {result.stats.match_rate}%
              </div>
              <div className="text-[10px] text-gray-500 mt-0.5">엑셀 매핑률</div>
            </div>

            {/* 엑셀 */}
            <div className="rounded-xl border border-gray-200 p-3 text-center bg-white">
              <div className="text-lg font-bold text-gray-800">
                {result.stats.matched_excel_tasks}
                <span className="text-xs font-normal text-gray-400"> / {result.stats.total_excel_tasks}</span>
              </div>
              <div className="text-[10px] text-gray-500 mt-0.5">엑셀 Task 매핑됨</div>
              {result.stats.unmatched_excel_tasks > 0 && (
                <div className="text-[10px] text-red-500 mt-0.5">미매핑 {result.stats.unmatched_excel_tasks}행</div>
              )}
            </div>

            {/* L4 노드 */}
            <div className="rounded-xl border border-gray-200 p-3 text-center bg-white">
              <div className="text-lg font-bold text-gray-800">
                {result.stats.matched_l4_nodes}
                <span className="text-xs font-normal text-gray-400"> / {result.stats.total_l4_nodes}</span>
              </div>
              <div className="text-[10px] text-gray-500 mt-0.5">L4 노드 매핑됨</div>
              {result.stats.unmatched_l4_nodes > 0 && (
                <div className="text-[10px] text-red-500 mt-0.5">미매핑 {result.stats.unmatched_l4_nodes}개</div>
              )}
            </div>
          </div>

          {/* 매핑 상태 요약 메시지 */}
          {result.has_excel && result.has_asis && (
            <div className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm ${
              result.stats.match_rate >= 80 ? "bg-green-50 text-green-700 border border-green-200" :
              result.stats.match_rate >= 40 ? "bg-yellow-50 text-yellow-700 border border-yellow-200" :
              "bg-red-50 text-red-700 border border-red-200"
            }`}>
              {result.stats.match_rate >= 80
                ? <><CheckCircle className="h-4 w-4 shrink-0" /> 매핑 상태 양호 — 대부분의 엑셀 Task가 As-Is 노드와 연결됩니다.</>
                : result.stats.match_rate >= 40
                ? <><AlertCircle className="h-4 w-4 shrink-0" /> 부분 매핑 — L4 task_id와 엑셀 l4_id가 일치하지 않는 항목이 있습니다.</>
                : <><XCircle className="h-4 w-4 shrink-0" /> 매핑률 낮음 — 엑셀 l4_id와 JSON task_id가 다를 수 있습니다. 아래에서 확인하세요.</>
              }
            </div>
          )}

          {/* 엑셀만 있는 경우 */}
          {result.has_excel && !result.has_asis && (
            <div className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm bg-yellow-50 text-yellow-700 border border-yellow-200">
              <AlertCircle className="h-4 w-4 shrink-0" />
              As-Is 워크플로우가 없어 매핑을 확인할 수 없습니다. As-Is JSON/PPT를 업로드하세요.
            </div>
          )}

          {/* 시트 탭 */}
          {result.sheets.length > 0 && (
            <>
              {result.sheets.length > 1 && (
                <div className="flex gap-1 border-b border-gray-200">
                  {result.sheets.map((s, i) => (
                    <button
                      key={s.sheet_id}
                      onClick={() => setActiveSheet(i)}
                      className={`px-4 py-1.5 text-xs font-medium border-b-2 transition ${
                        activeSheet === i ? "border-red-600 text-red-700" : "border-transparent text-gray-500 hover:text-gray-700"
                      }`}
                    >
                      {s.sheet_name}
                      <span className="ml-1 text-gray-400">L4 {s.l4_count}</span>
                    </button>
                  ))}
                </div>
              )}

              {/* L3 → L4 트리 */}
              {result.sheets[activeSheet] && (
                <div className="space-y-3 max-h-[440px] overflow-y-auto pr-1">
                  {result.sheets[activeSheet].l3_groups.map((g, gi) => (
                    <div key={gi}>
                      {/* L3 그룹 헤더 */}
                      {g.task_id && (
                        <div className="flex items-center gap-2 px-2 py-1.5 mb-1">
                          <span className="text-[10px] font-mono text-gray-400">{g.task_id}</span>
                          <span className="text-xs font-bold text-gray-700">{g.label}</span>
                          <span className="text-[10px] text-gray-400 ml-auto">
                            L4 {g.l4_nodes.length}개 · 엑셀 {g.total_excel}행
                          </span>
                        </div>
                      )}
                      {/* L4 노드 */}
                      <div className="space-y-1">
                        {g.l4_nodes.map((n) => (
                          <L4Row key={n.task_id} node={n} />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* 미매핑 엑셀 Task */}
          {result.excel_only.length > 0 && (
            <div>
              <button
                className="flex items-center gap-2 text-xs font-semibold text-red-600 hover:text-red-700 transition"
                onClick={() => setShowExcelOnly((v) => !v)}
              >
                {showExcelOnly ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                <XCircle className="h-3.5 w-3.5" />
                As-Is와 매핑 안 된 엑셀 Task ({result.excel_only.length}행)
              </button>

              {showExcelOnly && (
                <div className="mt-2 max-h-[260px] overflow-y-auto rounded-lg border border-red-200">
                  <table className="w-full text-xs">
                    <thead className="sticky top-0 bg-red-50 border-b border-red-200">
                      <tr>
                        <th className="text-left px-3 py-2 font-medium text-red-700">Task ID</th>
                        <th className="text-left px-3 py-2 font-medium text-red-700">Task명</th>
                        <th className="text-left px-3 py-2 font-medium text-red-700">L4 ID</th>
                        <th className="text-left px-3 py-2 font-medium text-red-700">L4</th>
                        <th className="text-left px-3 py-2 font-medium text-red-700">L3</th>
                        <th className="text-left px-3 py-2 font-medium text-red-700">분류</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.excel_only.map((t) => (
                        <tr key={t.id} className="border-b border-red-100 hover:bg-red-50/50">
                          <td className="px-3 py-1.5 font-mono text-gray-400">{t.id}</td>
                          <td className="px-3 py-1.5 text-gray-700 max-w-[180px] truncate">{t.name}</td>
                          <td className="px-3 py-1.5 font-mono text-red-500">{t.l4_id || "-"}</td>
                          <td className="px-3 py-1.5 text-gray-500 max-w-[120px] truncate">{t.l4}</td>
                          <td className="px-3 py-1.5 text-gray-400 max-w-[100px] truncate">{t.l3}</td>
                          <td className="px-3 py-1.5">{labelBadge(t.label)}</td>
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
