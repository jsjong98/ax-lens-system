"use client";

/**
 * ToBeSwimlaneRF — hr-workflow-ai 스타일 React Flow 기반 Swim Lane 렌더러
 *
 * 백엔드 generate-tobe-flow의 응답을 그대로 받아:
 *   1. As-Is 노드/엣지/role/position 보존
 *   2. Senior AI / Junior AI 레인을 추가로 표시
 *   3. LevelNode (L2~L5) + DecisionNode + OrthoEdge 컴포넌트로 렌더
 */

import { useCallback, useEffect, useMemo, useRef, useState, Component, type ErrorInfo, type ReactNode } from "react";
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

  // 🔑 백엔드가 laneHeights 를 명시적으로 보내면 그 값을 그대로 사용
  // (hr-workflow-ai SwimLaneOverlay 와 동일한 정책 — 앱 기본값 대신 저장된 값 우선)
  const initialLaneHeights = useMemo(
    () => {
      const fromBackend = (sheet as { laneHeights?: number[] })?.laneHeights;
      if (fromBackend && fromBackend.length === lanes.length) return fromBackend;
      return lanes.map(() => 600);  // hr-workflow-ai 기본값 (swimHeight=2400/4=600)
    },
    [lanes, sheet],
  );

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

      // 같은 lane 내 실제 배치된 x 추적 (충돌 시 오른쪽으로 밀어냄)
      const placedXs: number[] = [];

      for (let i = 0; i < items.length; i++) {
        const n = items[i];
        const stackY = laneStackY[lane] ?? 0;
        laneStackY[lane] = stackY + 1;

        const nodeType = NODE_TYPE_BY_LEVEL[n.level] || "l5";
        // x 충돌 해소 — 직전 배치 노드보다 최소 440px(L5 폭 380 + gap 60) 확보
        let x = n.position?.x ?? (i * 440 + 120);
        const lastX = placedXs.length > 0 ? placedXs[placedXs.length - 1] : -Infinity;
        if (x < lastX + 440) x = lastX + 440;
        placedXs.push(x);
        // y: backend 가 laneHeights 기반으로 계산한 position.y 를 우선 사용
        //     (hr-workflow-ai 규격 — 값이 lane 범위 안에 들어오면 그대로)
        //     값이 없거나 lane 범위 밖이면 fallback 으로 lane 시작 + 여백
        const backendY = n.position?.y;
        const laneEndY = yStart + (laneHeights[laneIdx] ?? 600);
        const y = (
          typeof backendY === "number" && backendY >= yStart && backendY <= laneEndY
        ) ? backendY : yStart + 40;

        // data: 백엔드가 보낸 풀 data 객체 + LevelNode가 기대하는 필드 매핑
        // 방어: role이 string이 아닐 수 있음 (dict/object/undefined) → 반드시 문자열로 강제
        const rawRole = (n.data as { role?: unknown } | undefined)?.role;
        const roleStr =
          typeof rawRole === "string"
            ? rawRole
            : n.actors_all && n.actors_all.length > 0
              ? n.actors_all.join(", ") + (n.custom_role ? `, 그 외:${n.custom_role}` : "")
              : "";
        const rawMemo = (n.data as { memo?: unknown } | undefined)?.memo;
        const memoStr = typeof rawMemo === "string" ? rawMemo : "";

        const data = {
          ...(n.data ?? {}),
          label: n.label,
          level: n.level,
          // ID 표시 우선순위: 백엔드 display_id (2.1.4.N 형식) > task_id > data.id
          id: (n as { display_id?: string }).display_id
            || n.task_id
            || (n.data as Record<string, unknown> | undefined)?.id,
          description: n.description
            ?? n.ai_support
            ?? (n.data as { description?: string } | undefined)?.description,
          role: roleStr,
          // memo 필드는 원본 As-Is에 memo가 있을 때만 유지 (AI 설명은 노란 스티커로 띄우지 않음)
          memo: memoStr || undefined,
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
  }, [lanes, sheet.nodes, laneYStart, laneHeights]);

  // edges — backend 가 hr-workflow-ai 표준 포맷 (type/animated/style/markerEnd) 을
  // 직접 보내므로 그대로 React Flow 에 전달. 프론트에서 임의로 색/굵기 덮어쓰지 않음.
  const rfEdges: Edge[] = useMemo(() => {
    const edges: Edge[] = [];
    for (const e of sheet.edges ?? []) {
      const raw = e as unknown as {
        id: string; source: string; target: string; label?: string;
        type?: string; animated?: boolean;
        style?: Record<string, unknown>;
        markerEnd?: { type?: string; width?: number; height?: number; color?: string };
      };
      // backend 가 markerEnd.type 를 소문자 "arrowclosed" 문자열로 보내므로
      // React Flow 의 MarkerType enum 값으로 정규화 (동일 문자열 "arrowclosed")
      const me = raw.markerEnd
        ? {
            type: MarkerType.ArrowClosed,
            width: raw.markerEnd.width ?? 18,
            height: raw.markerEnd.height ?? 18,
            color: raw.markerEnd.color ?? "#333333",
          }
        : undefined;
      edges.push({
        id: raw.id,
        source: raw.source,
        target: raw.target,
        type: raw.type ?? "ortho",
        label: raw.label,
        animated: raw.animated ?? false,
        style: (raw.style as React.CSSProperties | undefined) ?? {
          stroke: "#333333", strokeWidth: 1.5,
        },
        markerEnd: me,
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
  // SSR/hydration mismatch 방지: 브라우저 mount 이후에만 React Flow 렌더
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <div className="h-[200px] rounded-lg border border-gray-200 bg-gray-50 flex items-center justify-center text-xs text-gray-400">
        Swim Lane 로딩 중...
      </div>
    );
  }

  return (
    <ToBeErrorBoundary>
      <ReactFlowProvider>
        <ToBeSwimlaneInner sheet={sheet} />
      </ReactFlowProvider>
    </ToBeErrorBoundary>
  );
}
