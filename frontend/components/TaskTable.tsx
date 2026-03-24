"use client";

import React, { useState } from "react";
import type { Task, ClassificationResult, LabelType } from "@/lib/api";
import StatusBadge from "./StatusBadge";
import { ChevronDown, ChevronUp, Pencil, Check, X } from "lucide-react";

interface TaskRow extends Task {
  result?: ClassificationResult;
}

interface Props {
  rows: TaskRow[];
  showResult?: boolean;
  onLabelChange?: (taskId: string, label: LabelType, reason: string) => Promise<void>;
  selectable?: boolean;
  selectedIds?: Set<string>;
  onSelectionChange?: (ids: Set<string>) => void;
}

export default function TaskTable({
  rows,
  showResult = false,
  onLabelChange,
  selectable = false,
  selectedIds = new Set(),
  onSelectionChange,
}: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editingId, setEditingId]   = useState<string | null>(null);
  const [editLabel, setEditLabel]   = useState<LabelType>("미분류");
  const [editReason, setEditReason] = useState("");
  const [saving, setSaving]         = useState(false);

  const toggleExpand = (id: string) =>
    setExpandedId((prev) => (prev === id ? null : id));

  const startEdit = (row: TaskRow) => {
    setEditingId(row.id);
    setEditLabel(row.result?.label ?? "미분류");
    setEditReason(row.result?.reason ?? "");
  };

  const cancelEdit = () => setEditingId(null);

  const commitEdit = async (taskId: string) => {
    if (!onLabelChange) return;
    setSaving(true);
    try {
      await onLabelChange(taskId, editLabel, editReason);
      setEditingId(null);
    } finally {
      setSaving(false);
    }
  };

  const toggleSelect = (id: string) => {
    if (!onSelectionChange) return;
    const next = new Set(selectedIds);
    next.has(id) ? next.delete(id) : next.add(id);
    onSelectionChange(next);
  };

  const toggleAll = () => {
    if (!onSelectionChange) return;
    if (selectedIds.size === rows.length) {
      onSelectionChange(new Set());
    } else {
      onSelectionChange(new Set(rows.map((r) => r.id)));
    }
  };

  const labelOptions: LabelType[] = ["AI", "AI + Human", "Human", "미분류"];

  /* ── 공통 헤더 스타일 ── */
  const thBase = "px-3 py-2.5 text-left text-[11px] font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap bg-gray-50";
  const thId   = `${thBase} w-24`;

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200" style={{ fontSize: "13px" }}>
        <thead>
          <tr>
            {selectable && (
              <th className={`${thBase} w-10 px-3`}>
                <input
                  type="checkbox"
                  checked={rows.length > 0 && selectedIds.size === rows.length}
                  onChange={toggleAll}
                  className="h-3.5 w-3.5 rounded border-gray-300"
                  style={{ accentColor: "#A62121" }}
                />
              </th>
            )}
            {/* L3 */}
            <th className={thId}>L3 ID</th>
            <th className={thBase} style={{ minWidth: 140 }}>L3 프로세스</th>
            {/* L4 */}
            <th className={thId}>L4 ID</th>
            <th className={thBase} style={{ minWidth: 160 }}>L4 활동</th>
            {/* L5 */}
            <th className={thId}>L5 ID</th>
            <th className={thBase} style={{ minWidth: 180 }}>L5 Task명</th>

            {showResult && (
              <>
                <th className={`${thBase} w-32`}>분류 결과</th>
                <th className={thBase} style={{ minWidth: 160 }}>분류 근거</th>
                {onLabelChange && <th className={`${thBase} w-10`} />}
              </>
            )}
            {/* 펼치기 */}
            <th className={`${thBase} w-8 px-2`} />
          </tr>
        </thead>

        <tbody className="divide-y divide-gray-100 bg-white">
          {rows.map((row, rowIdx) => (
            <React.Fragment key={`${row.id}_${rowIdx}`}>
              <tr
                className={`transition-colors ${selectable ? "cursor-pointer" : "hover:bg-gray-50"}`}
                style={selectedIds.has(row.id) ? { backgroundColor: "#FFF5F7" } : undefined}
                onClick={selectable ? () => toggleSelect(row.id) : undefined}
              >
                {/* 체크박스 */}
                {selectable && (
                  <td className="px-3 py-2.5" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedIds.has(row.id)}
                      onChange={() => toggleSelect(row.id)}
                      className="h-3.5 w-3.5 rounded border-gray-300"
                      style={{ accentColor: "#A62121" }}
                    />
                  </td>
                )}

                {/* L3 ID */}
                <td className="px-3 py-2.5 font-mono text-[11px] text-gray-400 whitespace-nowrap">{row.l3_id}</td>
                {/* L3 프로세스 */}
                <td className="px-3 py-2.5 text-gray-600" style={{ maxWidth: 180 }}>
                  <span className="line-clamp-1">{row.l3}</span>
                </td>

                {/* L4 ID */}
                <td className="px-3 py-2.5 font-mono text-[11px] text-gray-400 whitespace-nowrap">{row.l4_id}</td>
                {/* L4 활동 */}
                <td className="px-3 py-2.5 text-gray-600" style={{ maxWidth: 200 }}>
                  <span className="line-clamp-1">{row.l4}</span>
                </td>

                {/* L5 ID */}
                <td className="px-3 py-2.5 font-mono text-[11px] text-gray-400 whitespace-nowrap">{row.id}</td>
                {/* L5 Task명 */}
                <td className="px-3 py-2.5 font-medium text-gray-900" style={{ maxWidth: 220 }}>
                  <span className="line-clamp-1">{row.name}</span>
                </td>

                {/* 결과 영역 */}
                {showResult && editingId === row.id ? (
                  <>
                    <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                      <select
                        value={editLabel}
                        onChange={(e) => setEditLabel(e.target.value as LabelType)}
                        className="w-full rounded border border-gray-300 px-2 py-1 text-xs focus:outline-none"
                        onFocus={(e) => (e.currentTarget.style.borderColor = "#A62121")}
                        onBlur={(e) => (e.currentTarget.style.borderColor = "")}
                      >
                        {labelOptions.map((l) => (
                          <option key={l} value={l}>{l}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="text"
                        value={editReason}
                        onChange={(e) => setEditReason(e.target.value)}
                        placeholder="분류 근거 입력"
                        className="w-full rounded border border-gray-300 px-2 py-1 text-xs focus:outline-none"
                        onFocus={(e) => (e.currentTarget.style.borderColor = "#A62121")}
                        onBlur={(e) => (e.currentTarget.style.borderColor = "")}
                      />
                    </td>
                    <td className="px-2 py-2" onClick={(e) => e.stopPropagation()}>
                      <div className="flex gap-1">
                        <button
                          onClick={() => commitEdit(row.id)}
                          disabled={saving}
                          className="rounded p-1 text-emerald-600 hover:bg-emerald-50"
                        >
                          <Check className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={cancelEdit}
                          className="rounded p-1 text-gray-400 hover:bg-gray-100"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  </>
                ) : showResult ? (
                  <>
                    <td className="px-3 py-2.5">
                      <StatusBadge label={row.result?.label ?? "미분류"} size="sm" />
                    </td>
                    <td className="px-3 py-2.5" style={{ maxWidth: 200 }}>
                      {row.result?.criterion && (
                        <span
                          className="mb-0.5 block text-[11px] font-medium"
                          style={{ color: "#A62121" }}
                        >
                          [{row.result.criterion}]
                        </span>
                      )}
                      <span className="text-xs text-gray-500 line-clamp-2">
                        {row.result?.reason ?? "—"}
                      </span>
                    </td>
                    {onLabelChange && (
                      <td className="px-2 py-2.5" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => startEdit(row)}
                          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    )}
                  </>
                ) : null}

                {/* 펼치기 버튼 */}
                <td className="px-2 py-2.5">
                  <button
                    onClick={(e) => { e.stopPropagation(); toggleExpand(row.id); }}
                    className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                  >
                    {expandedId === row.id
                      ? <ChevronUp className="h-3.5 w-3.5" />
                      : <ChevronDown className="h-3.5 w-3.5" />}
                  </button>
                </td>
              </tr>

              {/* 펼침 패널 */}
              {expandedId === row.id && (
                <tr className="bg-gray-50/70">
                  <td colSpan={99} className="px-6 py-4">
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                      {/* 계층 */}
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400 mb-1">계층 구조</p>
                        <p className="text-sm text-gray-700">{row.l2} › {row.l3} › {row.l4}</p>
                      </div>

                      {/* Task 설명 */}
                      {row.description && (
                        <div>
                          <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400 mb-1">Task 설명</p>
                          <p className="text-sm text-gray-700 whitespace-pre-wrap">{row.description}</p>
                        </div>
                      )}

                      {/* 수행주체 */}
                      {row.performer && (
                        <div className="col-span-full">
                          <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400 mb-1">수행주체</p>
                          <p className="text-sm text-gray-700 whitespace-pre-wrap">{row.performer}</p>
                        </div>
                      )}

                      {/* 3단계 Knock-out 분석 */}
                      {showResult && row.result && (
                        <div className="col-span-full">
                          <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400 mb-2">3단계 Knock-out 분석</p>
                          <div className="flex flex-col gap-1.5">
                            {(() => {
                              const stages = [
                                { label: "1단계: 규제 측면",      stage: row.result!.stage1 },
                                { label: "2단계: 확정/승인 업무", stage: row.result!.stage2 },
                                { label: "3단계: 상호작용 업무",  stage: row.result!.stage3 },
                              ];
                              // 첫 번째로 실패한 단계 인덱스 (없으면 -1)
                              const firstFailIdx = stages.findIndex((s) => s.stage && !s.stage.passed);

                              return stages.map(({ label, stage }, idx) => {
                                // 이전 단계에서 이미 X가 난 경우 → 건너뜀(회색)
                                const isSkipped = firstFailIdx !== -1 && idx > firstFailIdx;

                                if (isSkipped) {
                                  return (
                                    <div
                                      key={label}
                                      className="flex items-start gap-2 rounded-md px-3 py-2"
                                      style={{ backgroundColor: "#F9FAFB", border: "1px solid #E5E7EB" }}
                                    >
                                      <span className="mt-px text-sm font-bold flex-shrink-0 text-gray-300">—</span>
                                      <div>
                                        <span className="text-xs font-semibold text-gray-300">{label}</span>
                                        <p className="mt-0.5 text-xs text-gray-300">이전 단계 해당으로 건너뜀</p>
                                      </div>
                                    </div>
                                  );
                                }

                                return (
                                  <div
                                    key={label}
                                    className="flex items-start gap-2 rounded-md px-3 py-2"
                                    style={{
                                      backgroundColor: stage?.passed ? "#f0fdf4" : "#FFF5F7",
                                      border: `1px solid ${stage?.passed ? "#bbf7d0" : "#F2DCE0"}`,
                                    }}
                                  >
                                    <span
                                      className="mt-px text-sm font-bold flex-shrink-0"
                                      style={{ color: stage?.passed ? "#16a34a" : "#A62121" }}
                                    >
                                      {stage?.passed ? "✓" : "✗"}
                                    </span>
                                    <div>
                                      <span className="text-xs font-semibold" style={{ color: stage?.passed ? "#15803d" : "#A62121" }}>
                                        {label}
                                      </span>
                                      {stage?.note && (
                                        <p className="mt-0.5 text-xs text-gray-600">{stage.note}</p>
                                      )}
                                    </div>
                                  </div>
                                );
                              });
                            })()}
                          </div>
                        </div>
                      )}

                      {/* AI + Human 역할 분담 */}
                      {showResult && row.result?.hybrid_check && row.result.hybrid_note && (
                        <div className="col-span-full">
                          <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-600 mb-1">AI + Human 역할 분담</p>
                          <div
                            className="rounded-md px-3 py-2 text-xs text-amber-900"
                            style={{ background: "#FFFBEB", border: "1px solid #FCD34D" }}
                          >
                            {row.result.hybrid_note}
                          </div>
                        </div>
                      )}

                      {/* Input / Output 유형 */}
                      {showResult && row.result && (row.result.input_types || row.result.output_types) && (
                        <div className="col-span-full flex flex-wrap gap-4">
                          {row.result.input_types && (
                            <div>
                              <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400 mb-1">Input 유형</p>
                              <p className="text-xs text-gray-700">{row.result.input_types}</p>
                            </div>
                          )}
                          {row.result.output_types && (
                            <div>
                              <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400 mb-1">Output 유형</p>
                              <p className="text-xs text-gray-700">{row.result.output_types}</p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>

      {rows.length === 0 && (
        <div className="py-14 text-center text-sm text-gray-400">
          표시할 항목이 없습니다.
        </div>
      )}
    </div>
  );
}
