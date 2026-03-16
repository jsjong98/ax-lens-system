"""
tobe_generator.py — To-Be Workflow + Agent 정의 자동 생성기

As-Is 워크플로우 + 분류 결과를 기반으로:
  1. Junior AI Agent 그루핑
  2. Senior AI Agent 정의
  3. AI+Human 태스크 분할
  4. To-Be Workflow (React Flow JSON) 초안 생성
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from workflow_parser import WorkflowSheet, ExecutionStep, WorkflowNode


# ── 데이터 모델 ───────────────────────────────────────────────────────────────

@dataclass
class AgentTask:
    """Agent가 처리하는 개별 태스크."""
    task_id: str
    label: str
    classification: str     # "AI 수행 가능" | "AI + Human" | "인간 수행 필요"
    reason: str = ""
    ai_part: str = ""       # AI+Human일 때 AI가 하는 부분
    human_part: str = ""    # AI+Human일 때 사람이 하는 부분
    hybrid_note: str = ""
    node_id: str = ""       # 원본 워크플로우 노드 ID


@dataclass
class JuniorAgent:
    """순차 파이프라인을 처리하는 Junior AI Agent."""
    id: str
    name: str
    tasks: list[AgentTask] = field(default_factory=list)
    technique: str = ""     # LLM, RAG, Clustering, 규칙 기반 등
    input_types: str = ""
    output_types: str = ""
    description: str = ""

    @property
    def task_count(self) -> int:
        return len(self.tasks)


@dataclass
class HumanStep:
    """사람이 직접 수행하는 스텝."""
    id: str
    task_id: str
    label: str
    reason: str = ""
    is_hybrid_human_part: bool = False  # AI+Human의 Human 파트인지
    node_id: str = ""


@dataclass
class SeniorAgent:
    """전체를 관장하는 Senior AI Agent (과제당 1개)."""
    id: str
    name: str
    junior_agents: list[JuniorAgent] = field(default_factory=list)
    human_steps: list[HumanStep] = field(default_factory=list)
    orchestration_flow: list[dict] = field(default_factory=list)
    description: str = ""

    @property
    def total_junior_tasks(self) -> int:
        return sum(j.task_count for j in self.junior_agents)


@dataclass
class ToBeWorkflow:
    """To-Be Workflow 전체."""
    senior_agent: SeniorAgent
    execution_steps: list[dict] = field(default_factory=list)
    react_flow: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)


# ── To-Be 생성 ────────────────────────────────────────────────────────────────

def generate_tobe(
    as_is_sheet: WorkflowSheet,
    classification_results: dict[str, dict],
    process_name: str = "",
) -> ToBeWorkflow:
    """
    As-Is 워크플로우 + 분류 결과 → To-Be Workflow 생성.

    classification_results: {
        task_id: {
            "label": "AI 수행 가능" | "AI + Human" | "인간 수행 필요",
            "reason": "...",
            "hybrid_note": "...",  # AI+Human일 때
            "input_types": "...",
            "output_types": "...",
        }
    }
    """
    # 1. 노드별 분류 결과 매핑
    classified_nodes = _map_classifications(as_is_sheet, classification_results)

    # 2. AI+Human 태스크 분할
    split_tasks = _split_hybrid_tasks(classified_nodes)

    # 3. Junior Agent 그루핑
    junior_agents = _group_junior_agents(
        as_is_sheet, split_tasks, classification_results
    )

    # 4. Human 스텝 추출
    human_steps = _extract_human_steps(split_tasks)

    # 5. Senior Agent 정의 — 기존 노드가 아닌 새로 생성되는 오케스트레이터
    senior = SeniorAgent(
        id="senior-ai-1",
        name=f"{process_name or as_is_sheet.name} Senior AI Orchestrator",
        junior_agents=junior_agents,
        human_steps=human_steps,
        description=(
            f"신규 생성된 오케스트레이터 Agent입니다. "
            f"{len(junior_agents)}개 Junior AI Agent의 실행 순서를 관리하고, "
            f"각 Agent 간 산출물 정합성을 검증하며, "
            f"Human 수행 단계({len(human_steps)}건)로의 핸드오프를 제어합니다. "
            f"이 Agent는 As-Is 워크플로우에 존재하지 않으며, "
            f"To-Be 자동화 아키텍처를 위해 새로 정의됩니다."
        ),
    )

    # 6. 오케스트레이션 흐름 정의
    senior.orchestration_flow = _build_orchestration_flow(
        as_is_sheet, junior_agents, human_steps
    )

    # 7. 실행 스텝 생성
    execution_steps = _build_execution_steps(senior)

    # 8. React Flow JSON 생성
    react_flow = _generate_react_flow(senior, as_is_sheet)

    # 9. 요약 정보
    summary = _build_summary(senior, classified_nodes)

    return ToBeWorkflow(
        senior_agent=senior,
        execution_steps=execution_steps,
        react_flow=react_flow,
        summary=summary,
    )


# ── 내부 함수 ─────────────────────────────────────────────────────────────────

def _map_classifications(
    sheet: WorkflowSheet,
    results: dict[str, dict],
) -> list[dict]:
    """워크플로우 노드에 분류 결과를 매핑합니다."""
    classified = []
    for node in sorted(sheet.nodes.values(), key=lambda n: (n.y, n.x)):
        if node.level not in ("L4", "L5"):
            continue

        # task_id로 매칭 시도
        cr = results.get(node.task_id, {})
        if not cr:
            # node label로 매칭 시도
            for tid, r in results.items():
                if r.get("task_name", "") == node.label:
                    cr = r
                    break

        classified.append({
            "node_id": node.id,
            "task_id": node.task_id,
            "label": node.label,
            "level": node.level,
            "classification": cr.get("label", "미분류"),
            "reason": cr.get("reason", ""),
            "hybrid_note": cr.get("hybrid_note", ""),
            "input_types": cr.get("input_types", ""),
            "output_types": cr.get("output_types", ""),
        })

    return classified


def _split_hybrid_tasks(classified_nodes: list[dict]) -> list[dict]:
    """
    AI+Human 태스크를 AI 파트와 Human 파트로 분할합니다.

    hybrid_note 형식: "[패턴 A|B|C] AI 파트: ~~ / Human 파트: ~~"
    """
    split = []
    for node in classified_nodes:
        if node["classification"] == "AI + Human":
            ai_part, human_part = _parse_hybrid_note(node["hybrid_note"])
            # AI 파트
            split.append({
                **node,
                "split_type": "ai_part",
                "split_label": f"{node['label']} (AI)",
                "split_description": ai_part or "데이터 수집/분석/초안 작성",
            })
            # Human 파트
            split.append({
                **node,
                "split_type": "human_part",
                "split_label": f"{node['label']} (Human)",
                "split_description": human_part or "검토/승인/최종 판단",
            })
        else:
            split.append({
                **node,
                "split_type": "original",
                "split_label": node["label"],
                "split_description": "",
            })

    return split


def _parse_hybrid_note(note: str) -> tuple[str, str]:
    """hybrid_note에서 AI 파트와 Human 파트를 분리합니다."""
    ai_part = ""
    human_part = ""

    if not note:
        return ai_part, human_part

    # "AI 파트: XXX / Human 파트: YYY" 패턴
    ai_match = re.search(r'AI\s*파트[:\s]*([^/]+)', note)
    human_match = re.search(r'Human\s*파트[:\s]*(.+)', note)

    if ai_match:
        ai_part = ai_match.group(1).strip()
    if human_match:
        human_part = human_match.group(1).strip()

    return ai_part, human_part


def _group_junior_agents(
    sheet: WorkflowSheet,
    split_tasks: list[dict],
    classification_results: dict[str, dict],
) -> list[JuniorAgent]:
    """
    AI 수행 가능 + AI+Human의 AI 파트를 Junior Agent로 그루핑합니다.

    그루핑 전략 (같은 L4 내에서 연속 AI L5 태스크를 묶음):
      1. L5 태스크를 상위 L4 ID별로 그루핑
      2. 각 L4 내에서 실행 순서대로 정렬
      3. 연속된 AI 가능 L5 태스크를 하나의 Junior Agent로 묶음
      4. Human 태스크가 중간에 끼면 그룹을 끊고 새 그룹 시작
      5. L4 레벨 독립 AI 태스크는 단독 Junior Agent
    """
    if not split_tasks:
        return []

    # ── 실행 순서 매핑 ──
    node_to_step: dict[str, int] = {}
    for step in sheet.execution_order:
        for nid in step.node_ids:
            node_to_step[nid] = step.step_number

    def _task_sort_key(task: dict) -> tuple:
        nid = task.get("node_id", "")
        step_num = node_to_step.get(nid, 9999)
        parts = re.split(r'(\d+)', task.get("task_id", ""))
        natural = tuple(int(p) if p.isdigit() else p for p in parts if p)
        return (step_num, natural)

    def _is_ai_capable(task: dict) -> bool:
        cls = task["classification"]
        split_type = task.get("split_type", "original")
        if cls == "AI 수행 가능":
            return True
        if cls == "AI + Human" and split_type == "ai_part":
            return True
        return False

    def _l4_id_of(task: dict) -> str:
        """L5 태스크의 상위 L4 ID를 추출 (예: 1.1.1.2.3 → 1.1.1.2)"""
        tid = task.get("task_id", "")
        parts = tid.split(".")
        if len(parts) >= 4:
            return ".".join(parts[:4])
        return tid

    # ── L4별로 L5 태스크 그루핑 ──
    l4_groups: dict[str, list[dict]] = defaultdict(list)
    standalone: list[dict] = []  # L4 레벨 독립 태스크

    for task in split_tasks:
        if task.get("level") == "L5":
            l4_id = _l4_id_of(task)
            l4_groups[l4_id].append(task)
        elif _is_ai_capable(task):
            standalone.append(task)

    # ── 각 L4 내에서 연속 AI 태스크 묶기 ──
    all_groups: list[list[dict]] = []

    for l4_id in sorted(l4_groups.keys(), key=lambda k: _task_sort_key(l4_groups[k][0])):
        tasks_in_l4 = sorted(l4_groups[l4_id], key=_task_sort_key)
        current_group: list[dict] = []

        for task in tasks_in_l4:
            if _is_ai_capable(task):
                current_group.append(task)
            else:
                # Human 태스크를 만나면 현재 그룹 확정, 새 그룹 시작
                if current_group:
                    all_groups.append(current_group)
                    current_group = []

        if current_group:
            all_groups.append(current_group)

    # ── Junior Agent 생성 ──
    agents: list[JuniorAgent] = []
    agent_idx = 1

    # L4 내 그루핑된 Agent 생성
    for group_tasks in all_groups:
        agent_tasks = [
            AgentTask(
                task_id=t["task_id"],
                label=t.get("split_label", t["label"]),
                classification=t["classification"],
                reason=t.get("reason", ""),
                ai_part=t.get("split_description", ""),
                node_id=t["node_id"],
            )
            for t in group_tasks
        ]

        technique = _infer_technique(group_tasks, classification_results)

        first_label = group_tasks[0]["label"].split("(")[0].strip()
        if len(group_tasks) > 1:
            name = f"Agent {agent_idx}: {first_label} 외 {len(group_tasks)-1}건 파이프라인"
        else:
            name = f"Agent {agent_idx}: {first_label}"

        agents.append(JuniorAgent(
            id=f"junior-ai-{agent_idx}",
            name=name,
            tasks=agent_tasks,
            technique=technique,
            input_types=group_tasks[0].get("input_types", ""),
            output_types=group_tasks[-1].get("output_types", ""),
            description=f"{len(agent_tasks)}개 L5 태스크의 순차 처리 파이프라인",
        ))
        agent_idx += 1

    # L4 레벨 독립 AI 태스크
    for task in standalone:
        agent_tasks = [
            AgentTask(
                task_id=task["task_id"],
                label=task.get("split_label", task["label"]),
                classification=task["classification"],
                reason=task.get("reason", ""),
                ai_part=task.get("split_description", ""),
                node_id=task["node_id"],
            )
        ]
        technique = _infer_technique([task], classification_results)

        agents.append(JuniorAgent(
            id=f"junior-ai-{agent_idx}",
            name=f"Agent {agent_idx}: {task['label'].split('(')[0].strip()}",
            tasks=agent_tasks,
            technique=technique,
            input_types=task.get("input_types", ""),
            output_types=task.get("output_types", ""),
            description="단독 L4 태스크 처리",
        ))
        agent_idx += 1

    return agents


def _infer_technique(
    tasks: list[dict],
    classification_results: dict[str, dict],
) -> str:
    """태스크 특성으로 AI 기법을 추론합니다."""
    techniques = []

    all_text = " ".join(t.get("label", "") + " " + t.get("reason", "") for t in tasks)
    lower = all_text.lower()

    if any(kw in lower for kw in ["분석", "통계", "데이터", "수치"]):
        techniques.append("데이터 분석")
    if any(kw in lower for kw in ["수집", "조사", "검색", "외부"]):
        techniques.append("RAG")
    if any(kw in lower for kw in ["작성", "생성", "초안", "보고서"]):
        techniques.append("LLM")
    if any(kw in lower for kw in ["분류", "판단", "규칙"]):
        techniques.append("규칙 기반")
    if any(kw in lower for kw in ["유사", "매칭", "추천"]):
        techniques.append("임베딩 유사도")
    if any(kw in lower for kw in ["군집", "그룹", "클러스터"]):
        techniques.append("Clustering")

    if not techniques:
        techniques.append("LLM")

    return " + ".join(techniques)


def _extract_human_steps(split_tasks: list[dict]) -> list[HumanStep]:
    """인간 수행 필요 태스크 + AI+Human의 Human 파트를 추출합니다."""
    steps = []
    step_idx = 1

    for task in split_tasks:
        if task["classification"] == "인간 수행 필요":
            steps.append(HumanStep(
                id=f"human-{step_idx}",
                task_id=task["task_id"],
                label=task["label"],
                reason=task.get("reason", ""),
                is_hybrid_human_part=False,
                node_id=task["node_id"],
            ))
            step_idx += 1
        elif (task["classification"] == "AI + Human"
              and task.get("split_type") == "human_part"):
            steps.append(HumanStep(
                id=f"human-{step_idx}",
                task_id=task["task_id"],
                label=task.get("split_label", task["label"]),
                reason=task.get("split_description", ""),
                is_hybrid_human_part=True,
                node_id=task["node_id"],
            ))
            step_idx += 1

    return steps


def _build_orchestration_flow(
    sheet: WorkflowSheet,
    junior_agents: list[JuniorAgent],
    human_steps: list[HumanStep],
) -> list[dict]:
    """Senior AI의 오케스트레이션 흐름을 정의합니다."""
    flow = []

    # 모든 태스크의 node_id → agent/human 매핑
    node_to_agent: dict[str, str] = {}
    for agent in junior_agents:
        for task in agent.tasks:
            node_to_agent[task.node_id] = agent.id
    for hs in human_steps:
        node_to_agent[hs.node_id] = hs.id

    # 실행 순서를 따라가며 오케스트레이션 스텝 생성
    for exec_step in sheet.execution_order:
        step_agents = set()
        for nid in exec_step.node_ids:
            if nid in node_to_agent:
                step_agents.add(node_to_agent[nid])

        if not step_agents:
            continue

        flow.append({
            "step": exec_step.step_number,
            "is_parallel": exec_step.is_parallel,
            "agents": sorted(step_agents),
        })

    return flow


def _build_execution_steps(senior: SeniorAgent) -> list[dict]:
    """To-Be 실행 스텝을 생성합니다."""
    steps = []
    step_num = 1

    for flow_step in senior.orchestration_flow:
        agents_in_step = []
        for agent_id in flow_step["agents"]:
            # Junior Agent 찾기
            junior = next(
                (j for j in senior.junior_agents if j.id == agent_id), None
            )
            if junior:
                agents_in_step.append({
                    "type": "junior_ai",
                    "agent_id": junior.id,
                    "agent_name": junior.name,
                    "technique": junior.technique,
                    "tasks": [
                        {"task_id": t.task_id, "label": t.label}
                        for t in junior.tasks
                    ],
                })
                continue

            # Human 스텝 찾기
            human = next(
                (h for h in senior.human_steps if h.id == agent_id), None
            )
            if human:
                agents_in_step.append({
                    "type": "human",
                    "step_id": human.id,
                    "label": human.label,
                    "is_hybrid_part": human.is_hybrid_human_part,
                    "reason": human.reason,
                })

        if agents_in_step:
            steps.append({
                "step": step_num,
                "is_parallel": flow_step["is_parallel"],
                "actors": agents_in_step,
            })
            step_num += 1

    return steps


# ── React Flow 생성 ───────────────────────────────────────────────────────────

def _generate_react_flow(
    senior: SeniorAgent,
    as_is_sheet: WorkflowSheet,
) -> dict:
    """To-Be 워크플로우를 React Flow 호환 JSON으로 생성합니다."""
    nodes = []
    edges = []

    # Swim Lane 정의
    lanes = ["Senior AI", "Junior AI", "Human"]

    # Y 좌표 계산을 위한 레이아웃
    LANE_HEIGHT = 300
    NODE_GAP_X = 250
    NODE_GAP_Y = 150
    START_X = 200
    START_Y = 50

    y_offsets = {
        "senior": START_Y,
        "junior": START_Y + LANE_HEIGHT,
        "human": START_Y + LANE_HEIGHT * 2,
    }

    node_idx = 0
    current_x = START_X

    # Senior AI 노드 (최상단)
    senior_node_id = "tobe-senior"
    nodes.append({
        "id": senior_node_id,
        "type": "l3",
        "position": {"x": START_X, "y": y_offsets["senior"]},
        "data": {
            "label": senior.name,
            "level": "Senior AI",
            "id": senior.id,
            "description": senior.description,
            "agentType": "senior",
        },
    })

    prev_step_node_ids: list[str] = [senior_node_id]

    # 오케스트레이션 흐름에 따라 노드 배치
    for step_idx, flow_step in enumerate(senior.orchestration_flow):
        step_node_ids: list[str] = []
        branch_x = current_x

        for agent_id in flow_step["agents"]:
            # Junior Agent 노드
            junior = next(
                (j for j in senior.junior_agents if j.id == agent_id), None
            )
            if junior:
                jnode_id = f"tobe-{junior.id}"
                nodes.append({
                    "id": jnode_id,
                    "type": "l4",
                    "position": {"x": branch_x, "y": y_offsets["junior"]},
                    "data": {
                        "label": junior.name,
                        "level": "Junior AI",
                        "id": junior.id,
                        "description": f"기법: {junior.technique}",
                        "agentType": "junior",
                        "technique": junior.technique,
                        "taskCount": junior.task_count,
                    },
                })
                step_node_ids.append(jnode_id)

                # Junior Agent 하위 태스크 노드
                for ti, task in enumerate(junior.tasks):
                    task_node_id = f"tobe-task-{task.task_id}"
                    nodes.append({
                        "id": task_node_id,
                        "type": "l5",
                        "position": {
                            "x": branch_x + 30,
                            "y": y_offsets["junior"] + 80 + ti * 50,
                        },
                        "data": {
                            "label": task.label,
                            "level": "L5",
                            "id": task.task_id,
                            "description": task.ai_part,
                            "classification": task.classification,
                        },
                    })
                    # Junior → Task 엣지
                    edges.append({
                        "id": f"e-{jnode_id}-{task_node_id}",
                        "source": jnode_id,
                        "target": task_node_id,
                        "type": "smoothstep",
                        "animated": False,
                        "style": {"stroke": "#f2a0af", "strokeWidth": 1.5},
                        "markerEnd": {"type": "arrowclosed", "color": "#f2a0af"},
                    })

                branch_x += NODE_GAP_X
                continue

            # Human 스텝 노드
            human = next(
                (h for h in senior.human_steps if h.id == agent_id), None
            )
            if human:
                hnode_id = f"tobe-{human.id}"
                nodes.append({
                    "id": hnode_id,
                    "type": "l4",
                    "position": {"x": branch_x, "y": y_offsets["human"]},
                    "data": {
                        "label": human.label,
                        "level": "Human",
                        "id": human.id,
                        "description": human.reason,
                        "agentType": "human",
                        "isHybridPart": human.is_hybrid_human_part,
                    },
                })
                step_node_ids.append(hnode_id)
                branch_x += NODE_GAP_X

        # Senior → 각 스텝의 첫 노드 엣지
        for snid in step_node_ids:
            # 이전 스텝 → 현재 스텝 엣지
            for prev_id in prev_step_node_ids:
                edges.append({
                    "id": f"e-{prev_id}-{snid}",
                    "source": prev_id,
                    "target": snid,
                    "type": "smoothstep",
                    "animated": True,
                    "style": {"stroke": "#a62121", "strokeWidth": 2.5},
                    "markerEnd": {"type": "arrowclosed", "color": "#a62121"},
                    "label": "기동" if prev_id == senior_node_id else "",
                })

        prev_step_node_ids = step_node_ids
        current_x = branch_x + NODE_GAP_X // 2

    return {
        "version": "1.0",
        "type": "tobe",
        "nodes": nodes,
        "edges": edges,
        "lanes": lanes,
    }


# ── 요약 ──────────────────────────────────────────────────────────────────────

def _build_summary(
    senior: SeniorAgent,
    classified_nodes: list[dict],
) -> dict:
    """To-Be 워크플로우 요약 정보."""
    total = len(classified_nodes)
    ai_count = sum(1 for n in classified_nodes if n["classification"] == "AI 수행 가능")
    hybrid_count = sum(1 for n in classified_nodes if n["classification"] == "AI + Human")
    human_count = sum(1 for n in classified_nodes if n["classification"] == "인간 수행 필요")

    return {
        "process_name": senior.name,
        "total_tasks": total,
        "ai_tasks": ai_count,
        "hybrid_tasks": hybrid_count,
        "human_tasks": human_count,
        "automation_rate": round((ai_count + hybrid_count * 0.5) / max(total, 1) * 100, 1),
        "junior_agent_count": len(senior.junior_agents),
        "junior_agents": [
            {
                "id": j.id,
                "name": j.name,
                "technique": j.technique,
                "task_count": j.task_count,
                "tasks": [
                    {"task_id": t.task_id, "label": t.label}
                    for t in j.tasks
                ],
            }
            for j in senior.junior_agents
        ],
        "human_step_count": len(senior.human_steps),
        "human_steps": [
            {
                "id": h.id,
                "label": h.label,
                "is_hybrid_part": h.is_hybrid_human_part,
                "reason": h.reason,
            }
            for h in senior.human_steps
        ],
        "senior_agent": {
            "id": senior.id,
            "name": senior.name,
            "description": senior.description,
        },
    }
