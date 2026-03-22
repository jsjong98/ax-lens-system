"""
new_workflow_generator.py — Excel L5 Task 기반 AI 워크플로우 설계 초안 생성기

엑셀 파일만 입력으로 받아서:
  1. L5 Task의 Input/Output, 업무 성격을 분석
  2. 어떤 AI가 어떻게 들어가야 할지 초안 설계
  3. AI 에이전트별 역할, 기법, 실행 흐름 제안

모든 Task는 L5 Task로 취급합니다 (Orchestration 포함).
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

from models import Task


# ── 데이터 모델 ───────────────────────────────────────────────────────────────

@dataclass
class AssignedTask:
    """AI 에이전트에 배정된 L5 Task."""
    task_id: str
    task_name: str
    l4: str
    l3: str
    ai_role: str          # AI가 담당하는 역할
    human_role: str       # 사람이 담당하는 역할 (없으면 빈 문자열)
    input_data: list[str] = field(default_factory=list)
    output_data: list[str] = field(default_factory=list)
    automation_level: str = "Human-in-Loop"  # "Full-Auto" | "Human-in-Loop" | "Human-Supervised"


@dataclass
class AIAgent:
    """AI 워크플로우 내 단일 에이전트."""
    agent_id: str
    agent_name: str
    agent_type: str       # 예: "Document Processing AI", "Data Analysis AI"
    ai_technique: str     # 예: "LLM", "OCR + LLM", "RPA", "ML Model"
    description: str
    automation_level: str = "Human-in-Loop"
    assigned_tasks: list[AssignedTask] = field(default_factory=list)

    @property
    def task_count(self) -> int:
        return len(self.assigned_tasks)


@dataclass
class ExecutionStep:
    """실행 플로우 단계."""
    step: int
    step_name: str
    step_type: str        # "sequential" | "parallel"
    description: str
    agent_ids: list[str] = field(default_factory=list)
    task_ids: list[str] = field(default_factory=list)


@dataclass
class NewWorkflowResult:
    """New Workflow 생성 결과."""
    blueprint_summary: str
    process_name: str
    total_tasks: int
    full_auto_count: int
    human_in_loop_count: int
    human_supervised_count: int
    agents: list[AIAgent] = field(default_factory=list)
    execution_flow: list[ExecutionStep] = field(default_factory=list)


# ── 시스템 프롬프트 ───────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
당신은 AI 워크플로우 설계 전문가입니다.
HR 업무 프로세스의 L5 Task 목록을 분석하여, 각 업무에 어떤 AI 기술이 어떻게 적용되어야 하는지 설계 초안을 작성합니다.

## 역할
- 엑셀에서 추출된 L5 Task 정보를 분석하여 AI 통합 설계 초안을 제안합니다
- 모든 Task는 L5 Task로 취급합니다 (Orchestration 포함)
- 각 Task가 어떤 AI 에이전트에 배정되어야 하는지, 어떤 AI 기법이 적합한지 판단합니다

## AI 에이전트 유형 (예시, 실제 업무에 맞게 조정)
- Document Processing AI: 문서 작성, 양식 처리, 보고서 생성
- Data Analysis AI: 데이터 집계, 통계 분석, 패턴 인식
- Information Retrieval AI: 정보 검색, 조회, 확인
- Communication AI: 이메일/공지 초안 작성, 알림 발송
- Decision Support AI: 판단 보조, 조건 검토, 기준 적용
- Process Automation AI: 시스템 입력, 반복 처리, 규칙 기반 자동화
- Scheduling AI: 일정 관리, 조율, 배분

## AI 기법 유형
- LLM (대형 언어 모델): 문서 이해, 생성, 요약, 분류
- RAG (검색 증강 생성): 내부 규정/데이터 기반 답변 생성
- RPA (로봇 프로세스 자동화): 반복적 시스템 작업 자동화
- OCR + LLM: 문서 스캔 후 내용 분석
- ML Model: 예측, 패턴 분류, 이상 탐지
- 규칙 기반 (Rule Engine): 명확한 조건 분기 처리
- API 연동: 시스템 간 데이터 자동 연계

## 자동화 수준 정의
- Full-Auto: AI가 사람 개입 없이 전 과정을 처리
- Human-in-Loop: AI가 초안/분석을 제공하고 사람이 최종 확인/승인
- Human-Supervised: AI는 보조 역할, 사람이 주도하고 AI가 지원

## 출력 규칙
- 반드시 JSON만 출력하세요 (마크다운 코드 블록 없음)
- 유사한 성격의 Task는 하나의 에이전트로 묶으세요 (최대 7개 에이전트)
- 각 Task는 반드시 하나의 에이전트에 배정되어야 합니다
- 실행 흐름은 논리적 순서로 구성하세요
- 한국어로 작성하세요
"""


def _build_user_prompt(tasks: list[Task], process_name: str) -> str:
    """LLM에 전달할 사용자 프롬프트 생성."""
    lines = [
        f"프로세스명: {process_name}",
        f"총 L5 Task 수: {len(tasks)}개",
        "",
        "## L5 Task 목록",
        "",
    ]

    for t in tasks:
        pain_points = []
        if t.pain_time:       pain_points.append("시간/속도")
        if t.pain_accuracy:   pain_points.append("정확성")
        if t.pain_repetition: pain_points.append("반복/수작업")
        if t.pain_data:       pain_points.append("정보/데이터")
        if t.pain_system:     pain_points.append("시스템/도구")
        if t.pain_communication: pain_points.append("의사소통")

        output_types = []
        if t.output_system:   output_types.append("시스템 반영")
        if t.output_document: output_types.append("문서/보고서")
        if t.output_communication: output_types.append("커뮤니케이션")
        if t.output_decision: output_types.append("의사결정")

        logic_types = []
        if t.logic_rule_based:     logic_types.append("규칙 기반")
        if t.logic_human_judgment: logic_types.append("사람 판단")
        if t.logic_mixed:          logic_types.append("혼합")

        lines.append(f"### [{t.id}] {t.name}")
        lines.append(f"- 계층: {t.l2} > {t.l3} > {t.l4}")
        if t.description:
            lines.append(f"- 업무 설명: {t.description}")
        if t.performer:
            lines.append(f"- 수행 주체: {t.performer}")
        if pain_points:
            lines.append(f"- Pain Point: {', '.join(pain_points)}")
        if output_types:
            lines.append(f"- Output 유형: {', '.join(output_types)}")
        if logic_types:
            lines.append(f"- 판단 로직: {', '.join(logic_types)}")
        lines.append("")

    lines += [
        "",
        "## 요청사항",
        "위 L5 Task들을 분석하여 AI 워크플로우 설계 초안을 JSON 형식으로 작성해주세요.",
        "",
        "출력 형식:",
        """
{
  "blueprint_summary": "전체 AI 통합 설계 요약 (3~5문장)",
  "process_name": "프로세스명",
  "full_auto_count": 정수,
  "human_in_loop_count": 정수,
  "human_supervised_count": 정수,
  "agents": [
    {
      "agent_id": "agent_1",
      "agent_name": "에이전트 명 (한국어)",
      "agent_type": "에이전트 유형",
      "ai_technique": "사용할 AI 기법",
      "description": "에이전트 역할 설명",
      "automation_level": "Full-Auto | Human-in-Loop | Human-Supervised",
      "assigned_tasks": [
        {
          "task_id": "L5 Task ID",
          "task_name": "Task 명",
          "l4": "L4 Activity 명",
          "l3": "L3 Unit Process 명",
          "ai_role": "AI가 담당하는 구체적 역할",
          "human_role": "사람이 담당하는 역할 (Full-Auto면 빈 문자열)",
          "input_data": ["입력 데이터/문서 유형 목록"],
          "output_data": ["출력 결과물 유형 목록"],
          "automation_level": "Full-Auto | Human-in-Loop | Human-Supervised"
        }
      ]
    }
  ],
  "execution_flow": [
    {
      "step": 1,
      "step_name": "단계 이름",
      "step_type": "sequential | parallel",
      "description": "단계 설명",
      "agent_ids": ["agent_1"],
      "task_ids": ["Task ID 목록"]
    }
  ]
}
""",
    ]
    return "\n".join(lines)


# ── JSON 파싱 헬퍼 ────────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """LLM 응답에서 JSON 객체를 추출합니다."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    # JSON 블록만 추출 (앞뒤 텍스트 제거)
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        text = text[start:end]
    return json.loads(text)


def _parse_result(data: dict, tasks: list[Task]) -> NewWorkflowResult:
    """LLM 응답 dict를 NewWorkflowResult로 변환합니다."""
    agents = []
    for a in data.get("agents", []):
        assigned = []
        for t in a.get("assigned_tasks", []):
            assigned.append(AssignedTask(
                task_id=t.get("task_id", ""),
                task_name=t.get("task_name", ""),
                l4=t.get("l4", ""),
                l3=t.get("l3", ""),
                ai_role=t.get("ai_role", ""),
                human_role=t.get("human_role", ""),
                input_data=t.get("input_data", []),
                output_data=t.get("output_data", []),
                automation_level=t.get("automation_level", "Human-in-Loop"),
            ))
        agents.append(AIAgent(
            agent_id=a.get("agent_id", ""),
            agent_name=a.get("agent_name", ""),
            agent_type=a.get("agent_type", ""),
            ai_technique=a.get("ai_technique", ""),
            description=a.get("description", ""),
            automation_level=a.get("automation_level", "Human-in-Loop"),
            assigned_tasks=assigned,
        ))

    flow = []
    for s in data.get("execution_flow", []):
        flow.append(ExecutionStep(
            step=s.get("step", 0),
            step_name=s.get("step_name", ""),
            step_type=s.get("step_type", "sequential"),
            description=s.get("description", ""),
            agent_ids=s.get("agent_ids", []),
            task_ids=s.get("task_ids", []),
        ))

    return NewWorkflowResult(
        blueprint_summary=data.get("blueprint_summary", ""),
        process_name=data.get("process_name", ""),
        total_tasks=len(tasks),
        full_auto_count=int(data.get("full_auto_count", 0)),
        human_in_loop_count=int(data.get("human_in_loop_count", 0)),
        human_supervised_count=int(data.get("human_supervised_count", 0)),
        agents=agents,
        execution_flow=flow,
    )


# ── 규칙 기반 Fallback ────────────────────────────────────────────────────────

def _fallback_generate(tasks: list[Task], process_name: str) -> NewWorkflowResult:
    """LLM 호출 실패 시 규칙 기반으로 간단한 설계 초안을 생성합니다."""
    from collections import defaultdict

    # L3 기준으로 태스크 그루핑
    l3_groups: dict[str, list[Task]] = defaultdict(list)
    for t in tasks:
        l3_groups[t.l3].append(t)

    agents: list[AIAgent] = []
    flow: list[ExecutionStep] = []

    for idx, (l3_name, group) in enumerate(l3_groups.items(), start=1):
        agent_id = f"agent_{idx}"
        assigned = []
        for t in group:
            # 로직 유형 기반 자동화 수준 결정
            if t.logic_rule_based and not t.logic_human_judgment:
                level = "Full-Auto"
            elif t.logic_human_judgment and not t.logic_rule_based:
                level = "Human-Supervised"
            else:
                level = "Human-in-Loop"

            # 아웃풋 기반 AI 기법 추론
            technique = "LLM"
            if t.output_system:
                technique = "RPA + LLM"
            elif t.output_document:
                technique = "LLM"
            elif t.output_decision:
                technique = "Decision Support AI (LLM)"

            assigned.append(AssignedTask(
                task_id=t.id,
                task_name=t.name,
                l4=t.l4,
                l3=t.l3,
                ai_role=f"{t.name} 자동화 처리",
                human_role="" if level == "Full-Auto" else "결과 검토 및 승인",
                input_data=["업무 데이터"],
                output_data=["처리 결과"],
                automation_level=level,
            ))

        agents.append(AIAgent(
            agent_id=agent_id,
            agent_name=f"{l3_name} AI 에이전트",
            agent_type="Process Automation AI",
            ai_technique=technique,
            description=f"{l3_name} 관련 L5 Task 자동화",
            automation_level="Human-in-Loop",
            assigned_tasks=assigned,
        ))

        flow.append(ExecutionStep(
            step=idx,
            step_name=l3_name,
            step_type="sequential",
            description=f"{l3_name} 처리 단계",
            agent_ids=[agent_id],
            task_ids=[t.id for t in group],
        ))

    all_tasks = [t for g in l3_groups.values() for t in g]
    full_auto = sum(1 for a in agents for t in a.assigned_tasks if t.automation_level == "Full-Auto")
    hil = sum(1 for a in agents for t in a.assigned_tasks if t.automation_level == "Human-in-Loop")
    hsup = sum(1 for a in agents for t in a.assigned_tasks if t.automation_level == "Human-Supervised")

    return NewWorkflowResult(
        blueprint_summary=f"{process_name} 프로세스에 대한 AI 통합 설계 초안입니다. "
                          f"총 {len(tasks)}개 L5 Task를 {len(agents)}개 AI 에이전트로 구성합니다.",
        process_name=process_name,
        total_tasks=len(tasks),
        full_auto_count=full_auto,
        human_in_loop_count=hil,
        human_supervised_count=hsup,
        agents=agents,
        execution_flow=flow,
    )


# ── 메인 생성 함수 ─────────────────────────────────────────────────────────────

async def generate_new_workflow(
    tasks: list[Task],
    process_name: str,
    api_key: str = "",
    model: str = "claude-sonnet-4-6",
    use_openai: bool = False,
    openai_api_key: str = "",
    openai_model: str = "gpt-5.4",
) -> NewWorkflowResult:
    """
    L5 Task 목록을 분석하여 AI 워크플로우 설계 초안을 생성합니다.

    Anthropic Claude를 우선 사용하며, 실패 시 OpenAI로 fallback,
    둘 다 없으면 규칙 기반 fallback을 사용합니다.
    """
    if not tasks:
        return NewWorkflowResult(
            blueprint_summary="분석할 Task가 없습니다.",
            process_name=process_name,
            total_tasks=0,
            full_auto_count=0,
            human_in_loop_count=0,
            human_supervised_count=0,
        )

    user_prompt = _build_user_prompt(tasks, process_name)

    # Anthropic Claude 시도
    anthropic_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=anthropic_key)
            response = await client.messages.create(
                model=model,
                max_tokens=8192,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw = response.content[0].text
            data = _extract_json(raw)
            return _parse_result(data, tasks)
        except Exception as e:
            print(f"[new_workflow] Anthropic 호출 실패: {e}")

    # OpenAI fallback
    openai_key = openai_api_key or os.getenv("OPENAI_API_KEY", "")
    if openai_key:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=openai_key)
            response = await client.chat.completions.create(
                model=openai_model,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            return _parse_result(data, tasks)
        except Exception as e:
            print(f"[new_workflow] OpenAI 호출 실패: {e}")

    # 규칙 기반 fallback
    print("[new_workflow] API 키 없음 — 규칙 기반 fallback 사용")
    return _fallback_generate(tasks, process_name)


def result_to_dict(result: NewWorkflowResult) -> dict[str, Any]:
    """NewWorkflowResult를 JSON 직렬화 가능한 dict로 변환합니다."""
    return {
        "blueprint_summary": result.blueprint_summary,
        "process_name": result.process_name,
        "total_tasks": result.total_tasks,
        "full_auto_count": result.full_auto_count,
        "human_in_loop_count": result.human_in_loop_count,
        "human_supervised_count": result.human_supervised_count,
        "agents": [
            {
                "agent_id": a.agent_id,
                "agent_name": a.agent_name,
                "agent_type": a.agent_type,
                "ai_technique": a.ai_technique,
                "description": a.description,
                "automation_level": a.automation_level,
                "task_count": a.task_count,
                "assigned_tasks": [
                    {
                        "task_id": t.task_id,
                        "task_name": t.task_name,
                        "l4": t.l4,
                        "l3": t.l3,
                        "ai_role": t.ai_role,
                        "human_role": t.human_role,
                        "input_data": t.input_data,
                        "output_data": t.output_data,
                        "automation_level": t.automation_level,
                    }
                    for t in a.assigned_tasks
                ],
            }
            for a in result.agents
        ],
        "execution_flow": [
            {
                "step": s.step,
                "step_name": s.step_name,
                "step_type": s.step_type,
                "description": s.description,
                "agent_ids": s.agent_ids,
                "task_ids": s.task_ids,
            }
            for s in result.execution_flow
        ],
    }


# ── hr-workflow-ai 호환 JSON 변환 ────────────────────────────────────────────

# 자동화 수준별 노드 색상 (hr-workflow-ai 스타일)
_LEVEL_COLOR: dict[str, str] = {
    "Full-Auto":        "#6fcf97",   # 초록
    "Human-in-Loop":    "#f2c94c",   # 노랑
    "Human-Supervised": "#eb5757",   # 빨강
}

# 레인(swimlane) 높이 및 노드 크기 (px)
_LANE_H   = 220
_NODE_H   = 80
_STEP_W   = 280   # 실행 스텝 간격
_X_OFFSET = 120   # 첫 노드 시작 x
_Y_PAD    = 70    # 레인 상단 여백


def result_to_hr_workflow_json(result: NewWorkflowResult) -> dict[str, Any]:
    """
    NewWorkflowResult → hr-workflow-ai v2.0 호환 JSON 변환.

    - 각 AI 에이전트 = 스윔레인 1개
    - 각 L5 Task = L5 노드
    - 실행 플로우 순서 = 엣지로 연결
    """
    from datetime import datetime, timezone

    if not result.agents:
        return {
            "version": "2.0",
            "sheets": [],
            "exportedAt": datetime.now(timezone.utc).isoformat(),
        }

    # ── 레인 목록 (에이전트명) ─────────────────────────────────────────────
    lanes: list[str] = [a.agent_name for a in result.agents]
    lane_index: dict[str, int] = {a.agent_id: i for i, a in enumerate(result.agents)}

    # task_id → agent_id 역매핑
    task_to_agent: dict[str, str] = {}
    for a in result.agents:
        for t in a.assigned_tasks:
            task_to_agent[t.task_id] = a.agent_id

    # task_id → AssignedTask 역매핑
    task_map: dict[str, AssignedTask] = {}
    for a in result.agents:
        for t in a.assigned_tasks:
            task_map[t.task_id] = t

    # ── 노드 위치 계산 ─────────────────────────────────────────────────────
    # execution_flow 기반으로 각 task의 x 스텝을 결정
    task_step: dict[str, int] = {}
    for step in result.execution_flow:
        for tid in step.task_ids:
            task_step[tid] = step.step - 1  # 0-based

    # execution_flow에 없는 task는 맨 뒤 스텝으로
    max_step = max(task_step.values(), default=0)
    for a in result.agents:
        for t in a.assigned_tasks:
            if t.task_id not in task_step:
                max_step += 1
                task_step[t.task_id] = max_step

    # 같은 스텝 + 같은 레인 안에서 y 오프셋 (여러 노드가 겹치지 않도록)
    step_lane_count: dict[tuple[int, int], int] = {}

    nodes: list[dict] = []
    node_id_map: dict[str, str] = {}   # task_id → React Flow node id

    for a in result.agents:
        li = lane_index[a.agent_id]
        lane_color = _LEVEL_COLOR.get(a.automation_level, "#bdbdbd")

        for t in a.assigned_tasks:
            step = task_step.get(t.task_id, 0)
            key = (step, li)
            offset = step_lane_count.get(key, 0)
            step_lane_count[key] = offset + 1

            x = _X_OFFSET + step * _STEP_W
            y = li * _LANE_H + _Y_PAD + offset * (_NODE_H + 20)

            nid = f"nw-{t.task_id.replace('.', '-')}"
            node_id_map[t.task_id] = nid

            nodes.append({
                "id": nid,
                "type": "l5",
                "position": {"x": x, "y": y},
                "data": {
                    "id": t.task_id,
                    "label": t.task_name,
                    "level": "L5",
                    "description": f"[AI] {t.ai_role}" + (f"\n[Human] {t.human_role}" if t.human_role else ""),
                    "role": a.agent_name,
                    "l3Id": "",
                    "l4Id": "",
                    "isManual": False,
                    "automationLevel": t.automation_level,
                    "aiTechnique": a.ai_technique,
                    "actors": {"exec": "", "hr": "", "teamlead": "", "member": ""},
                    "systems": {},
                    "painPoints": {},
                    "inputs": {d: True for d in t.input_data},
                    "outputs": {d: True for d in t.output_data},
                    "logic": {},
                    "nodeColor": lane_color,
                },
            })

    # ── 엣지 생성 ─────────────────────────────────────────────────────────
    edges: list[dict] = []
    edge_id = 0

    # 실행 플로우 순서대로 스텝 간 엣지 연결
    sorted_steps = sorted(result.execution_flow, key=lambda s: s.step)
    for i in range(len(sorted_steps) - 1):
        curr_step = sorted_steps[i]
        next_step = sorted_steps[i + 1]

        # 현재 스텝의 마지막 task → 다음 스텝의 첫 번째 task 연결
        for src_tid in curr_step.task_ids:
            for tgt_tid in next_step.task_ids:
                src_nid = node_id_map.get(src_tid)
                tgt_nid = node_id_map.get(tgt_tid)
                if src_nid and tgt_nid:
                    edges.append({
                        "id": f"e-{edge_id}",
                        "source": src_nid,
                        "target": tgt_nid,
                        "type": "ortho",
                        "animated": False,
                        "style": {"stroke": "#9e9e9e", "strokeWidth": 2},
                        "markerEnd": {
                            "type": "ArrowClosed",
                            "width": 18,
                            "height": 18,
                            "color": "#9e9e9e",
                        },
                    })
                    edge_id += 1
                    break  # 한 연결만 (fan-out 방지)
            else:
                continue
            break

    # 같은 에이전트 내 순차 task 연결 (execution_flow 순서 기반)
    # task_id 리스트를 실행 스텝 순으로 정렬
    all_ordered: list[str] = []
    seen: set[str] = set()
    for step in sorted_steps:
        for tid in step.task_ids:
            if tid not in seen:
                all_ordered.append(tid)
                seen.add(tid)

    agent_task_order: dict[str, list[str]] = {a.agent_id: [] for a in result.agents}
    for tid in all_ordered:
        aid = task_to_agent.get(tid)
        if aid:
            agent_task_order[aid].append(tid)

    for aid, tids in agent_task_order.items():
        for j in range(len(tids) - 1):
            src_nid = node_id_map.get(tids[j])
            tgt_nid = node_id_map.get(tids[j + 1])
            if src_nid and tgt_nid:
                edges.append({
                    "id": f"e-{edge_id}",
                    "source": src_nid,
                    "target": tgt_nid,
                    "type": "ortho",
                    "animated": False,
                    "style": {"stroke": "#555", "strokeWidth": 2},
                    "markerEnd": {
                        "type": "ArrowClosed",
                        "width": 18,
                        "height": 18,
                        "color": "#555",
                    },
                })
                edge_id += 1

    return {
        "version": "2.0",
        "exportedAt": datetime.now(timezone.utc).isoformat(),
        "sheets": [
            {
                "id": "sheet-1",
                "name": result.process_name or "AI 워크플로우 설계",
                "type": "swimlane",
                "lanes": lanes,
                "nodes": nodes,
                "edges": edges,
            }
        ],
    }
