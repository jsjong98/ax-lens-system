"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { X, Download, RefreshCw } from "lucide-react";
import {
  fetchToBeWorkflowJson,
  downloadToBeWorkflowJson,
  type HrWorkflowJson,
  type HrWorkflowSheet,
} from "@/lib/api";

// ── 자동화 레벨 색상 ──────────────────────────────────────────────────────
const AUTOMATION_COLOR: Record<string, { bg: string; text: string; border: string }> = {
  "Full-Auto":         { bg: "#DCFCE7", text: "#15803D", border: "#86EFAC" },
  "Human-in-Loop":     { bg: "#FEF9C3", text: "#A16207", border: "#FDE047" },
  "Human-on-the-Loop": { bg: "#DBEAFE", text: "#1D4ED8", border: "#93C5FD" },
  "Human-Supervised":  { bg: "#FEE2E2", text: "#DC2626", border: "#FCA5A5" },
};

function getAutomationStyle(level?: string) {
  if (!level) return { bg: "#F9FAFB", text: "#374151", border: "#D1D5DB" };
  for (const key of Object.keys(AUTOMATION_COLOR)) {
    if (level.includes(key.replace("-", " ").split(" ")[0])) return AUTOMATION_COLOR[key];
  }
  return { bg: "#F9FAFB", text: "#374151", border: "#D1D5DB" };
}

function shortLevel(level?: string): string {
  if (!level) return "-";
  if (level.includes("Full")) return "Full-Auto";
  if (level.includes("in-Loop") || level.includes("in Loop")) return "HiL";
  if (level.includes("on-the") || level.includes("on the")) return "HotL";
  if (level.includes("Supervised")) return "HSup";
  return level;
}

// ── L5 커스텀 노드 ─────────────────────────────────────────────────────────
type L5NodeData = {
  label: string;
  id: string;
  description?: string;
  automationLevel?: string;
  aiTechnique?: string;
  role?: string;
  inputs?: Record<string, boolean>;
  outputs?: Record<string, boolean>;
  [key: string]: unknown;
};

function L5NodeComponent({ data }: NodeProps) {
  const d = data as L5NodeData;
  const style = getAutomationStyle(d.automationLevel);
  const inputKeys = d.inputs ? Object.keys(d.inputs).filter((k) => d.inputs![k]) : [];
  const outputKeys = d.outputs ? Object.keys(d.outputs).filter((k) => d.outputs![k]) : [];

  return (
    <div
      className="rounded-xl shadow-md text-[11px] leading-tight"
      style={{
        width: 220,
        backgroundColor: style.bg,
        border: `2px solid ${style.border}`,
        color: style.text,
        padding: "10px 12px",
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: style.border }} />

      {/* 헤더 */}
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <span className="font-bold text-[12px] leading-snug flex-1">{d.label}</span>
        <span
          className="shrink-0 px-1.5 py-0.5 rounded text-[9px] font-bold whitespace-nowrap"
          style={{ backgroundColor: style.border, color: style.text }}
        >
          {shortLevel(d.automationLevel)}
        </span>
      </div>

      {/* task_id */}
      <div className="font-mono text-[9px] text-gray-400 mb-1">{d.id}</div>

      {/* AI 기법 */}
      {d.aiTechnique && (
        <div className="mb-1 px-1.5 py-0.5 rounded bg-white/60 text-[10px] font-medium text-purple-700 border border-purple-200">
          {d.aiTechnique}
        </div>
      )}

      {/* description (AI/Human 역할) */}
      {d.description && (
        <div className="text-[10px] text-gray-600 mt-1 whitespace-pre-line leading-snug">
          {d.description}
        </div>
      )}

      {/* 인풋/아웃풋 */}
      {inputKeys.length > 0 && (
        <div className="mt-1.5 text-[9px] text-gray-500">
          <span className="font-semibold text-gray-600">IN: </span>
          {inputKeys.slice(0, 2).join(", ")}
          {inputKeys.length > 2 && ` +${inputKeys.length - 2}`}
        </div>
      )}
      {outputKeys.length > 0 && (
        <div className="mt-0.5 text-[9px] text-gray-500">
          <span className="font-semibold text-gray-600">OUT: </span>
          {outputKeys.slice(0, 2).join(", ")}
          {outputKeys.length > 2 && ` +${outputKeys.length - 2}`}
        </div>
      )}

      <Handle type="source" position={Position.Right} style={{ background: style.border }} />
    </div>
  );
}

const NODE_TYPES: NodeTypes = { l5: L5NodeComponent };

// ── 스윔레인 배경 ─────────────────────────────────────────────────────────
const LANE_H = 220;
const LANE_COLORS = [
  "#EFF6FF", "#F0FDF4", "#FFF7ED", "#F5F3FF",
  "#FFF1F2", "#ECFEFF", "#F0FDFA", "#FEFCE8",
];

function SwimLaneBackground({ lanes }: { lanes: string[] }) {
  return (
    <div className="absolute inset-0 pointer-events-none" style={{ zIndex: 0 }}>
      {lanes.map((lane, i) => (
        <div
          key={i}
          className="absolute left-0 right-0 border-b border-gray-200"
          style={{ top: i * LANE_H, height: LANE_H, backgroundColor: LANE_COLORS[i % LANE_COLORS.length] }}
        >
          <div
            className="absolute left-0 top-0 bottom-0 flex items-center justify-center text-xs font-semibold text-gray-500 border-r border-gray-200"
            style={{ width: 100, writingMode: "vertical-lr", transform: "rotate(180deg)" }}
          >
            {lane}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── React Flow 캔버스 (Provider 안에서 훅 사용) ────────────────────────────
interface FlowCanvasProps {
  sheet: HrWorkflowSheet;
}

function FlowCanvas({ sheet }: FlowCanvasProps) {
  const xOffset = 110;

  const rfNodes: Node[] = sheet.nodes.map((n) => ({
    id: n.id,
    type: n.type || "l5",
    position: { x: n.position.x + xOffset, y: n.position.y },
    data: n.data as Record<string, unknown>,
  }));

  const rfEdges: Edge[] = sheet.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    type: "smoothstep",
    animated: e.animated ?? false,
    label: e.label ?? undefined,
    style: e.style as import("react").CSSProperties | undefined,
    markerEnd: e.markerEnd as Edge["markerEnd"],
  }));

  return (
    <ReactFlow
      nodes={rfNodes}
      edges={rfEdges}
      nodeTypes={NODE_TYPES}
      fitView
      fitViewOptions={{ padding: 0.15 }}
      minZoom={0.2}
      maxZoom={2}
      proOptions={{ hideAttribution: true }}
    >
      <SwimLaneBackground lanes={sheet.lanes} />
      <Background gap={20} color="#e5e7eb" />
      <Controls />
      <MiniMap
        nodeColor={(n) => {
          const d = n.data as { automationLevel?: string };
          return getAutomationStyle(d.automationLevel).bg;
        }}
        maskColor="rgba(255,255,255,0.6)"
      />
    </ReactFlow>
  );
}

// ── 메인 모달 ─────────────────────────────────────────────────────────────
interface ToBeWorkflowModalProps {
  open: boolean;
  onClose: () => void;
}

export default function ToBeWorkflowModal({ open, onClose }: ToBeWorkflowModalProps) {
  const [wfJson, setWfJson] = useState<HrWorkflowJson | null>(null);
  const [activeSheetIdx, setActiveSheetIdx] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadJson = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const json = await fetchToBeWorkflowJson();
      setWfJson(json);
      setActiveSheetIdx(0);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open && !wfJson) {
      loadJson();
    }
  }, [open, wfJson, loadJson]);

  if (!open) return null;

  const sheet = wfJson?.sheets[activeSheetIdx];

  return (
    <div className="fixed inset-0 z-[200] flex flex-col bg-white">
      {/* 헤더 */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-gray-200 bg-white shadow-sm shrink-0">
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold"
            style={{ backgroundColor: "#A62121" }}
          >
            W
          </div>
          <div>
            <div className="font-bold text-gray-800">AI 기반 Workflow 기본 설계</div>
            <div className="text-xs text-gray-500">To-Be Workflow — React Flow 캔버스</div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* 시트 탭 */}
          {wfJson && wfJson.sheets.length > 1 && (
            <div className="flex gap-1 mr-4">
              {wfJson.sheets.map((s, i) => (
                <button
                  key={s.id}
                  onClick={() => setActiveSheetIdx(i)}
                  className={`px-3 py-1.5 rounded text-xs font-medium border transition ${
                    activeSheetIdx === i
                      ? "bg-red-600 text-white border-red-600"
                      : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
                  }`}
                >
                  {s.name}
                </button>
              ))}
            </div>
          )}

          {/* 범례 */}
          <div className="hidden md:flex items-center gap-2 mr-4">
            {Object.entries(AUTOMATION_COLOR).map(([k, v]) => (
              <div key={k} className="flex items-center gap-1">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: v.bg, border: `1px solid ${v.border}` }} />
                <span className="text-[10px] text-gray-500">{shortLevel(k)}</span>
              </div>
            ))}
          </div>

          <button
            onClick={loadJson}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-gray-300 text-sm text-gray-600 hover:bg-gray-50 transition disabled:opacity-50"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            새로고침
          </button>

          <button
            onClick={() => downloadToBeWorkflowJson().catch((e) => setError((e as Error).message))}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium text-white transition"
            style={{ backgroundColor: "#A62121" }}
          >
            <Download className="h-3.5 w-3.5" />
            JSON 다운로드
          </button>

          <button
            onClick={onClose}
            className="flex items-center justify-center w-8 h-8 rounded-full border border-gray-300 text-gray-500 hover:bg-gray-100 transition"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* 오류 */}
      {error && (
        <div className="px-6 py-2 bg-red-50 border-b border-red-200 text-sm text-red-700 shrink-0">
          {error}
          <button className="ml-2 underline" onClick={() => setError(null)}>닫기</button>
        </div>
      )}

      {/* 로딩 */}
      {loading && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="inline-block h-10 w-10 animate-spin rounded-full border-4 border-red-200 border-t-red-600 mb-3" />
            <p className="text-sm text-gray-500">Workflow JSON 로딩 중...</p>
          </div>
        </div>
      )}

      {/* 빈 상태 */}
      {!loading && !wfJson && !error && (
        <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
          <div className="text-center">
            <div className="text-4xl mb-3">&#128203;</div>
            <p>Step 1 기본 설계를 먼저 실행하세요.</p>
          </div>
        </div>
      )}

      {/* React Flow 캔버스 */}
      {!loading && sheet && (
        <div className="flex-1 relative overflow-hidden">
          {/* 시트 이름 */}
          <div className="absolute top-3 left-4 z-10 px-3 py-1 rounded-full text-xs font-bold bg-white border border-gray-200 shadow-sm text-gray-700">
            {sheet.name}
            <span className="ml-2 text-gray-400">
              {sheet.nodes.length}개 Task · {sheet.lanes.length}개 Agent
            </span>
          </div>

          <ReactFlowProvider>
            <FlowCanvas sheet={sheet} />
          </ReactFlowProvider>
        </div>
      )}

      {/* 통계 바 */}
      {!loading && sheet && (
        <div className="flex items-center gap-6 px-6 py-2 border-t border-gray-200 bg-gray-50 shrink-0 text-xs text-gray-500">
          <span>Agent: <strong className="text-gray-800">{sheet.lanes.length}</strong></span>
          <span>Task: <strong className="text-gray-800">{sheet.nodes.length}</strong></span>
          <span>엣지: <strong className="text-gray-800">{sheet.edges.length}</strong></span>
          {sheet.agentColors && (
            <div className="flex items-center gap-2 ml-4">
              {sheet.lanes.map((lane, i) => {
                const agentId = Object.keys(sheet.agentColors!)[i];
                const color = agentId ? sheet.agentColors![agentId] : "#9e9e9e";
                return (
                  <div key={i} className="flex items-center gap-1">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
                    <span>{lane}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
