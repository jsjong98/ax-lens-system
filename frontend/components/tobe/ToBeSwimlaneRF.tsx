"use client";

/**
 * ToBeSwimlaneRF — hr-workflow-ai 스타일 React Flow 기반 Swim Lane 렌더러
 *
 * 백엔드 generate-tobe-flow의 응답을 그대로 받아:
 *   1. As-Is 노드/엣지/role/position 보존
 *   2. Senior AI / Junior AI 레인을 추가로 표시
 *   3. LevelNode (L2~L5) + DecisionNode + OrthoEdge 컴포넌트로 렌더
 */

import { useCallback, useMemo, useRef, useState, Component, type ErrorInfo, type ReactNode } from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type NodeTypes,
  type EdgeTypes,
  MarkerType,
} from "@xyflow/react";
import { L2Node, L3Node, L4Node, L5Node, DecisionNode, MemoNode } from "./LevelNode";
import OrthoEdge from "./OrthoEdge";
import SwimLaneOverlay from "./SwimLaneOverlay";
import type { TobeSheet, TobeNode } from "@/lib/api";

// ── Error Boundary — 렌더 오류를 화면에 표시 (generic "client-side exception" 대신) ──
class ToBeErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    // 콘솔에 상세 로그
    // eslint-disable-next-line no-console
    console.error("[ToBeSwimlaneRF] render error:", error, info);
  }
  render() {
    if (this.state.error) {
      return (
        <div className="p-4 rounded-lg border border-red-300 bg-red-50 text-xs text-red-800 overflow-auto" style={{ maxHeight: 400 }}>
          <div className="font-bold mb-2">⚠️ Swim Lane 렌더링 오류</div>
          <div className="font-mono whitespace-pre-wrap break-all">
            {this.state.error.message}
          </div>
          {this.state.error.stack && (
            <pre className="mt-2 text-[10px] opacity-70 whitespace-pre-wrap">
              {this.state.error.stack.split("\n").slice(0, 8).join("\n")}
            </pre>
          )}
        </div>
      );
    }
    return this.props.children;
  }
}

const nodeTypes: NodeTypes = {
  l2: L2Node,
  l3: L3Node,
  l4: L4Node,
  l5: L5Node,
  decision: DecisionNode,
  memo: MemoNode,
};

const edgeTypes: EdgeTypes = {
  ortho: OrthoEdge,
};

const NODE_TYPE_BY_LEVEL: Record<string, string> = {
  L2: "l2", L3: "l3", L4: "l4", L5: "l5",
  DECISION: "decision", MEMO: "memo",
};

interface Props {
  sheet: TobeSheet;
}

function ToBeSwimlaneInner({ sheet }: Props) {
  const canvasRef = useRef<HTMLDivElement>(null);

  // lane 순서 — sheet.lanes (백엔드가 표준 순서로 정렬해서 보냄)
  const lanes = useMemo(() => {
    const l = sheet?.lanes ?? sheet?.actors_used ?? [];
    return Array.isArray(l) ? l.filter(Boolean) : [];
  }, [sheet]);

  // 각 lane의 높이 (가변): 해당 lane의 노드 수에 따라 동적
  const initialLaneHeights = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const n of sheet.nodes ?? []) {
      const a = (n as TobeNode).actor || "그 외";
      counts[a] = (counts[a] ?? 0) + 1;
    }
    return lanes.map((lane) => {
      const c = counts[lane] ?? 0;
      // L5 노드는 ~150px, 여유 포함 stack당 200px + padding 80
      return Math.max(280, c * 200 + 80);
    });
  }, [lanes, sheet.nodes]);

  const [laneHeights, setLaneHeights] = useState<number[]>(initialLaneHeights);

  // lane index → cumulative Y (lane 시작 Y)
  const laneYStart = useMemo(() => {
    const arr: number[] = [];
    let acc = 0;
    for (const h of laneHeights) {
      arr.push(acc);
      acc += h;
    }
    return arr;
  }, [laneHeights]);

  // 우리 To-Be 데이터 → React Flow nodes
  const rfNodes: Node[] = useMemo(() => {
    if (!lanes.length) return [];
    // 각 lane 안에서 노드들을 collect — 같은 lane 내에서 x는 보존, y는 lane-start 기준 stack
    const laneStackY: Record<string, number> = {};
    const out: Node[] = [];

    // lane별로 노드를 모아 x 정렬
    const byLane: Record<string, TobeNode[]> = {};
    for (const n of (sheet.nodes ?? []) as TobeNode[]) {
      const a = lanes.includes(n.actor) ? n.actor : "그 외";
      (byLane[a] ??= []).push(n);
    }
    for (const lane of lanes) {
      (byLane[lane] ?? []).sort((a, b) => (a.position?.x ?? 0) - (b.position?.x ?? 0));
    }

    for (const lane of lanes) {
      const laneIdx = lanes.indexOf(lane);
      const yStart = laneYStart[laneIdx] ?? 0;
      const items = byLane[lane] ?? [];

      for (let i = 0; i < items.length; i++) {
        const n = items[i];
        const stackY = laneStackY[lane] ?? 0;
        laneStackY[lane] = stackY + 1;

        const nodeType = NODE_TYPE_BY_LEVEL[n.level] || "l5";
        const x = n.position?.x ?? (i * 380 + 120);
        // y: lane 시작 + stack offset (같은 x에 여러 노드면 세로로 스택)
        const overlapStack = items.filter(
          (m, mi) => mi < i && Math.abs((m.position?.x ?? 0) - x) < 30
        ).length;
        const y = yStart + 60 + overlapStack * 220;

        // data: 백엔드가 보낸 풀 data 객체 + LevelNode가 기대하는 필드 매핑
        const data = {
          ...(n.data ?? {}),
          label: n.label,
          level: n.level,
          id: n.task_id || (n.data as Record<string, unknown> | undefined)?.id,
          description: n.description ?? (n.data as { description?: string } | undefined)?.description,
          // role 원본 그대로 — LevelNode의 extractCustomRole이 "그 외:DDI" 파싱
          role: (n.data as { role?: string } | undefined)?.role
            ?? (n.actors_all && n.actors_all.length > 0
              ? n.actors_all.join(", ") + (n.custom_role ? `, 그 외:${n.custom_role}` : "")
              : ""),
          // AI 노드 표시
          memo: n.ai_support || (n.data as { memo?: string } | undefined)?.memo,
        };

        out.push({
          id: n.id,
          type: nodeType,
          position: { x, y },
          data,
          draggable: true,
        });
      }
    }
    return out;
  }, [lanes, sheet.nodes, laneYStart]);

  // edges
  const rfEdges: Edge[] = useMemo(() => {
    const edges: Edge[] = [];
    for (const e of sheet.edges ?? []) {
      const isAi = e.origin === "ai";
      edges.push({
        id: e.id,
        source: e.source,
        target: e.target,
        type: "ortho",
        label: e.label,
        animated: isAi,
        style: {
          stroke: isAi ? "#00827F" : "#64748B",
          strokeWidth: isAi ? 2 : 1.5,
          strokeDasharray: isAi ? "6 4" : undefined,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 18,
          height: 18,
          color: isAi ? "#00827F" : "#64748B",
        },
      });
    }
    return edges;
  }, [sheet.edges]);

  const onLaneHeightsChange = useCallback((heights: number[]) => {
    setLaneHeights(heights);
  }, []);

  return (
    <div
      ref={canvasRef}
      className="w-full rounded-lg border border-gray-200 bg-white"
      style={{ height: 720 }}
    >
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        proOptions={{ hideAttribution: true }}
        minZoom={0.1}
        maxZoom={1.5}
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#E2E8F0" />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={(n) => {
            const lvl = (n.data as { level?: string } | undefined)?.level;
            if (lvl === "L2") return "#A62121";
            if (lvl === "L3") return "#D95578";
            if (lvl === "L4") return "#DEDEDE";
            return "#FFFFFF";
          }}
          pannable
          zoomable
        />
        <SwimLaneOverlay
          lanes={lanes}
          laneHeights={laneHeights}
          onLaneHeightsChange={onLaneHeightsChange}
          canvasRef={canvasRef}
        />
      </ReactFlow>
    </div>
  );
}

export function ToBeSwimlaneRF({ sheet }: Props) {
  return (
    <ToBeErrorBoundary>
      <ReactFlowProvider>
        <ToBeSwimlaneInner sheet={sheet} />
      </ReactFlowProvider>
    </ToBeErrorBoundary>
  );
}
