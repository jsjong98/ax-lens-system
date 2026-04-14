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
당신은 AI 기반 업무 혁신 설계 전문가입니다.
기존 As-Is 프로세스의 Task와 Pain Point를 분석하여, **완전히 새로운 To-Be Workflow**를 설계합니다.

## 핵심 철학
**기존 Task에 단순히 AI를 씌우는 것이 아닙니다.**
Pain Point에서 출발하여, AI가 만들어낼 수 있는 **완전히 새로운 가치와 경험**을 설계하세요.

### 사고 방식 (Think Big)
1. **Pain Point를 확장 해석하세요**
   - "연차 시기를 놓친다" → 단순히 알림을 보내는 게 아니라, AI가 패턴을 분석하여 **선제적으로 최적 휴가 시기와 여행지를 추천**하는 챗봇 Workflow
   - "수작업 데이터 취합이 오래 걸린다" → 단순 자동화가 아니라, AI가 **실시간 대시보드 + 이상 징후 선제 알림 + 자동 보고서 생성**까지
   - "신규 입사자 온보딩이 비체계적" → AI가 **개인 맞춤 온보딩 코스 설계 + 멘토 매칭 + 적응도 실시간 모니터링**

2. **As-Is에 없던 완전히 새로운 Task를 만드세요**
   - 기존 Task를 그대로 가져오지 마세요
   - Pain Point를 해결하기 위해 **As-Is에는 존재하지 않았던 혁신적인 단계**를 추가하세요
   - AI가 선제적(proactive)으로 행동하는 Task를 포함하세요

3. **AI + Human 협업을 자연스럽게 설계하세요**
   - AI가 분석/초안/추천 → Human이 확인/판단/승인 → AI가 후속 처리
   - 사람의 전문성이 필요한 영역은 AI가 보조하되, 사람이 주도

## AI 에이전트 유형
- Proactive AI Assistant: 사용자 패턴 분석, 선제적 추천, 맞춤형 안내
- Document Processing AI: 문서 작성, 양식 처리, 보고서 자동 생성
- Data Analysis AI: 데이터 분석, 인사이트 도출, 이상 탐지, 예측
- Information Retrieval AI: 정보 검색, RAG 기반 지식 제공
- Communication AI: 이메일/공지 자동화, 챗봇, 개인화 메시지
- Decision Support AI: 판단 보조, 시나리오 분석, 기준 적용
- Process Automation AI: 시스템 연동, 반복 처리, 규칙 기반 자동화
- Monitoring AI: 실시간 모니터링, 대시보드, 알림

## AI 기법
- LLM: 문서 이해/생성/요약/분류
- RAG: 내부 규정/데이터 기반 답변
- RPA: 반복적 시스템 작업 자동화
- OCR + LLM: 문서 스캔 후 분석
- ML Model: 예측, 패턴 분류, 이상 탐지, 추천
- Rule Engine: 명확한 조건 분기
- API 연동: 시스템 간 자동 연계
- Chatbot/Conversational AI: 대화형 인터페이스

## AI 자율화 수준 (automation_level 값) — 두산그룹 HR AX 프레임워크
우리 프로젝트의 목표는 **Human-on-the-Loop** 수준입니다.

- **Human-on-the-Loop** (본 프로젝트 목표):
  Senior AI(수석급)가 프로세스 전 영역을 관리. Junior AI(선임급)가 실무 수행.
  Human은 **감독·조율 역할**만 수행. AI가 대부분의 업무를 전담.

- **Human-in-the-Loop** (현 수준):
  Junior AI가 Activity 일부를 보조. Human이 의사결정하고 직접 개입.
  → 이 수준에 머물지 마세요. 더 높은 자율화를 설계하세요.

- **Human-out-of-the-Loop** (최종 지향):
  AI가 자율 수행, Human 개입 거의 없음. 결과 확인·최종 조율만.

## 설계 원칙
- 대부분의 Task를 **Human-on-the-Loop**으로 설계 (60~70%)
- Human-in-the-Loop은 법적 판단, 최종 승인 등 꼭 필요한 곳만
- Senior AI가 Junior AI들을 오케스트레이션하는 구조
- Human은 감독자 역할 — 직접 실무를 하지 않고 AI 결과를 확인/승인

## Task 작성 규칙 (반드시 지키세요)
- **task_name**: 짧게 (예: "DBS 점수 추출", "지원자 데이터 정리", "에세이 검토")
- **ai_role**: task_name과 다른 내용, 구체적 처리 방법 한 줄 (예: "DBS 원시 데이터 자동 추출·집계")
- task_name을 ai_role에 반복 금지

## 출력 규칙
- 반드시 JSON만 출력 (마크다운 코드 블록 없음)
- 기존 As-Is Task를 그대로 복사하지 말고 새로운 To-Be Task를 정의
- Pain Point 기반 혁신적 Task 포함
- 에이전트는 최대 7개
- 한국어로 작성
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
        "위 As-Is Task들의 Pain Point를 깊이 분석하여, **완전히 새로운 To-Be Workflow**를 설계해주세요.",
        "기존 Task를 그대로 가져오지 말고, Pain Point에서 출발하여 혁신적인 새 Task를 정의하세요.",
        "AI가 선제적으로 행동하는 Task, 기존에 없던 새로운 가치를 만드는 Task를 포함하세요.",
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

    from usage_store import add_usage as _add_usage

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
            if response.usage:
                _add_usage("anthropic",
                           input_tokens=response.usage.input_tokens,
                           output_tokens=response.usage.output_tokens)
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
            if response.usage:
                _add_usage("openai",
                           input_tokens=response.usage.prompt_tokens,
                           output_tokens=response.usage.completion_tokens)
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

# Agent별 구분 색상 — 파란 계열 유지, 명도·채도 차이로 구분 (PPT/HTML/Frontend 동일)
_AGENT_PALETTE: list[str] = [
    "#1A3C6E",   # 1  진남색
    "#2E75B6",   # 2  중간 파란
    "#00827F",   # 3  틸
    "#5B9BD5",   # 4  밝은 하늘
    "#4B0082",   # 5  인디고
    "#00A6A0",   # 6  밝은 청록
    "#4172C4",   # 7  코발트
    "#7B68C4",   # 8  퍼플블루
    "#006E90",   # 9  페트롤
    "#87CEEB",   # 10 스카이
]

# 레인(swimlane) 높이 및 노드 크기 (px)
_MIN_LANE_H = 160  # 레인 최소 높이
_NODE_H   = 80
_NODE_GAP = 24     # 같은 레인·스텝 내 노드 수직 간격
_STEP_W   = 280    # 실행 스텝 간격
_X_OFFSET = 120    # 첫 노드 시작 x
_Y_PAD    = 60     # 레인 상단·하단 여백

# swim lane 액터 표준 순서 (상→하)
_ACTOR_ORDER = [
    "임원", "현업 팀장", "HR 임원", "HR 담당자",
    "Senior AI", "Junior AI", "현업 구성원", "그 외",
]

# 액터별 노드 강조 색상
_ACTOR_COLOR: dict[str, str] = {
    "임원":       "#2E3A59",
    "현업 팀장":  "#3D5A80",
    "HR 임원":    "#1A3C6E",
    "HR 담당자":  "#2E75B6",
    "Senior AI":  "#00827F",
    "Junior AI":  "#00A6A0",
    "현업 구성원":"#5B9BD5",
    "그 외":      "#9E9E9E",
}


def _sort_actors(actors: list[str]) -> list[str]:
    """표준 swim lane 순서대로 액터 정렬."""
    def _key(a: str) -> int:
        try:
            return _ACTOR_ORDER.index(a)
        except ValueError:
            return 99
    return sorted(actors, key=_key)


def _topo_steps(nodes: list[dict]) -> dict[str, int]:
    """
    next[] 그래프 위상정렬 → 각 노드의 x-step(0-based) 계산.
    cycle이 있으면 남은 노드를 순서대로 배정.
    """
    from collections import defaultdict, deque

    id_set = {n["id"] for n in nodes}
    in_degree: dict[str, int] = {n["id"]: 0 for n in nodes}
    adj: dict[str, list[str]] = defaultdict(list)

    for n in nodes:
        for nxt in n.get("next", []):
            if nxt in id_set:
                adj[n["id"]].append(nxt)
                in_degree[nxt] += 1

    queue: deque[str] = deque(nid for nid, d in in_degree.items() if d == 0)
    step_map: dict[str, int] = {}
    current = 0

    while queue:
        level_size = len(queue)
        for _ in range(level_size):
            nid = queue.popleft()
            step_map[nid] = current
            for nxt in adj[nid]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)
        current += 1

    # cycle 잔여 노드 처리
    for n in nodes:
        if n["id"] not in step_map:
            step_map[n["id"]] = current
            current += 1

    return step_map


def _calc_lane_layout(
    n_lanes: int,
    lane_step_count: dict[int, dict[int, int]],
) -> tuple[list[int], list[int]]:
    """
    레인별 동적 높이 + 누적 y 오프셋 계산.

    Returns:
        lane_heights  : 각 레인의 픽셀 높이 리스트
        lane_y_offsets: 각 레인의 시작 y 리스트
    """
    heights = []
    for li in range(n_lanes):
        max_stack = max(lane_step_count.get(li, {}).values(), default=1)
        h = max(max_stack * (_NODE_H + _NODE_GAP) + 2 * _Y_PAD, _MIN_LANE_H)
        heights.append(h)

    offsets = []
    acc = 0
    for h in heights:
        offsets.append(acc)
        acc += h

    return heights, offsets


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

    # 레인별 동적 높이 계산 — 먼저 (lane, step) 별 노드 수 집계
    _slc_pre: dict[int, dict[int, int]] = {}
    for a in result.agents:
        li = lane_index[a.agent_id]
        for t in a.assigned_tasks:
            s = task_step.get(t.task_id, 0)
            _slc_pre.setdefault(li, {})
            _slc_pre[li][s] = _slc_pre[li].get(s, 0) + 1

    lane_heights, lane_y_offsets = _calc_lane_layout(len(lanes), _slc_pre)

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
            y = lane_y_offsets[li] + _Y_PAD + offset * (_NODE_H + _NODE_GAP)

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

    # ── Agent별 색상 매핑 ────────────────────────────────────────────────
    agent_color: dict[str, str] = {}
    for idx, a in enumerate(result.agents):
        agent_color[a.agent_id] = _AGENT_PALETTE[idx % len(_AGENT_PALETTE)]

    # ── 엣지 생성 ─────────────────────────────────────────────────────────
    edges: list[dict] = []
    edge_id = 0

    # 실행 플로우 순서대로 스텝 간 엣지 연결 (Agent 색상 적용)
    sorted_steps = sorted(result.execution_flow, key=lambda s: s.step)
    for i in range(len(sorted_steps) - 1):
        curr_step = sorted_steps[i]
        next_step = sorted_steps[i + 1]

        for src_tid in curr_step.task_ids:
            for tgt_tid in next_step.task_ids:
                src_nid = node_id_map.get(src_tid)
                tgt_nid = node_id_map.get(tgt_tid)
                if src_nid and tgt_nid:
                    src_aid = task_to_agent.get(src_tid, "")
                    color = agent_color.get(src_aid, "#9e9e9e")
                    # 데이터 흐름 라벨 (source task의 output)
                    src_task = task_map.get(src_tid)
                    label = ""
                    if src_task and src_task.output_data:
                        label = src_task.output_data[0][:20]
                    edges.append({
                        "id": f"e-{edge_id}",
                        "source": src_nid,
                        "target": tgt_nid,
                        "type": "ortho",
                        "animated": False,
                        "label": label,
                        "style": {"stroke": color, "strokeWidth": 2},
                        "markerEnd": {
                            "type": "ArrowClosed",
                            "width": 18,
                            "height": 18,
                            "color": color,
                        },
                    })
                    edge_id += 1
                    break
            else:
                continue
            break

    # 같은 에이전트 내 순차 task 연결 (Agent 고유 색상)
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
        color = agent_color.get(aid, "#AA8E2A")
        for j in range(len(tids) - 1):
            src_nid = node_id_map.get(tids[j])
            tgt_nid = node_id_map.get(tids[j + 1])
            if src_nid and tgt_nid:
                src_task = task_map.get(tids[j])
                label = ""
                if src_task and src_task.output_data:
                    label = src_task.output_data[0][:20]
                edges.append({
                    "id": f"e-{edge_id}",
                    "source": src_nid,
                    "target": tgt_nid,
                    "type": "ortho",
                    "animated": False,
                    "label": label,
                    "style": {"stroke": color, "strokeWidth": 2},
                    "markerEnd": {
                        "type": "ArrowClosed",
                        "width": 18,
                        "height": 18,
                        "color": color,
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
                "laneHeights": lane_heights,
                "nodes": nodes,
                "edges": edges,
                "agentColors": {a.agent_id: agent_color[a.agent_id] for a in result.agents},
            }
        ],
    }


# ── generate-tobe-flow 결과 → hr-workflow-ai JSON 변환 ────────────────────────

def tobe_sheets_to_hr_json(tobe_data: dict) -> dict:
    """
    generate-tobe-flow LLM 결과(tobe_sheets) → hr-workflow-ai v2.0 호환 JSON 변환.

    - actors_used 기준으로 swim lane 구성 (표준 순서 정렬)
    - next[] 그래프 위상정렬 → x 좌표
    - 레인별 동적 높이 (stack 수 기반)
    - L4 시트마다 독립 sheet 생성 (multi-sheet)
    """
    from datetime import datetime, timezone

    process_name = tobe_data.get("process_name", "To-Be Workflow")
    raw_sheets = tobe_data.get("tobe_sheets", [])

    sheets_out: list[dict] = []

    for raw_sheet in raw_sheets:
        sheet_id = str(raw_sheet.get("l4_id", f"sheet-{len(sheets_out) + 1}"))
        sheet_name = str(raw_sheet.get("l4_name", sheet_id))
        raw_nodes: list[dict] = raw_sheet.get("nodes", [])
        actors_used: list[str] = raw_sheet.get("actors_used", [])

        if not raw_nodes:
            continue

        # 레인 목록 — 표준 순서 정렬
        lanes = _sort_actors(actors_used) if actors_used else ["HR 담당자", "Senior AI", "Junior AI"]
        lane_index: dict[str, int] = {actor: i for i, actor in enumerate(lanes)}

        # 위상정렬로 x-step 계산
        node_step = _topo_steps(raw_nodes)

        # (lane, step) 별 노드 수 집계 → 동적 레인 높이
        _slc: dict[int, dict[int, int]] = {}
        for n in raw_nodes:
            actor = n.get("actor", "그 외")
            li = lane_index.get(actor, len(lanes) - 1)
            s = node_step.get(n["id"], 0)
            _slc.setdefault(li, {})
            _slc[li][s] = _slc[li].get(s, 0) + 1

        lane_heights, lane_y_offsets = _calc_lane_layout(len(lanes), _slc)

        # 노드 생성
        nodes_out: list[dict] = []
        node_id_map: dict[str, str] = {}
        stack_seen: dict[tuple[int, int], int] = {}

        for n in raw_nodes:
            actor = n.get("actor", "그 외")
            li = lane_index.get(actor, len(lanes) - 1)
            s = node_step.get(n["id"], 0)

            key = (s, li)
            stack_off = stack_seen.get(key, 0)
            stack_seen[key] = stack_off + 1

            x = _X_OFFSET + s * _STEP_W
            y = lane_y_offsets[li] + _Y_PAD + stack_off * (_NODE_H + _NODE_GAP)

            node_type = n.get("type", "task")
            level = {"start": "L4", "end": "L4", "decision": "DECISION"}.get(node_type, "L5")

            nid = f"tb-{sheet_id}-{n['id']}"
            node_id_map[n["id"]] = nid

            color = _ACTOR_COLOR.get(actor, "#9E9E9E")
            ai_support = n.get("ai_support") or ""

            nodes_out.append({
                "id": nid,
                "type": "l5" if level == "L5" else ("decision" if level == "DECISION" else "l4"),
                "position": {"x": x, "y": y},
                "data": {
                    "id": n["id"],
                    "label": n.get("label", "")[:14],   # hr-workflow-ai 14자 제한
                    "level": level,
                    "description": ai_support,
                    "role": actor,
                    "nodeColor": color,
                    "isManual": actor not in ("Senior AI", "Junior AI"),
                    "automationLevel": (
                        "Full-Auto" if actor == "Senior AI"
                        else ("Human-in-Loop" if actor == "Junior AI" else "Human")
                    ),
                    "actors": {},
                    "systems": {},
                    "painPoints": {},
                    "inputs": {},
                    "outputs": {},
                    "logic": {},
                },
            })

        # 엣지 생성 — next[] 그래프 기반
        edges_out: list[dict] = []
        edge_id = 0
        for n in raw_nodes:
            src_nid = node_id_map.get(n["id"])
            if not src_nid:
                continue
            actor = n.get("actor", "그 외")
            color = _ACTOR_COLOR.get(actor, "#9E9E9E")
            for nxt in n.get("next", []):
                tgt_nid = node_id_map.get(nxt)
                if tgt_nid:
                    edges_out.append({
                        "id": f"e-{sheet_id}-{edge_id}",
                        "source": src_nid,
                        "target": tgt_nid,
                        "type": "ortho",
                        "animated": actor in ("Senior AI", "Junior AI"),
                        "style": {"stroke": color, "strokeWidth": 2},
                        "markerEnd": {
                            "type": "ArrowClosed",
                            "width": 18, "height": 18, "color": color,
                        },
                    })
                    edge_id += 1

        sheets_out.append({
            "id": sheet_id,
            "name": sheet_name,
            "type": "swimlane",
            "lanes": lanes,
            "laneHeights": lane_heights,
            "nodes": nodes_out,
            "edges": edges_out,
        })

    return {
        "version": "2.0",
        "exportedAt": datetime.now(timezone.utc).isoformat(),
        "processName": process_name,
        "sheets": sheets_out,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 자유형식 입력 기반 Workflow 생성
# ═══════════════════════════════════════════════════════════════════════════════

_FREEFORM_SYSTEM_PROMPT = """
당신은 AI 기반 업무 혁신 설계 전문가입니다.
사용자가 제공하는 업무 개요(주제, Input, Output, 시스템/툴, Pain Point 등)를 분석하여,
**완전히 새로운 To-Be Workflow**를 설계합니다.

## 핵심 철학: Pain Point에서 혁신을 만들어내세요

**기존 업무에 AI를 단순히 붙이는 것이 아닙니다.**
Pain Point의 근본 원인을 파악하고, AI가 만들 수 있는 **완전히 새로운 가치와 경험**을 설계하세요.

### 사고 과정 (반드시 이 순서로 생각하세요)

**Step 1: Pain Point 확장 해석**
- 표면적 Pain Point 뒤에 숨어있는 **근본 원인**을 파악하세요
- 예: "연차 시기를 놓친다" → 근본: 업무에 몰두하다 보면 자기 관리를 할 여유가 없다
- 예: "데이터 취합이 오래 걸린다" → 근본: 정보가 분산되어 있고 실시간 가시성이 없다

**Step 2: 혁신적 해결 방향 도출**
- 근본 원인에 대해 AI가 **선제적(proactive)으로** 해결할 수 있는 방법을 설계하세요
- 예: AI 챗봇이 사용자의 패턴을 분석하여 "최근 6개월간 휴가를 안 쓰셨는데, 다음 주 수요일은 어떠세요? 2자녀 가족들은 이런 곳을 많이 갑니다" → 사람이 확인 → AI가 신청 처리
- 예: AI가 실시간 대시보드 + 이상 징후 선제 알림 + 자동 요약 보고서 → 사람은 전략적 판단에 집중

**Step 3: AI + Human 협업 흐름 설계**
- AI가 분석/추천/초안 → Human이 확인/판단/승인 → AI가 후속 처리/실행
- 사람의 전문적 판단이 필요한 곳은 명확히 구분

## AI 에이전트 유형
- Proactive AI Assistant: 사용자 패턴 분석, 선제적 추천/안내, 맞춤형 코칭
- Intelligent Chatbot: 대화형 인터페이스, 자연어 질의, 가이드
- Document Processing AI: 문서 자동 작성/분석/요약
- Data Analysis AI: 데이터 분석, 인사이트 도출, 예측, 이상 탐지
- Information Retrieval AI: RAG 기반 지식 검색, 규정/사례 조회
- Communication AI: 개인화 메시지, 이메일 자동화, 알림
- Decision Support AI: 시나리오 분석, 판단 보조, 기준 적용
- Process Automation AI: 시스템 연동, RPA, 규칙 기반 자동화
- Monitoring AI: 실시간 모니터링, 대시보드, 선제적 알림

## AI 기법
- LLM: 문서 이해/생성/요약/분류/대화
- RAG: 내부 규정/데이터 기반 답변
- ML Model: 예측, 패턴 분류, 추천, 이상 탐지
- RPA: 반복 시스템 작업 자동화
- Chatbot/Conversational AI: 대화형 인터페이스
- OCR + LLM: 문서 스캔 후 분석
- Rule Engine: 조건 분기
- API 연동: 시스템 간 자동 연계

## AI 자율화 수준 (automation_level 값) — HR AX 프레임워크
목표: **Human-on-the-Loop** 수준

- **Human-on-the-Loop** (목표): Senior AI가 전 영역 관리, Junior AI가 실무. Human은 감독·조율만
- **Human-in-the-Loop** (현 수준): Junior AI가 일부 보조, Human이 의사결정·직접 개입
- **Human-out-of-the-Loop** (지향): AI 자율 수행, Human 개입 거의 없음

## 설계 원칙
- Human-on-the-Loop 60~70% 이상
- Senior AI → Junior AI 오케스트레이션 구조
- Human은 감독자 — AI 결과 확인/승인만

## Task 작성 규칙
- **task_name**: 짧게 (예: "DBS 점수 추출", "에세이 검토")
- **ai_role**: task_name과 다른 처리 방법 한 줄
- task_name을 ai_role에 반복 금지

## 출력 형식 (JSON)
{
  "blueprint_summary": "2~3문장 간결 요약",
  "process_name": "프로세스명",
  "agents": [
    {
      "agent_id": "agent_1",
      "agent_name": "짧은 이름 (예: 데이터 수집·정제기)",
      "agent_type": "유형",
      "ai_technique": "기법",
      "description": "역할 한 줄",
      "automation_level": "Human-on-the-Loop | Human-in-the-Loop | Human-Supervised",
      "assigned_tasks": [
        {
          "task_id": "1.1",
          "task_name": "짧은 Task명",
          "l4": "상위 카테고리",
          "l3": "프로세스 영역",
          "ai_role": "구체적 처리 방법 한 줄",
          "human_role": "사람이 하는 구체적 행동 (예: '스크리닝 결과 최종 확정'). task_name과 같은 내용 금지. AI 자율이면 빈 문자열",
          "input_data": ["입력"],
          "output_data": ["출력"],
          "automation_level": "Human-on-the-Loop | Human-in-the-Loop | Human-Supervised"
        }
      ]
    }
  ],
  "execution_flow": [
    {
      "step": 1,
      "step_name": "단계명",
      "step_type": "sequential | parallel",
      "description": "설명",
      "agent_ids": ["agent_1"],
      "task_ids": ["1.1"]
    }
  ]
}

## 규칙
- 반드시 JSON만 출력 (마크다운 코드 블록 없음)
- Task ID는 "1.1", "1.2", "2.1" 형태
- 최소 5개, 최대 20개 Task를 새로 정의
- Pain Point 기반 혁신적 Task 포함
- 에이전트는 최대 7개
- **task_name은 반드시 10~20자로 짧게, ai_role은 task_name과 다른 내용**
- AI 단독(Full-Auto) 60~70% 이상
- 한국어로 작성
"""


def _build_freeform_prompt(
    process_name: str,
    inputs: str,
    outputs: str,
    systems: str,
    pain_points: str,
    additional_info: str,
) -> str:
    """자유형식 입력으로부터 LLM 프롬프트 생성."""
    lines = [f"## 업무 개요\n"]
    lines.append(f"**프로세스/주제**: {process_name}\n")
    if inputs:
        lines.append(f"**Input (투입 자료/데이터)**: {inputs}\n")
    if outputs:
        lines.append(f"**Output (산출물/결과물)**: {outputs}\n")
    if systems:
        lines.append(f"**사용 시스템/툴**: {systems}\n")
    if pain_points:
        lines.append(f"**Pain Point (현재 문제점)**: {pain_points}\n")
    if additional_info:
        lines.append(f"**참고 사항**: {additional_info}\n")

    lines.append("\n## 설계 지시사항")
    lines.append("1. Pain Point를 확장 해석하여, 근본 원인을 파악하세요.")
    lines.append("2. 기존에 없던 **혁신적인 Task**를 정의하세요 (선제적 추천, 패턴 분석, 맞춤형 안내 등).")
    lines.append("3. Input에서 시작하여 원하는 Output까지 이어지는 완전히 새로운 흐름을 설계하세요.")
    lines.append("4. AI가 선제적(proactive)으로 행동하는 단계를 반드시 포함하세요.")
    lines.append("5. AI + Human 협업: AI가 분석/추천 → Human이 확인/판단 → AI가 후속 처리.")
    lines.append("6. 단순히 업무를 자동화하는 것이 아니라, **새로운 가치와 경험**을 만들어내세요.")

    return "\n".join(lines)


def _parse_freeform_result(data: dict) -> NewWorkflowResult:
    """자유형식 LLM 응답을 NewWorkflowResult로 파싱."""
    agents_raw = data.get("agents", [])
    agents: list[AIAgent] = []
    all_tasks: list[AssignedTask] = []

    for a in agents_raw:
        tasks_list = []
        for t in a.get("assigned_tasks", []):
            at = AssignedTask(
                task_id=str(t.get("task_id", "")),
                task_name=t.get("task_name", ""),
                l4=t.get("l4", ""),
                l3=t.get("l3", ""),
                ai_role=t.get("ai_role", ""),
                human_role=t.get("human_role", ""),
                input_data=t.get("input_data", []),
                output_data=t.get("output_data", []),
                automation_level=t.get("automation_level", "Human-in-Loop"),
            )
            tasks_list.append(at)
            all_tasks.append(at)

        agent = AIAgent(
            agent_id=a.get("agent_id", f"agent_{len(agents)+1}"),
            agent_name=a.get("agent_name", ""),
            agent_type=a.get("agent_type", ""),
            ai_technique=a.get("ai_technique", ""),
            description=a.get("description", ""),
            automation_level=a.get("automation_level", "Human-in-Loop"),
            assigned_tasks=tasks_list,
        )
        agents.append(agent)

    flow_raw = data.get("execution_flow", [])
    execution_flow = [
        ExecutionStep(
            step=s.get("step", i + 1),
            step_name=s.get("step_name", ""),
            step_type=s.get("step_type", "sequential"),
            description=s.get("description", ""),
            agent_ids=s.get("agent_ids", []),
            task_ids=s.get("task_ids", []),
        )
        for i, s in enumerate(flow_raw)
    ]

    full_auto = sum(1 for t in all_tasks if t.automation_level == "Full-Auto")
    hil = sum(1 for t in all_tasks if t.automation_level == "Human-in-Loop")
    hs = sum(1 for t in all_tasks if t.automation_level == "Human-Supervised")

    return NewWorkflowResult(
        blueprint_summary=data.get("blueprint_summary", ""),
        process_name=data.get("process_name", ""),
        total_tasks=len(all_tasks),
        full_auto_count=full_auto,
        human_in_loop_count=hil,
        human_supervised_count=hs,
        agents=agents,
        execution_flow=execution_flow,
    )


async def generate_workflow_from_freeform(
    process_name: str,
    inputs: str = "",
    outputs: str = "",
    systems: str = "",
    pain_points: str = "",
    additional_info: str = "",
    api_key: str = "",
    model: str = "claude-sonnet-4-6",
    openai_api_key: str = "",
    openai_model: str = "gpt-5.4",
) -> NewWorkflowResult:
    """
    자유형식 입력을 받아 AI가 새로운 L5 Task를 정의하고 Workflow를 설계합니다.
    """
    user_prompt = _build_freeform_prompt(
        process_name, inputs, outputs, systems, pain_points, additional_info,
    )

    from usage_store import add_usage as _add_usage_ff

    # Anthropic Claude
    anthropic_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=anthropic_key)
            response = await client.messages.create(
                model=model,
                max_tokens=8192,
                system=_FREEFORM_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            if response.usage:
                _add_usage_ff("anthropic",
                              input_tokens=response.usage.input_tokens,
                              output_tokens=response.usage.output_tokens)
            raw = response.content[0].text
            data = _extract_json(raw)
            return _parse_freeform_result(data)
        except Exception as e:
            print(f"[new_workflow_freeform] Anthropic 실패: {e}")

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
                    {"role": "system", "content": _FREEFORM_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            if response.usage:
                _add_usage_ff("openai",
                              input_tokens=response.usage.prompt_tokens,
                              output_tokens=response.usage.completion_tokens)
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            return _parse_freeform_result(data)
        except Exception as e:
            print(f"[new_workflow_freeform] OpenAI 실패: {e}")

    return NewWorkflowResult(
        blueprint_summary="API 키가 설정되지 않아 워크플로우를 생성할 수 없습니다.",
        process_name=process_name,
        total_tasks=0, full_auto_count=0, human_in_loop_count=0, human_supervised_count=0,
    )
