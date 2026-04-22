"use client";

import { useState, useCallback, useRef } from "react";
import { Plus, Trash2, Save, X } from "lucide-react";
import type { NewWorkflowResult } from "@/lib/api";

/* ── 데이터 타입 ──────────────────────────────────────────────────────────── */

interface InputBox {
  id: string;
  title: string;
  subtitle: string;
  ownerAgent: number; // agent index (for color)
}

interface TaskBox {
  id: string;
  title: string;
  description: string;
  badges: string[];
  needsHumanConfirm: boolean;
}

interface AgentColumn {
  id: string;
  number: number;
  name: string;
  tasks: TaskBox[];
  arrowToHuman?: string; // HR에게 보내는 화살표 라벨
}

interface HumanTask {
  id: string;
  title: string;
  description: string;
  column: number; // 어떤 agent column 아래에 위치할지 (0-based)
}

interface SwimlaneData {
  inputs: InputBox[];
  seniorAI: { title: string; description: string };
  agents: AgentColumn[];
  humanTasks: HumanTask[];
}

/* ── 뱃지 옵션 ────────────────────────────────────────────────────────────── */
const BADGE_OPTIONS = [
  { value: "LLM", label: "LLM", cls: "bg" },
  { value: "RAG", label: "RAG", cls: "bra" },
  { value: "RPA", label: "RPA", cls: "bra" },
  { value: "Rule-based", label: "Rule-based", cls: "br" },
  { value: "Tabular", label: "Tabular", cls: "bp" },
  { value: "OCR", label: "OCR", cls: "bo" },
  { value: "ML", label: "ML", cls: "bo" },
  { value: "최적화", label: "최적화", cls: "bo" },
  { value: "Human 확인", label: "Human 확인", cls: "bh" },
  { value: "API", label: "API", cls: "bra" },
  { value: "Chatbot", label: "Chatbot", cls: "bg" },
];

const BADGE_STYLE: Record<string, { bg: string; color: string; border: string }> = {
  bg:  { bg: "#FAEEDA", color: "#633806", border: "#BA7517" },
  bp:  { bg: "#E1F5EE", color: "#085041", border: "#1D9E75" },
  br:  { bg: "#F1EFE8", color: "#5F5E5A", border: "#888780" },
  bra: { bg: "#E8F4FF", color: "#0C447C", border: "#378ADD" },
  bh:  { bg: "#FCEBEB", color: "#A32D2D", border: "#F09595" },
  bo:  { bg: "#EEEDFE", color: "#3C3489", border: "#7F77DD" },
};

/* ── PPT 동일 색상 상수 ─────────────────────────────────────────────────── */
const AGENT_PALETTE = [
  "#1A3C6E", "#2E75B6", "#00827F", "#5B9BD5", "#4B0082",
  "#00A6A0", "#4172C4", "#7B68C4", "#006E90", "#87CEEB",
];
const agentColor = (idx: number) => AGENT_PALETTE[idx % AGENT_PALETTE.length];
const C_RED    = "#8B1A1A";   // Senior AI
const C_GOLD   = "#AA8E2A";   // Junior AI
const C_GRAY   = "#999999";   // 피드백
const C_HR_GOLD = "#B48E04";  // Junior→HR

function Badge({ value }: { value: string }) {
  const opt = BADGE_OPTIONS.find((b) => b.value === value);
  const cls = opt?.cls || "br";
  const s = BADGE_STYLE[cls] || BADGE_STYLE.br;
  return (
    <span className="text-[7.5px] font-medium px-2 py-0.5 rounded-lg whitespace-nowrap"
      style={{ backgroundColor: s.bg, color: s.color, border: `0.5px solid ${s.border}` }}>
      {value}
    </span>
  );
}

/* ── Workflow → Swimlane 변환 ─────────────────────────────────────────────── */
function workflowToSwimlane(result: NewWorkflowResult): SwimlaneData {
  // Junior AI 먼저 필터링 — inputOwner 인덱스를 Junior AI 기준으로 통일
  const juniorAgents = result.agents.filter((a) => a.agent_type === "Junior AI");
  const effectiveAgents = juniorAgents.length > 0 ? juniorAgents : result.agents;

  // Input → 해당 input 을 사용하는 모든 Junior AI 인덱스 (shared input 대응)
  // 하나의 Input 이 여러 Junior AI 에게 공급되면 각 agent 컬럼에 모두 표시됨 (색상 일치)
  const inputOwners: Record<string, number[]> = {};
  for (let ai = 0; ai < effectiveAgents.length; ai++) {
    for (const task of effectiveAgents[ai].assigned_tasks) {
      task.input_data?.forEach((d) => {
        const owners = inputOwners[d] ?? (inputOwners[d] = []);
        if (!owners.includes(ai)) owners.push(ai);
      });
    }
  }

  // 각 owner 컬럼별로 input 을 복제 배치 → 색상 = 해당 agent 색상 (정렬 보장)
  const inputs: InputBox[] = [];
  const _seenTitles = new Set<string>();
  // agent 순서대로 순회 — 컬럼 정렬 위해 ownerAgent 오름차순
  for (let ai = 0; ai < effectiveAgents.length; ai++) {
    for (const d of Object.keys(inputOwners)) {
      if (!inputOwners[d].includes(ai)) continue;
      // 같은 title + 같은 ownerAgent 조합만 중복 제거 (다른 agent 컬럼에는 중복 허용)
      const key = `${ai}::${d}`;
      if (_seenTitles.has(key)) continue;
      _seenTitles.add(key);
      inputs.push({
        id: `input-${ai}-${inputs.length}`,
        title: d,
        subtitle: "",
        ownerAgent: ai,
      });
      if (inputs.length >= 20) break;
    }
    if (inputs.length >= 20) break;
  }

  // Senior AI: agent_type="Senior AI"인 첫 번째 에이전트를 오케스트레이터로 사용
  const seniorAgent = result.agents.find((a) => a.agent_type === "Senior AI");
  const seniorAI = {
    title: seniorAgent?.agent_name || `${result.process_name} 오케스트레이터`,
    description: seniorAgent?.description || result.blueprint_summary || "",
  };

  // 괄호 밖 구분자만으로 split (괄호 안 쉼표 보존). 예: "A(x, y), B" → ["A(x, y)", "B"]
  const splitTechStack = (s: string): string[] => {
    const out: string[] = [];
    let buf = "";
    let depth = 0;
    for (const ch of s) {
      if (ch === "(" || ch === "（") depth++;
      else if (ch === ")" || ch === "）") depth = Math.max(0, depth - 1);
      if (depth === 0 && (ch === "," || ch === "·" || ch === "+" || ch === "/")) {
        const v = buf.trim();
        if (v) out.push(v);
        buf = "";
      } else {
        buf += ch;
      }
    }
    const last = buf.trim();
    if (last) out.push(last);
    // 배지 1개가 20자 넘으면 뭔가 설명이 들어간 것 — 자르지 말고 그대로 표기 (짧지 않아도 한 덩어리로)
    return out;
  };

  // Junior AI 컬럼 — effectiveAgents 기준 (inputOwner와 동일 인덱스)
  const agents: AgentColumn[] = effectiveAgents.map((a, i) => ({
    id: a.agent_id,
    number: i + 1,
    name: a.agent_name,
    tasks: a.assigned_tasks.map((t) => {
      // task 전용 ai_technique을 우선, 없으면 Agent 기술로 fallback
      const taskTech = (t as { ai_technique?: string }).ai_technique;
      const techStr = (taskTech && taskTech.trim()) || a.ai_technique || "";
      return {
        id: t.task_id,
        title: t.task_name,
        description: t.ai_role || "",
        badges: techStr ? splitTechStack(techStr) : [],
        needsHumanConfirm: t.automation_level !== "Human-on-the-Loop",
      };
    }),
    arrowToHuman: a.assigned_tasks.some((t) => t.automation_level !== "Human-on-the-Loop")
      ? `${a.agent_name} 결과 HR 담당자 확인 요청`
      : undefined,
  }));

  // Human Tasks
  const humanTasks: HumanTask[] = [];
  result.agents.forEach((a, i) => {
    a.assigned_tasks
      .filter((t) => t.automation_level !== "Human-on-the-Loop")
      .forEach((t) => {
        humanTasks.push({
          id: `human-${t.task_id}`,
          title: t.task_name || "검토",
          description: t.human_role || "최종 확인",
          column: i,
        });
      });
  });

  return { inputs, seniorAI, agents, humanTasks };
}

/* ── 편집 모달 ────────────────────────────────────────────────────────────── */
interface EditModalProps {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}

function EditModal({ title, children, onClose }: EditModalProps) {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-2xl max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-bold text-gray-900">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X className="h-5 w-5" /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════ */
/* ── Pain Context Panel — Step 2 설계에 반영된 Pain Point + 분류 가시화 ── */
/* ══════════════════════════════════════════════════════════════════════════ */

interface PainContextItem {
  task_id: string;
  task_name: string;
  l4: string;
  l3: string;
  classification: string;
  classification_reason: string;
  hybrid_note: string;
  ai_prerequisites: string;
  pain_points: Array<{ type: string; text: string }>;
}

function PainContextPanel({
  painContext,
  stats,
}: {
  painContext: PainContextItem[];
  stats?: { AI: number; "AI + Human": number; Human: number };
}) {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState<"" | "AI" | "AI + Human" | "Human">("");

  const totalPains = painContext.reduce((s, i) => s + i.pain_points.length, 0);
  const filtered = filter ? painContext.filter((i) => i.classification === filter) : painContext;

  const badge = (label: string, count: number, key: "" | "AI" | "AI + Human" | "Human", color: string) => (
    <button
      onClick={() => setFilter(filter === key ? "" : key)}
      className="text-[11px] font-semibold px-2.5 py-1 rounded-full border-[1.5px] transition"
      style={{
        borderColor: color,
        color: filter === key ? "#fff" : color,
        backgroundColor: filter === key ? color : "#fff",
      }}
    >
      {label} {count}
    </button>
  );

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50/50">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-left hover:bg-amber-50 rounded-t-lg"
      >
        <div className="flex items-center gap-3">
          <span className="text-[13px] font-bold text-amber-900">🔍 Step 2 설계에 반영된 Pain Point · 분류</span>
          <span className="text-[11px] text-amber-700">
            {painContext.length}개 태스크 · Pain {totalPains}개
          </span>
        </div>
        <span className="text-amber-700 text-xs">{open ? "▲ 접기" : "▼ 펼치기"}</span>
      </button>
      {open && (
        <div className="px-4 pb-3 pt-1 space-y-3">
          {stats && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[11px] text-gray-500">분류 필터:</span>
              {badge("AI", stats.AI, "AI", "#16A34A")}
              {badge("AI + Human", stats["AI + Human"], "AI + Human", "#F59E0B")}
              {badge("Human", stats.Human, "Human", "#B91C1C")}
              {filter && (
                <button onClick={() => setFilter("")} className="text-[10px] text-gray-400 underline">전체 보기</button>
              )}
            </div>
          )}
          <div className="max-h-[320px] overflow-y-auto space-y-2">
            {filtered.length === 0 && (
              <div className="text-[11px] text-gray-400 text-center py-4">해당 분류에 표시할 항목이 없습니다.</div>
            )}
            {filtered.map((item) => {
              const clsColor =
                item.classification === "AI" ? "#16A34A"
                : item.classification === "AI + Human" ? "#F59E0B"
                : item.classification === "Human" ? "#B91C1C"
                : "#6B7280";
              return (
                <div key={item.task_id} className="rounded-md border border-amber-200 bg-white p-2.5">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div className="flex-1 min-w-0">
                      <div className="text-[12px] font-bold text-gray-800">
                        [{item.task_id}] {item.task_name}
                      </div>
                      <div className="text-[10px] text-gray-500 mt-0.5">
                        {item.l3} / {item.l4}
                      </div>
                    </div>
                    {item.classification && (
                      <span
                        className="text-[10px] font-bold px-2 py-0.5 rounded-full whitespace-nowrap"
                        style={{ backgroundColor: clsColor + "15", color: clsColor, border: `1px solid ${clsColor}` }}
                      >
                        {item.classification}
                      </span>
                    )}
                  </div>
                  {item.classification_reason && (
                    <div className="text-[10.5px] text-gray-600 mt-1 leading-snug">
                      <span className="font-semibold text-gray-700">📋 판단 근거:</span> {item.classification_reason}
                    </div>
                  )}
                  {item.hybrid_note && (
                    <div className="text-[10.5px] text-amber-800 mt-1 leading-snug">
                      <span className="font-semibold">⚙️ AI/Human 분리:</span> {item.hybrid_note}
                    </div>
                  )}
                  {item.ai_prerequisites && (
                    <div className="text-[10.5px] text-blue-700 mt-1 leading-snug">
                      <span className="font-semibold">🔧 AI 수행 필요여건:</span> {item.ai_prerequisites}
                    </div>
                  )}
                  {item.pain_points.length > 0 && (
                    <div className="mt-1.5 space-y-0.5">
                      {item.pain_points.map((p, pi) => (
                        <div key={pi} className="text-[10.5px] text-red-700 leading-snug">
                          <span className="font-semibold">💢 {p.type}:</span> {p.text}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════ */
/* ── 메인 에디터 ──────────────────────────────────────────────────────────── */
/* ══════════════════════════════════════════════════════════════════════════ */

interface WorkflowEditorProps {
  result: NewWorkflowResult & {
    pain_context?: Array<{
      task_id: string;
      task_name: string;
      l4: string;
      l3: string;
      classification: string;
      classification_reason: string;
      hybrid_note: string;
      ai_prerequisites: string;
      pain_points: Array<{ type: string; text: string }>;
    }>;
    classification_stats?: { AI: number; "AI + Human": number; Human: number };
  };
  onSave: (updated: SwimlaneData) => void;
}

export default function WorkflowEditor({ result, onSave }: WorkflowEditorProps) {
  const [data, setData] = useState<SwimlaneData>(() => workflowToSwimlane(result));
  const [editingTask, setEditingTask] = useState<{ agentIdx: number; taskIdx: number } | null>(null);
  const [editingInput, setEditingInput] = useState<number | null>(null);
  const [editingSenior, setEditingSenior] = useState(false);
  const [editingHuman, setEditingHuman] = useState<number | null>(null);

  const update = useCallback((fn: (d: SwimlaneData) => SwimlaneData) => {
    setData((prev) => fn({ ...prev }));
  }, []);

  /* ── 핸들러들 ─────────────────────────────────────────────────────────── */

  // Input 편집
  const updateInput = (idx: number, field: keyof InputBox, value: string) => {
    update((d) => {
      d.inputs = [...d.inputs];
      d.inputs[idx] = { ...d.inputs[idx], [field]: value };
      return d;
    });
  };
  const addInput = () => {
    update((d) => ({
      ...d,
      inputs: [...d.inputs, { id: `input-${Date.now()}`, title: "새 Input", subtitle: "", ownerAgent: 0 }],
    }));
  };
  const deleteInput = (idx: number) => {
    update((d) => ({ ...d, inputs: d.inputs.filter((_, i) => i !== idx) }));
  };

  // Task 편집
  const updateTask = (agentIdx: number, taskIdx: number, field: keyof TaskBox, value: unknown) => {
    update((d) => {
      d.agents = [...d.agents];
      d.agents[agentIdx] = { ...d.agents[agentIdx], tasks: [...d.agents[agentIdx].tasks] };
      d.agents[agentIdx].tasks[taskIdx] = { ...d.agents[agentIdx].tasks[taskIdx], [field]: value };
      return d;
    });
  };
  const addTask = (agentIdx: number) => {
    update((d) => {
      d.agents = [...d.agents];
      d.agents[agentIdx] = {
        ...d.agents[agentIdx],
        tasks: [...d.agents[agentIdx].tasks, {
          id: `task-${Date.now()}`, title: "새 Task", description: "", badges: [], needsHumanConfirm: false,
        }],
      };
      return d;
    });
  };
  const deleteTask = (agentIdx: number, taskIdx: number) => {
    update((d) => {
      d.agents = [...d.agents];
      d.agents[agentIdx] = {
        ...d.agents[agentIdx],
        tasks: d.agents[agentIdx].tasks.filter((_, i) => i !== taskIdx),
      };
      return d;
    });
    setEditingTask(null);
  };

  // Agent 추가/삭제
  const addAgent = () => {
    update((d) => ({
      ...d,
      agents: [...d.agents, {
        id: `agent-${Date.now()}`, number: d.agents.length + 1, name: "새 에이전트",
        tasks: [], arrowToHuman: undefined,
      }],
    }));
  };
  const deleteAgent = (idx: number) => {
    update((d) => ({
      ...d,
      agents: d.agents.filter((_, i) => i !== idx).map((a, i) => ({ ...a, number: i + 1 })),
      humanTasks: d.humanTasks.filter((h) => h.column !== idx).map((h) => ({
        ...h, column: h.column > idx ? h.column - 1 : h.column,
      })),
    }));
  };

  // Human Task
  const addHumanTask = (column: number) => {
    update((d) => ({
      ...d,
      humanTasks: [...d.humanTasks, { id: `human-${Date.now()}`, title: "새 검토 항목", description: "", column }],
    }));
  };
  const deleteHumanTask = (idx: number) => {
    update((d) => ({ ...d, humanTasks: d.humanTasks.filter((_, i) => i !== idx) }));
    setEditingHuman(null);
  };

  // 에이전트 수에 따라 자동 줌 계산 (4개 이하: 100%, 5~6개: 70%, 7개+: 50%)
  const autoZoom = data.agents.length <= 3 ? 100 : data.agents.length <= 5 ? 70 : data.agents.length <= 7 ? 55 : 45;
  const [zoom, setZoom] = useState(autoZoom);
  const diagramRef = useRef<HTMLDivElement>(null);

  const handleSaveHtml = useCallback(() => {
    onSave(data);
    const container = diagramRef.current;
    if (!container) return;

    const processName = result.process_name || "workflow";
    const filename = `${processName}_상세설계.html`.replace(/[/\\:*?"<>|]/g, "_");

    const htmlContent = `<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${processName} — AI Service Flow 상세 설계</title>
  <script src="https://cdn.tailwindcss.com"><\/script>
  <style>
    body { font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif; background: #f8f8f6; margin: 0; padding: 24px; }
    h1 { font-size: 1.1rem; font-weight: 700; color: #1a1a1a; margin-bottom: 16px; }
    .diagram-wrap { background: #fff; border-radius: 12px; border: 1px solid #D3D1C7; overflow-x: auto; padding: 8px; }
  </style>
</head>
<body>
  <h1>${processName} — AI Service Flow 상세 설계</h1>
  <div class="diagram-wrap">
    ${container.innerHTML}
  </div>
</body>
</html>`;

    const blob = new Blob([htmlContent], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }, [data, result, onSave]);

  return (
    <div className="space-y-3">
      {/* 🔍 Pain Point + 분류 가시성 패널 (접이식) */}
      {(result.pain_context?.length || result.classification_stats) && (
        <PainContextPanel
          painContext={result.pain_context || []}
          stats={result.classification_stats}
        />
      )}

      {/* 상단 컨트롤 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button onClick={() => setZoom((z) => Math.max(50, z - 10))}
            className="rounded border px-2 py-1 text-xs text-gray-600 hover:bg-gray-50">−</button>
          <span className="text-xs text-gray-500 w-12 text-center">{zoom}%</span>
          <button onClick={() => setZoom((z) => Math.min(150, z + 10))}
            className="rounded border px-2 py-1 text-xs text-gray-600 hover:bg-gray-50">+</button>
          <button onClick={() => setZoom(autoZoom)}
            className="rounded border px-2 py-1 text-xs text-gray-500 hover:bg-gray-50">맞춤</button>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold px-3 py-1 rounded border-[1.5px]" style={{ borderColor: C_RED, color: C_RED }}>Senior AI</span>
          <span className="text-[11px] font-semibold px-3 py-1 rounded border-[1.5px]" style={{ borderColor: C_GOLD, color: C_GOLD }}>Junior AI</span>
          <span className="text-[11px] font-semibold px-3 py-1 rounded border-[1.5px] border-[#B4B2A9] text-[#5F5E5A]">사람</span>
          <button onClick={handleSaveHtml}
            className="flex items-center gap-2 rounded-lg px-4 py-1.5 text-xs font-semibold text-white"
            style={{ backgroundColor: "#A62121" }}>
            <Save className="h-3.5 w-3.5" /> HTML 저장
          </button>
        </div>
      </div>

      <div className="overflow-x-auto overflow-y-auto rounded-xl border" style={{ borderColor: "#D3D1C7", maxHeight: "70vh" }}>
        <div style={{ transform: `scale(${zoom / 100})`, transformOrigin: "top left", minWidth: zoom < 100 ? `${100 / (zoom / 100)}%` : "100%" }}>
        <div ref={diagramRef} style={{ borderColor: "#D3D1C7" }}>

        {/* ── INPUT 레인 — Junior AI 컬럼과 동일한 grid 로 정렬 (색상 매칭 가시화) ── */}
        <div className="grid" style={{ gridTemplateColumns: "56px 1fr", borderBottom: "0.5px solid #D3D1C7" }}>
          <div className="flex flex-col items-center justify-center gap-1 p-2 border-r bg-white" style={{ borderColor: "#D3D1C7" }}>
            <span className="text-lg">📥</span>
            <span className="text-[9px] font-bold text-[#5F5E5A]">Input</span>
          </div>
          <div className="p-3" style={{ backgroundColor: "#FAFAF8" }}>
            <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${Math.max(data.agents.length, 1)}, 1fr)` }}>
              {data.agents.map((_agent, ai) => {
                const colInputs = data.inputs
                  .map((inp, originalIdx) => ({ inp, originalIdx }))
                  .filter(({ inp }) => inp.ownerAgent === ai);
                return (
                  <div key={`input-col-${ai}`} className="flex flex-col gap-1.5">
                    {colInputs.map(({ inp, originalIdx }) => (
                      <div key={inp.id}
                        className="rounded-lg p-2 border-2 text-center cursor-pointer hover:ring-2 hover:ring-[#A62121] transition-shadow"
                        style={{ backgroundColor: "#F5F4F1", borderColor: agentColor(inp.ownerAgent) }}
                        onClick={() => setEditingInput(originalIdx)}>
                        <div className="text-[9.5px] font-semibold text-[#2C2C2A]">{inp.title}</div>
                        {inp.subtitle && <div className="text-[8px] text-[#888780]">{inp.subtitle}</div>}
                      </div>
                    ))}
                    {ai === data.agents.length - 1 && (
                      <button onClick={addInput}
                        className="rounded-lg border-2 border-dashed p-2 text-[10px] text-gray-400 hover:text-[#A62121] hover:border-[#A62121] transition-colors"
                        style={{ borderColor: "#D3D1C7" }}>
                        <Plus className="h-4 w-4 mx-auto" />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* ── Input → Junior AI 직접 연결선 (Agent 색상, 컬럼 정렬) ──────── */}
        <div className="grid" style={{ gridTemplateColumns: "56px 1fr" }}>
          <div className="border-r bg-white" style={{ borderColor: "#D3D1C7" }} />
          <div className="py-1 px-3" style={{ backgroundColor: "#FAFAF8" }}>
            <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${Math.max(data.agents.length, 1)}, 1fr)` }}>
              {data.agents.map((_agent, ai) => {
                const hasInput = data.inputs.some((inp) => inp.ownerAgent === ai);
                return (
                  <div key={`conn-col-${ai}`} className="flex justify-center">
                    {hasInput && (
                      <div className="w-[2px] h-3" style={{ backgroundColor: agentColor(ai) }} />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* ── SENIOR AI 레인 (풀 스팬 오케스트레이터) ──────────────────── */}
        <div className="grid" style={{ gridTemplateColumns: "56px 1fr", borderBottom: "0.5px solid #D3D1C7" }}>
          <div className="flex flex-col items-center justify-center gap-1 p-2 border-r bg-white" style={{ borderColor: "#D3D1C7" }}>
            <span className="text-lg">🤖</span>
            <span className="text-[9px] font-bold text-[#8B1A1A]">Senior<br/>AI</span>
          </div>
          <div className="p-3" style={{ backgroundColor: "#FDF4F4" }}>
            {/* 오케스트레이터 헤더 — 전체 폭 스팬 */}
            <div className="rounded-lg px-4 py-2 cursor-pointer hover:ring-2 hover:ring-[#8B1A1A] transition-shadow mb-2"
              style={{ border: "2px solid #8B1A1A", backgroundColor: "#FFF5F5" }}
              onClick={() => setEditingSenior(true)}>
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-xs font-bold text-[#8B1A1A] whitespace-nowrap">🧠 {data.seniorAI.title}</span>
                  <span className="text-[9px] text-[#888780] truncate">{data.seniorAI.description.slice(0, 100)}...</span>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <span className="text-[8px] font-semibold text-[#8B1A1A] bg-[#F5E0E0] rounded px-1.5 py-0.5">플로우 오케스트레이션</span>
                  <span className="text-[8px] font-semibold text-[#8B1A1A] bg-[#F5E0E0] rounded px-1.5 py-0.5">상태 관리</span>
                  <span className="text-[8px] font-semibold text-[#8B1A1A] bg-[#F5E0E0] rounded px-1.5 py-0.5">예외 라우팅</span>
                </div>
              </div>
            </div>

            {/* 각 Agent 컬럼별 지시/회수 화살표 — Senior AI 레인 안에 포함 */}
            <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${Math.max(data.agents.length, 1)}, 1fr)` }}>
              {data.agents.map((agent, ai) => (
                <div key={`orch-${agent.id}`} className="flex flex-col items-center gap-0">
                  {/* 오케스트레이션 라벨 */}
                  <span className="text-[7px] font-semibold text-[#8B1A1A] text-center leading-tight mb-0.5">
                    {"①②③④⑤⑥⑦⑧⑨⑩"[ai]} {agent.name}
                  </span>
                  {/* 양방향 화살표 */}
                  <div className="flex items-center gap-3">
                    {/* Senior → Junior */}
                    <div className="flex flex-col items-center gap-0">
                      <div className="w-[1.5px] h-3 bg-[#8B1A1A]" />
                      <div className="w-0 h-0 border-l-[3px] border-r-[3px] border-t-[4px] border-l-transparent border-r-transparent border-t-[#8B1A1A]" />
                      <span className="text-[6px] text-[#8B1A1A] font-medium">지시</span>
                    </div>
                    {/* Junior → Senior */}
                    <div className="flex flex-col items-center gap-0">
                      <span className="text-[6px] font-medium" style={{ color: C_GRAY }}>반환</span>
                      <div className="w-0 h-0 border-l-[3px] border-r-[3px] border-b-[4px] border-l-transparent border-r-transparent" style={{ borderBottomColor: C_GRAY }} />
                      <div className="w-[1.5px] h-3" style={{ backgroundColor: C_GRAY }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── JUNIOR AI 레인 ──────────────────────────────────────────── */}
        <div className="grid" style={{ gridTemplateColumns: "56px 1fr", borderBottom: "0.5px solid #D3D1C7" }}>
          <div className="flex flex-col items-center justify-center gap-1 p-2 border-r bg-white" style={{ borderColor: "#D3D1C7" }}>
            <span className="text-lg">🤖</span>
            <span className="text-[9px] font-bold text-[#AA8E2A]">Junior<br/>AI</span>
          </div>
          <div className="p-3" style={{ backgroundColor: "#FEFAF0" }}>
            <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${Math.max(data.agents.length, 1)}, 1fr)` }}>
              {data.agents.map((agent, ai) => (
                <div key={agent.id} className="flex flex-col">

                  {/* 에이전트 박스 — Input과 동일 색상으로 연결 */}
                  <div className="rounded-lg p-3 flex-1" style={{ border: `2px solid ${agentColor(ai)}`, backgroundColor: "#fff" }}>
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0"
                        style={{ backgroundColor: agentColor(ai) }}>
                        {agent.number}
                      </div>
                      <input className="text-[11px] font-bold text-[#2C2C2A] bg-transparent border-b border-transparent hover:border-gray-300 focus:border-[#AA8E2A] outline-none flex-1"
                        value={agent.name}
                        onChange={(e) => update((d) => {
                          d.agents = [...d.agents];
                          d.agents[ai] = { ...d.agents[ai], name: e.target.value };
                          return d;
                        })} />
                      <button onClick={() => deleteAgent(ai)} className="text-gray-300 hover:text-red-500 transition-colors">
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>

                    {/* Task 박스들 */}
                    <div className="flex flex-col gap-2">
                      {agent.tasks.map((task, ti) => (
                        <div key={task.id}
                          className={`rounded-md p-2 text-center cursor-pointer hover:ring-2 hover:ring-[#AA8E2A] transition-shadow ${
                            task.needsHumanConfirm ? "" : ""
                          }`}
                          style={{
                            backgroundColor: task.needsHumanConfirm ? "#FAEEDA" : "#F5F4F1",
                            border: task.needsHumanConfirm ? "0.5px dashed #BA7517" : "0.5px solid #D3D1C7",
                          }}
                          onClick={() => setEditingTask({ agentIdx: ai, taskIdx: ti })}>
                          <div className="text-[9px] font-semibold text-[#2C2C2A] mb-0.5">{task.title}</div>
                          <div className="text-[8px] text-[#888780] mb-1">{task.description}</div>
                          <div className="flex justify-center gap-1 flex-wrap">
                            {task.badges.map((b, bi) => <Badge key={bi} value={b} />)}
                          </div>
                        </div>
                      ))}
                      <button onClick={() => addTask(ai)}
                        className="rounded-md border-2 border-dashed p-2 text-[9px] text-gray-400 hover:text-[#AA8E2A] hover:border-[#AA8E2A] transition-colors"
                        style={{ borderColor: "#D3D1C7" }}>
                        <Plus className="h-3 w-3 mx-auto" /> Task 추가
                      </button>
                    </div>
                  </div>

                  {/* Junior → HR 전달 화살표 */}
                  {agent.arrowToHuman && (
                    <div className="flex flex-col items-center pt-2">
                      <div className="w-[2px] h-5" style={{ backgroundColor: C_HR_GOLD }} />
                      <div className="w-0 h-0 border-l-[5px] border-r-[5px] border-t-[7px] border-l-transparent border-r-transparent" style={{ borderTopColor: C_HR_GOLD }} />
                    </div>
                  )}
                </div>
              ))}

              {/* 에이전트 추가 */}
              <button onClick={addAgent}
                className="rounded-lg border-2 border-dashed p-4 flex flex-col items-center justify-center gap-1 text-gray-400 hover:text-[#AA8E2A] hover:border-[#AA8E2A] transition-colors min-h-[120px]"
                style={{ borderColor: "#D3D1C7" }}>
                <Plus className="h-5 w-5" />
                <span className="text-[10px] font-medium">에이전트 추가</span>
              </button>
            </div>
          </div>
        </div>

        {/* ── HR 담당자 레인 ──────────────────────────────────────────── */}
        <div className="grid" style={{ gridTemplateColumns: "56px 1fr" }}>
          <div className="flex flex-col items-center justify-center gap-1 p-2 border-r bg-white" style={{ borderColor: "#D3D1C7" }}>
            <span className="text-lg">👤</span>
            <span className="text-[9px] font-bold text-[#2C2C2A]">HR<br/>담당자</span>
          </div>
          <div className="p-3" style={{ backgroundColor: "#FAFAF8" }}>
            <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${Math.max(data.agents.length, 1)}, 1fr)` }}>
              {data.agents.map((_, ai) => {
                const tasks = data.humanTasks.filter((h) => h.column === ai);
                return (
                  <div key={ai} className="space-y-2">
                    {tasks.map((ht) => {
                      const realIdx = data.humanTasks.indexOf(ht);
                      return (
                        <div key={ht.id}
                          className="rounded-lg p-2 text-center cursor-pointer hover:ring-2 hover:ring-[#A62121] transition-shadow"
                          style={{ border: "0.5px solid #D3D1C7", backgroundColor: "#F5F4F1" }}
                          onClick={() => setEditingHuman(realIdx)}>
                          <div className="text-[9px] font-semibold text-[#2C2C2A]">{ht.title}</div>
                          <div className="text-[8px] text-[#888780]">{ht.description}</div>
                        </div>
                      );
                    })}
                    <button onClick={() => addHumanTask(ai)}
                      className="w-full rounded-md border-2 border-dashed p-1.5 text-[8px] text-gray-400 hover:text-[#A62121] hover:border-[#A62121] transition-colors"
                      style={{ borderColor: "#D3D1C7" }}>
                      + 검토 항목
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

        </div>
      </div>

      {/* ── 편집 모달들 ──────────────────────────────────────────────── */}

      {/* Input 편집 */}
      {editingInput !== null && (
        <EditModal title="Input 편집" onClose={() => setEditingInput(null)}>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">제목</label>
              <input className="w-full rounded-lg border px-3 py-2 text-sm"
                value={data.inputs[editingInput].title}
                onChange={(e) => updateInput(editingInput, "title", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">부제 (출처)</label>
              <input className="w-full rounded-lg border px-3 py-2 text-sm"
                value={data.inputs[editingInput].subtitle}
                onChange={(e) => updateInput(editingInput, "subtitle", e.target.value)} />
            </div>
            <button onClick={() => { deleteInput(editingInput); setEditingInput(null); }}
              className="flex items-center gap-2 text-sm text-red-600 hover:text-red-800">
              <Trash2 className="h-4 w-4" /> 삭제
            </button>
          </div>
        </EditModal>
      )}

      {/* Senior AI 편집 */}
      {editingSenior && (
        <EditModal title="Senior AI 편집" onClose={() => setEditingSenior(false)}>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">오케스트레이터 이름</label>
              <input className="w-full rounded-lg border px-3 py-2 text-sm"
                value={data.seniorAI.title}
                onChange={(e) => update((d) => ({ ...d, seniorAI: { ...d.seniorAI, title: e.target.value } }))} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">설명</label>
              <textarea className="w-full rounded-lg border px-3 py-2 text-sm resize-none" rows={3}
                value={data.seniorAI.description}
                onChange={(e) => update((d) => ({ ...d, seniorAI: { ...d.seniorAI, description: e.target.value } }))} />
            </div>
          </div>
        </EditModal>
      )}

      {/* Task 편집 */}
      {editingTask && (
        <EditModal title="Task 편집" onClose={() => setEditingTask(null)}>
          {(() => {
            const { agentIdx, taskIdx } = editingTask;
            const task = data.agents[agentIdx]?.tasks[taskIdx];
            if (!task) return null;
            return (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">Task 이름</label>
                  <input className="w-full rounded-lg border px-3 py-2 text-sm" value={task.title}
                    onChange={(e) => updateTask(agentIdx, taskIdx, "title", e.target.value)} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">설명</label>
                  <textarea className="w-full rounded-lg border px-3 py-2 text-sm resize-none" rows={2} value={task.description}
                    onChange={(e) => updateTask(agentIdx, taskIdx, "description", e.target.value)} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">AI 기법 (뱃지)</label>
                  <div className="flex flex-wrap gap-2">
                    {BADGE_OPTIONS.map((opt) => (
                      <label key={opt.value} className="flex items-center gap-1 text-xs">
                        <input type="checkbox" checked={task.badges.includes(opt.value)}
                          onChange={(e) => {
                            const newBadges = e.target.checked
                              ? [...task.badges, opt.value]
                              : task.badges.filter((b) => b !== opt.value);
                            updateTask(agentIdx, taskIdx, "badges", newBadges);
                          }} />
                        <Badge value={opt.value} />
                      </label>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="flex items-center gap-2 text-xs">
                    <input type="checkbox" checked={task.needsHumanConfirm}
                      onChange={(e) => updateTask(agentIdx, taskIdx, "needsHumanConfirm", e.target.checked)} />
                    <span className="font-medium">Human 확인 필요</span>
                  </label>
                </div>
                <button onClick={() => deleteTask(agentIdx, taskIdx)}
                  className="flex items-center gap-2 text-sm text-red-600 hover:text-red-800">
                  <Trash2 className="h-4 w-4" /> 삭제
                </button>
              </div>
            );
          })()}
        </EditModal>
      )}

      {/* Human Task 편집 */}
      {editingHuman !== null && (
        <EditModal title="HR 담당자 Task 편집" onClose={() => setEditingHuman(null)}>
          {(() => {
            const ht = data.humanTasks[editingHuman];
            if (!ht) return null;
            return (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">제목</label>
                  <input className="w-full rounded-lg border px-3 py-2 text-sm" value={ht.title}
                    onChange={(e) => update((d) => {
                      d.humanTasks = [...d.humanTasks];
                      d.humanTasks[editingHuman] = { ...ht, title: e.target.value };
                      return d;
                    })} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">설명</label>
                  <input className="w-full rounded-lg border px-3 py-2 text-sm" value={ht.description}
                    onChange={(e) => update((d) => {
                      d.humanTasks = [...d.humanTasks];
                      d.humanTasks[editingHuman] = { ...ht, description: e.target.value };
                      return d;
                    })} />
                </div>
                <button onClick={() => deleteHumanTask(editingHuman)}
                  className="flex items-center gap-2 text-sm text-red-600 hover:text-red-800">
                  <Trash2 className="h-4 w-4" /> 삭제
                </button>
              </div>
            );
          })()}
        </EditModal>
      )}
    </div>
  );
}
