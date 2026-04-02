"use client";

import { useState, useCallback, useEffect } from "react";
import { getMappingCheck, type MappingCheckResult, type MappingL4Node } from "@/lib/api";
import { RefreshCw, ChevronDown, ChevronRight, CheckCircle, XCircle, AlertCircle, Link2 } from "lucide-react";

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
function L4Row({ node }: { node: MappingL4Node }) {
  const [open, setOpen] = useState(false);
  const hasExcel = node.excel_tasks.length > 0;
  const total = node.excel_tasks.length;
  const cls = node.cls_summary || {};

  return (
    <div className={`border rounded-lg mb-1 ${hasExcel ? "border-green-200 bg-green-50/30" : "border-red-200 bg-red-50/20"}`}>
      <button
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-white/60 transition-colors rounded-lg"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <ChevronDown className="h-3.5 w-3.5 text-gray-400 shrink-0" /> : <ChevronRight className="h-3.5 w-3.5 text-gray-400 shrink-0" />}
        {hasExcel
          ? <CheckCircle className="h-3.5 w-3.5 text-green-500 shrink-0" />
          : <XCircle className="h-3.5 w-3.5 text-red-400 shrink-0" />}
        <span className="font-mono text-[10px] text-gray-400 shrink-0">{node.task_id}</span>
        <span className="text-xs font-medium text-gray-700 flex-1 truncate">{node.label}</span>

        {hasExcel ? (
          <div className="flex items-center gap-2 shrink-0">
            <ClsSummaryBar counts={cls} total={total} />
            <span className="text-[10px] text-green-600 font-bold">{total}행</span>
          </div>
        ) : (
          <span className="shrink-0 text-[10px] text-red-400 font-medium">미연결</span>
        )}
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-1.5">
          {hasExcel ? (
            <>
              <div className="text-[10px] font-semibold text-gray-500 mb-1 flex items-center gap-1">
                <Link2 className="h-3 w-3" /> 연결된 엑셀 Task ({total}행)
              </div>
              {node.excel_tasks.map((t) => (
                <div key={t.id} className="bg-white rounded border border-green-100 px-2.5 py-1.5 flex items-start gap-2">
                  <span className="font-mono text-[9px] text-gray-400 shrink-0 mt-0.5 w-16 truncate">{t.id}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs text-gray-800 font-medium">{t.name}</div>
                    {t.description && (
                      <div className="text-[10px] text-gray-400 mt-0.5 line-clamp-1">{t.description}</div>
                    )}
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <LabelBadge label={t.label} />
                    <PainBadge points={t.pain_points} />
                  </div>
                </div>
              ))}
            </>
          ) : (
            <div className="flex items-center gap-1.5 text-[11px] text-red-500 bg-red-50 rounded px-2.5 py-1.5">
              <XCircle className="h-3.5 w-3.5 shrink-0" />
              <span>task_id <span className="font-mono">{node.task_id}</span>와 일치하는 엑셀 l4_id가 없습니다.</span>
            </div>
          )}
          {node.l5_nodes.length > 0 && (
            <div className="mt-1">
              <div className="text-[10px] font-semibold text-blue-600 mb-0.5">L5 하위 노드</div>
              {node.l5_nodes.map((n) => (
                <div key={n.task_id} className="flex items-center gap-2 text-[10px] text-gray-500 px-1">
                  <span className="font-mono text-gray-400">{n.task_id}</span>
                  <span>{n.label}</span>
                </div>
              ))}
            </div>
          )}
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
              <div className="text-[10px] text-gray-500 mt-0.5">연결률</div>
            </div>
            <div className="rounded-xl border border-gray-200 p-3 text-center bg-white">
              <div className="text-lg font-bold text-gray-800">
                {result.stats.matched_excel_tasks}
                <span className="text-xs font-normal text-gray-400"> / {result.stats.total_excel_tasks}</span>
              </div>
              <div className="text-[10px] text-gray-500 mt-0.5">엑셀 Task 연결됨</div>
              {result.stats.unmatched_excel_tasks > 0 && (
                <div className="text-[10px] text-red-500 mt-0.5">미연결 {result.stats.unmatched_excel_tasks}행</div>
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
                  ? `부분 연결 — ${result.stats.unmatched_excel_tasks}개 Task가 As-Is 노드와 연결되지 않았습니다. 엑셀 l4_id와 JSON task_id가 일치하는지 확인하세요.`
                  : `연결률이 낮습니다 (${result.stats.match_rate}%). 엑셀과 JSON/PPT의 L4 ID 체계가 다를 수 있습니다. 아래 미연결 목록을 확인하세요.`
                }
              </div>
            </div>
          )}

          {/* ④ L4 노드별 분류 현황 (시트 탭) */}
          {result.sheets.length > 0 && (
            <div>
              <div className="text-xs font-bold text-gray-600 mb-2">L4 노드별 AI/Human 분류 연결 현황</div>
              {result.sheets.length > 1 && (
                <div className="flex gap-1 border-b border-gray-200 mb-3">
                  {result.sheets.map((s, i) => (
                    <button key={s.sheet_id} onClick={() => setActiveSheet(i)}
                      className={`px-4 py-1.5 text-xs font-medium border-b-2 transition ${
                        activeSheet === i ? "border-red-600 text-red-700" : "border-transparent text-gray-500 hover:text-gray-700"
                      }`}>
                      {s.sheet_name} <span className="text-gray-400">L4 {s.l4_count}</span>
                    </button>
                  ))}
                </div>
              )}

              {result.sheets[activeSheet] && (
                <div className="space-y-4 max-h-[480px] overflow-y-auto pr-1">
                  {result.sheets[activeSheet].l3_groups.map((g, gi) => (
                    <div key={gi}>
                      {g.task_id && (
                        <div className="flex items-center gap-2 px-2 py-1.5 mb-1">
                          <span className="text-[10px] font-mono text-gray-400">{g.task_id}</span>
                          <span className="text-xs font-bold text-gray-700">{g.label}</span>
                          <span className="text-[10px] text-gray-400 ml-auto">
                            L4 {g.l4_nodes.length} · 엑셀 {g.total_excel}행
                          </span>
                        </div>
                      )}
                      {g.l4_nodes.map((n) => <L4Row key={n.task_id} node={n} />)}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

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
