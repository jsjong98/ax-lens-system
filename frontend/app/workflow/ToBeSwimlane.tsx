"use client";

import { type TobeSheet, type TobeNode, type TobeActor } from "@/lib/api";

// ── 상수 ──────────────────────────────────────────────────────────────────────

const ACTOR_ORDER: TobeActor[] = [
  "임원", "현업 팀장", "HR 임원", "HR 담당자",
  "Senior AI", "Junior AI", "현업 구성원", "그 외",
];

const ACTOR_STYLE: Record<TobeActor, { lane: string; bg: string; border: string; text: string; label: string }> = {
  "임원":       { lane: "#FFFBEB", bg: "#FEF3C7", border: "#F59E0B", text: "#92400E", label: "#78350F" },
  "현업 팀장":  { lane: "#EFF6FF", bg: "#DBEAFE", border: "#60A5FA", text: "#1E40AF", label: "#1E3A8A" },
  "HR 임원":    { lane: "#F5F3FF", bg: "#EDE9FE", border: "#8B5CF6", text: "#5B21B6", label: "#4C1D95" },
  "HR 담당자":  { lane: "#F0F9FF", bg: "#E0F2FE", border: "#38BDF8", text: "#0C4A6E", label: "#0369A1" },
  "Senior AI":  { lane: "#F0FDF4", bg: "#BBF7D0", border: "#22C55E", text: "#14532D", label: "#166534" },
  "Junior AI":  { lane: "#ECFDF5", bg: "#D1FAE5", border: "#34D399", text: "#065F46", label: "#047857" },
  "현업 구성원":{ lane: "#FFF1F2", bg: "#FFE4E6", border: "#FB7185", text: "#9F1239", label: "#881337" },
  "그 외":      { lane: "#F9FAFB", bg: "#F3F4F6", border: "#9CA3AF", text: "#374151", label: "#1F2937" },
};

// 레이아웃 상수
const ACTOR_COL_W = 88;   // 왼쪽 액터 이름 열 너비
const NODE_W      = 150;  // 노드 너비
const NODE_H      = 52;   // 노드 높이
const COL_GAP     = 36;   // 열 간격
const LANE_H      = 96;   // 액터 행 높이 (사용 중인 행)
const NODE_RADIUS = 8;    // 노드 둥근 모서리

// ── 레이아웃 계산 ─────────────────────────────────────────────────────────────

/** 위상 정렬로 각 노드의 열(column) 위치 결정 */
function computeColumns(nodes: TobeNode[]): Map<string, number> {
  const byId = new Map(nodes.map(n => [n.id, n]));
  const inDeg = new Map(nodes.map(n => [n.id, 0]));

  for (const n of nodes) {
    for (const nxt of n.next ?? []) {
      inDeg.set(nxt, (inDeg.get(nxt) ?? 0) + 1);
    }
  }

  const cols = new Map<string, number>();
  const queue: string[] = [];

  for (const n of nodes) {
    if (!inDeg.get(n.id)) {
      queue.push(n.id);
      cols.set(n.id, 0);
    }
  }

  while (queue.length > 0) {
    const id = queue.shift()!;
    const col = cols.get(id) ?? 0;
    for (const nxt of byId.get(id)?.next ?? []) {
      const nc = Math.max(cols.get(nxt) ?? 0, col + 1);
      cols.set(nxt, nc);
      inDeg.set(nxt, (inDeg.get(nxt) ?? 0) - 1);
      if ((inDeg.get(nxt) ?? 0) <= 0) queue.push(nxt);
    }
  }
  // 사이클 등 미방문 노드 fallback
  for (const n of nodes) {
    if (!cols.has(n.id)) cols.set(n.id, 0);
  }
  return cols;
}

/** 노드 레이블을 한/영 혼합 기준으로 두 줄 분리 */
function splitLabel(label: string): [string, string] {
  if (label.length <= 10) return [label, ""];
  // 공백 기준 분리 시도
  const sp = label.lastIndexOf(" ", 10);
  if (sp > 0) return [label.slice(0, sp), label.slice(sp + 1)];
  return [label.slice(0, 10), label.slice(10, 20)];
}

// ── SVG 노드 도형 ──────────────────────────────────────────────────────────────

function NodeShape({
  x, y, node, style,
}: {
  x: number; y: number;
  node: TobeNode;
  style: typeof ACTOR_STYLE[TobeActor];
}) {
  const cx = x + NODE_W / 2;
  const cy = y + NODE_H / 2;
  const [line1, line2] = splitLabel(node.label);
  const isAI = node.actor === "Senior AI" || node.actor === "Junior AI";

  if (node.type === "start" || node.type === "end") {
    // 캡슐 형태
    const rx = NODE_W / 2;
    const ry = NODE_H / 2 - 4;
    return (
      <g>
        <ellipse cx={cx} cy={cy} rx={rx} ry={ry}
          fill={style.bg} stroke={style.border} strokeWidth={isAI ? 2 : 1.5} />
        <text x={cx} y={cy} textAnchor="middle" dominantBaseline="middle"
          fontSize={10} fontWeight={600} fill={style.text}>
          {node.label.slice(0, 14)}
        </text>
        {node.ai_support && <AiSupportBadge x={x + NODE_W - 6} y={y - 6} />}
      </g>
    );
  }

  if (node.type === "decision") {
    // 다이아몬드
    const hw = NODE_W / 2, hh = NODE_H / 2 - 2;
    const pts = `${cx},${cy - hh} ${cx + hw},${cy} ${cx},${cy + hh} ${cx - hw},${cy}`;
    return (
      <g>
        <polygon points={pts}
          fill={style.bg} stroke={style.border} strokeWidth={isAI ? 2 : 1.5} />
        <text x={cx} y={cy - 5} textAnchor="middle" dominantBaseline="middle"
          fontSize={9} fontWeight={600} fill={style.text}>{line1}</text>
        {line2 && (
          <text x={cx} y={cy + 8} textAnchor="middle" dominantBaseline="middle"
            fontSize={9} fill={style.text}>{line2}</text>
        )}
        {node.ai_support && <AiSupportBadge x={x + NODE_W - 6} y={y - 6} />}
      </g>
    );
  }

  // 기본 task
  return (
    <g>
      <rect x={x} y={y} width={NODE_W} height={NODE_H} rx={NODE_RADIUS}
        fill={style.bg} stroke={style.border}
        strokeWidth={isAI ? 2.5 : 1.5}
        strokeDasharray={isAI ? undefined : undefined}
        filter={isAI ? "drop-shadow(0 0 5px rgba(34,197,94,0.25))" : undefined}
      />
      <text x={cx} y={line2 ? cy - 8 : cy}
        textAnchor="middle" dominantBaseline="middle"
        fontSize={10.5} fontWeight={600} fill={style.text}>
        {line1}
      </text>
      {line2 && (
        <text x={cx} y={cy + 8}
          textAnchor="middle" dominantBaseline="middle"
          fontSize={10} fill={style.text}>
          {line2}
        </text>
      )}
      {node.ai_support && <AiSupportBadge x={x + NODE_W - 6} y={y - 6} />}
    </g>
  );
}

function AiSupportBadge({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <circle cx={x} cy={y} r={9} fill="#22C55E" />
      <text x={x} y={y} textAnchor="middle" dominantBaseline="middle"
        fontSize={7} fontWeight={700} fill="white">AI</text>
    </g>
  );
}

// ── 화살표 경로 ────────────────────────────────────────────────────────────────

function Arrow({
  x1, y1, x2, y2, key,
}: {
  x1: number; y1: number; x2: number; y2: number; key: string;
}) {
  const sameLane = Math.abs(y1 - y2) < 4;
  let d: string;

  if (sameLane) {
    d = `M${x1},${y1} H${x2}`;
  } else {
    // 직각 꺾임: 출발점 → 중간X → 목적지Y → 목적지X
    const midX = (x1 + x2) / 2;
    d = `M${x1},${y1} H${midX} V${y2} H${x2}`;
  }

  return (
    <path key={key} d={d} fill="none"
      stroke="#94A3B8" strokeWidth={1.5}
      markerEnd="url(#arrowhead)"
      strokeLinejoin="round" />
  );
}

// ── 메인 컴포넌트 ──────────────────────────────────────────────────────────────

export function ToBeSwimlane({ sheet }: { sheet: TobeSheet }) {
  const { nodes, actors_used } = sheet;

  // 실제로 사용하는 액터만 (순서 보존)
  const usedActors = ACTOR_ORDER.filter(
    a => actors_used.includes(a) || nodes.some(n => n.actor === a)
  );

  const actorRowIdx = new Map(usedActors.map((a, i) => [a, i]));
  const colMap = computeColumns(nodes);
  const maxCol = nodes.length > 0 ? Math.max(...[...colMap.values()]) : 0;

  const svgW = ACTOR_COL_W + (maxCol + 1) * (NODE_W + COL_GAP) + COL_GAP;
  const svgH = usedActors.length * LANE_H + 1;

  // 각 노드의 중심 좌표 (x=노드 사각형 왼쪽, y=노드 사각형 위쪽)
  const nodeX = (id: string) => {
    const col = colMap.get(id) ?? 0;
    return ACTOR_COL_W + col * (NODE_W + COL_GAP) + COL_GAP;
  };
  const nodeY = (actor: TobeActor) => {
    const row = actorRowIdx.get(actor) ?? 0;
    return row * LANE_H + (LANE_H - NODE_H) / 2;
  };
  // 화살표 연결점: 노드 오른쪽 중심 → 다음 노드 왼쪽 중심
  const rightMidY  = (actor: TobeActor) => (actorRowIdx.get(actor) ?? 0) * LANE_H + LANE_H / 2;
  const rightEdgeX = (id: string) => nodeX(id) + NODE_W;
  const leftEdgeX  = (id: string) => nodeX(id);

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
      <svg
        width={svgW} height={svgH}
        xmlns="http://www.w3.org/2000/svg"
        style={{ display: "block", minWidth: svgW }}
      >
        <defs>
          <marker id="arrowhead" markerWidth="8" markerHeight="6"
            refX="7" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="#94A3B8" />
          </marker>
        </defs>

        {/* 레인 배경 */}
        {usedActors.map((actor, i) => {
          const st = ACTOR_STYLE[actor];
          return (
            <g key={actor}>
              <rect x={0} y={i * LANE_H} width={svgW} height={LANE_H}
                fill={st.lane} />
              {/* 레인 구분선 */}
              <line x1={0} y1={i * LANE_H} x2={svgW} y2={i * LANE_H}
                stroke="#E2E8F0" strokeWidth={1} />
            </g>
          );
        })}
        {/* 마지막 줄 아래 선 */}
        <line x1={0} y1={svgH - 1} x2={svgW} y2={svgH - 1}
          stroke="#E2E8F0" strokeWidth={1} />

        {/* 액터 이름 열 배경 */}
        <rect x={0} y={0} width={ACTOR_COL_W} height={svgH}
          fill="#F8FAFC" />
        <line x1={ACTOR_COL_W} y1={0} x2={ACTOR_COL_W} y2={svgH}
          stroke="#CBD5E1" strokeWidth={1.5} />

        {/* 액터 이름 뱃지 */}
        {usedActors.map((actor, i) => {
          const st = ACTOR_STYLE[actor];
          const cy = i * LANE_H + LANE_H / 2;
          return (
            <g key={actor}>
              <rect x={6} y={i * LANE_H + 10} width={ACTOR_COL_W - 12} height={LANE_H - 20}
                rx={6} fill={st.bg} stroke={st.border} strokeWidth={1.5} />
              <text x={ACTOR_COL_W / 2} y={cy}
                textAnchor="middle" dominantBaseline="middle"
                fontSize={10.5} fontWeight={700} fill={st.label}>
                {actor}
              </text>
            </g>
          );
        })}

        {/* 화살표 (노드 아래 레이어) */}
        {nodes.map(n =>
          (n.next ?? []).map(nxtId => {
            const srcActor = n.actor;
            const tgtNode = nodes.find(x => x.id === nxtId);
            if (!tgtNode) return null;
            const tgtActor = tgtNode.actor;

            return (
              <Arrow
                key={`${n.id}-${nxtId}`}
                x1={rightEdgeX(n.id)}
                y1={rightMidY(srcActor)}
                x2={leftEdgeX(nxtId)}
                y2={rightMidY(tgtActor)}
              />
            );
          })
        )}

        {/* 노드 */}
        {nodes.map(n => (
          <NodeShape
            key={n.id}
            x={nodeX(n.id)}
            y={nodeY(n.actor)}
            node={n}
            style={ACTOR_STYLE[n.actor] ?? ACTOR_STYLE["그 외"]}
          />
        ))}
      </svg>

      {/* AI 지원 노드 범례 */}
      {nodes.some(n => n.ai_support) && (
        <div className="flex items-center gap-2 px-4 py-2 border-t border-gray-100 bg-gray-50 text-[10px] text-gray-500">
          <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-green-500 text-white font-bold text-[7px]">AI</span>
          <span>초록 뱃지 = 해당 Task에서 AI 보조 있음</span>
          {nodes
            .filter(n => n.ai_support)
            .map(n => (
              <span key={n.id} className="ml-2 text-gray-400">
                [{n.label}: {n.ai_support}]
              </span>
            ))}
        </div>
      )}
    </div>
  );
}
