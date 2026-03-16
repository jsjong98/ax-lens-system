"""
tobe_generator.py — To-Be Workflow + Agent 정의 자동 생성기

Anthropic Claude (claude-sonnet-4-6) 기반으로:
  1. Junior AI Agent 그루핑 + AI 기법 추론
  2. Senior AI Agent 오케스트레이션 전략 수립
  3. AI+Human 태스크 분할
  4. To-Be Workflow (React Flow JSON) 초안 생성

LLM 호출이 실패하면 규칙 기반 fallback으로 동작합니다.
"""
from __future__ import annotations

import json
import os
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
    technique: str = ""     # 개별 태스크의 AI 기법
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
    senior_instruction: str = ""  # Senior AI가 이 Agent에게 내리는 지시

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


# ── LLM 프롬프트 ─────────────────────────────────────────────────────────────

_TOBE_SYSTEM_PROMPT = """당신은 HR 업무 자동화 아키텍트입니다.
As-Is 워크플로우의 L5 태스크 목록과 AI 분류 결과를 받아,
To-Be 워크플로우를 설계합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【사고 과정】 — 반드시 아래 순서로 단계별로 깊이 사고한 뒤 결론을 내리세요
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step A. 업무 흐름 파악
  — L5 태스크들을 순서대로 읽고, 어떤 업무가 어떤 순서로 흘러가는지 파악합니다.
  — 같은 L4 안에서 어떤 태스크들이 하나의 "업무 묶음"으로 보이는지 판단합니다.

Step B. 역할 분담 설계
  — 실제 회사에서 사원·주임급 직원이 여러 개의 세부 업무를 순차적으로 처리하듯이,
    Junior AI Agent 하나가 여러 L5 태스크를 순서대로 처리하는 것이 자연스러운지 판단합니다.
  — 사람이 중간에 개입해야 하는 업무(검토·승인·판단)가 있으면 그 지점에서 끊습니다.

Step C. AI 기법 매칭
  — 각 태스크의 특성(데이터 분석? 문서 작성? 외부 자료 수집?)을 보고
    가장 적합한 AI 기법을 선택합니다.

Step D. 오케스트레이션 전략
  — Senior AI가 각 Junior Agent를 어떤 순서로 기동하고,
    Agent 간 산출물을 어떻게 전달할지 전략을 수립합니다.
  — 독립적인 Agent끼리는 병렬 수행이 가능한지 검토합니다.

위 사고 과정을 거친 뒤, 최종 결과만 JSON으로 출력하세요.
(사고 과정 자체는 출력하지 마세요)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【역할 정의】 — 실제 조직 구조에 비유
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ Junior AI Agent = 사원·주임급 실무자
  - 사람이 여러 세부 업무를 순차적으로 처리하듯이,
    같은 L4 안에서 연속된 AI 수행 가능 L5 태스크 2개 이상을 묶어 순차 파이프라인으로 처리
  - 예: 사원이 "자료 수집 → 분석 → 보고서 초안 작성"을 연달아 하는 것과 같음
  - Human 태스크가 중간에 끼면 그룹을 끊고 새 Agent 생성
  - 각 Agent마다 구체적인 AI 기법을 지정 (아래 참조)
  - L5 태스크가 1개뿐이면 단독 Agent로 생성

■ Senior AI Agent (Orchestrator) = 대리·과장급 관리자
  - As-Is에 없던 새로운 엔티티로 신규 생성
  - 팀장이 팀원들에게 업무를 배분하고 진행 상황을 관리하듯이,
    모든 Junior Agent의 실행 순서를 관리
  - Junior Agent 간 산출물 전달 및 정합성 검증
  - Human 수행 단계로의 핸드오프 제어 ("이 부분은 사람이 확인해야 합니다")
  - 각 Junior Agent에게 기동 지시(어떤 범위와 기준으로 수행할지) 전달

■ Human (HR 담당자) = 사람이 직접 해야 하는 역할
  - "인간 수행 필요" 태스크 수행
  - "AI + Human" 태스크의 Human 파트(검토·승인·판단) 수행

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【AI 기법 목록】 — 각 태스크에 가장 적합한 기법을 선택
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  · LLM — 텍스트 생성, 요약, 초안 작성, 번역, 질의응답
  · RAG — 사내 문서/규정/이력 검색 후 답변 생성
  · Tabular 분석 — 정형 데이터 집계, 통계, 이상치 탐지
  · Clustering — 유사 그룹 분류, 패턴 발견
  · 임베딩 유사도 — 텍스트/문서 간 유사도 비교, 매칭
  · 규칙 기반 — 확정된 기준에 따른 자동 분류/매핑
  · Web Crawling — 외부 정보 수집 (벤치마크, 법령 등)
  · LLM 기반 추천 — 데이터 기반 최적 옵션 추천

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【출력 형식】 JSON만 출력
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{
  "junior_agents": [
    {
      "agent_name": "니즈 분석",
      "l4_id": "1.6.1",
      "task_ids": ["1.6.1.1", "1.6.1.2", "1.6.1.3", "1.6.1.4"],
      "techniques_per_task": {
        "1.6.1.1": ["LLM"],
        "1.6.1.2": ["LLM"],
        "1.6.1.3": ["Web Crawling", "RAG"],
        "1.6.1.4": ["LLM"]
      },
      "agent_technique_summary": "LLM + RAG + Web Crawling",
      "description": "교육 니즈를 Top-down/Bottom-up 양방향으로 분석하고 외부 자료를 수집하여 시사점을 도출하는 파이프라인",
      "senior_instruction": "키워드·소스·범위 설정 후 기동. 완료 시 니즈 분석 보고서 수령",
      "input_description": "외부 HRD 매체, 교육 니즈 자료",
      "output_description": "니즈 분석 보고서, Implication 도출"
    }
  ],
  "human_steps": [
    {
      "task_id": "1.6.3.6",
      "label": "경영진 보고",
      "reason": "최종 의사결정 및 보고는 인간 고유 영역",
      "is_hybrid_human_part": false
    }
  ],
  "senior_agent": {
    "name": "교육체계 수립 Senior AI Orchestrator",
    "description": "3개 Junior Agent의 실행을 관리하고, Agent 간 산출물을 전달하며, Human 단계 핸드오프를 제어하는 오케스트레이터",
    "orchestration_strategy": "Agent 1, 2를 병렬 기동 → 산출물 수령 → Agent 3에 전달 → Human 검토·승인 → 보고"
  },
  "workflow_optimization": {
    "parallel_opportunities": ["Agent 1과 Agent 2는 독립적이므로 병렬 수행 가능"],
    "sequential_dependencies": ["Agent 3은 Agent 1·2의 산출물이 필요하므로 순차"],
    "improvement_notes": "병렬 수행으로 기존 대비 처리 시간 약 30% 단축 가능"
  }
}

■ 유의사항:
  - task_ids에는 AI 수행 가능 태스크와 AI+Human의 AI 파트만 포함
  - 인간 수행 필요 태스크와 AI+Human의 Human 파트는 human_steps에 포함
  - 같은 L4 안에서만 묶을 것 (L4 경계를 넘지 않음)
  - techniques_per_task에 각 태스크별 적합한 AI 기법을 1~2개 지정
  - senior_instruction은 Senior AI가 해당 Agent에게 내리는 구체적 지시 내용
  - 기술 용어를 쉽게 풀어서 description을 작성할 것
"""


# ── To-Be 생성 (LLM 기반) ────────────────────────────────────────────────────

async def generate_tobe_with_llm(
    as_is_sheet: WorkflowSheet,
    classification_results: dict[str, dict],
    process_name: str = "",
    api_key: str = "",
    model: str = "claude-sonnet-4-6",
) -> ToBeWorkflow:
    """
    Anthropic Claude를 활용한 To-Be Workflow 생성.
    anthropic_classifier.py와 동일한 패턴으로 API 호출합니다.
    LLM이 에이전트 그루핑, 기법 추론, 오케스트레이션 전략을 수행합니다.
    """
    from anthropic import AsyncAnthropic
    from usage_store import add_usage

    # API 키: 환경변수 → 파라미터 순으로 확인 (anthropic_classifier.py 패턴)
    api_key = os.getenv("ANTHROPIC_API_KEY", "") or api_key
    if not api_key:
        print("[To-Be LLM] API 키 없음, 규칙 기반 fallback")
        return generate_tobe(as_is_sheet, classification_results, process_name)

    client = AsyncAnthropic(api_key=api_key)

    # 1. 분류 결과 매핑
    classified_nodes = _map_classifications(as_is_sheet, classification_results)

    # 2. LLM에 보낼 태스크 정보 구성
    user_prompt = _build_tobe_user_prompt(
        classified_nodes, process_name or as_is_sheet.name
    )

    # 3. Claude 호출 (anthropic_classifier.py와 동일한 패턴)
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=8192,
            system=_TOBE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = response.content[0].text

        # 토큰 사용량 누적 기록
        if response.usage:
            add_usage(
                "anthropic",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

        llm_result = _extract_json_from_response(raw)

        # 4. LLM 결과를 데이터 모델로 변환
        return _build_tobe_from_llm_result(
            llm_result, classified_nodes, as_is_sheet, process_name,
            classification_results,
        )

    except Exception as e:
        print(f"[To-Be LLM] Claude 호출 실패, 규칙 기반 fallback: {e}")
        return generate_tobe(as_is_sheet, classification_results, process_name)


def _build_tobe_user_prompt(
    classified_nodes: list[dict],
    process_name: str,
) -> str:
    """LLM에 보낼 사용자 프롬프트를 구성합니다."""
    lines = [
        f"프로세스: {process_name}\n",
        "아래 L5 태스크 목록과 AI 분류 결과를 기반으로 To-Be 워크플로우를 설계해 주세요.\n",
        "─── L5 태스크 목록 ───",
    ]

    for node in classified_nodes:
        tid = node["task_id"]
        label = node["label"]
        cls = node["classification"]
        reason = node.get("reason", "")
        hybrid = node.get("hybrid_note", "")
        inputs = node.get("input_types", "")
        outputs = node.get("output_types", "")

        line = f"  [{tid}] {label}"
        line += f"\n    분류: {cls}"
        if reason:
            line += f"\n    근거: {reason}"
        if hybrid:
            line += f"\n    AI+Human: {hybrid}"
        if inputs:
            line += f"\n    Input: {inputs}"
        if outputs:
            line += f"\n    Output: {outputs}"
        lines.append(line)

    lines.append("\n위 태스크들을 분석하여 Junior Agent 그루핑, AI 기법 지정, "
                 "Senior AI 오케스트레이션 전략을 JSON으로 출력해 주세요.")

    return "\n".join(lines)


def _extract_json_from_response(text: str) -> dict:
    """Claude 응답에서 JSON을 추출합니다."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


def _build_tobe_from_llm_result(
    llm_result: dict,
    classified_nodes: list[dict],
    as_is_sheet: WorkflowSheet,
    process_name: str,
    classification_results: dict[str, dict],
) -> ToBeWorkflow:
    """LLM 결과를 ToBeWorkflow 데이터 모델로 변환합니다."""

    # 분류 결과 빠른 조회용 맵
    node_by_tid = {n["task_id"]: n for n in classified_nodes}

    # ── Junior Agents ──
    junior_agents: list[JuniorAgent] = []
    for idx, ja_data in enumerate(llm_result.get("junior_agents", []), 1):
        task_ids = ja_data.get("task_ids", [])
        techniques_map = ja_data.get("techniques_per_task", {})

        agent_tasks = []
        for tid in task_ids:
            node = node_by_tid.get(tid, {})
            if not node:
                continue
            tech_list = techniques_map.get(tid, ["LLM"])
            agent_tasks.append(AgentTask(
                task_id=tid,
                label=node.get("label", tid),
                classification=node.get("classification", "AI 수행 가능"),
                reason=node.get("reason", ""),
                ai_part=node.get("hybrid_note", ""),
                technique=" + ".join(tech_list) if isinstance(tech_list, list) else str(tech_list),
                node_id=node.get("node_id", ""),
            ))

        if not agent_tasks:
            continue

        junior_agents.append(JuniorAgent(
            id=f"junior-ai-{idx}",
            name=ja_data.get("agent_name", f"Agent {idx}"),
            tasks=agent_tasks,
            technique=ja_data.get("agent_technique_summary", "LLM"),
            input_types=ja_data.get("input_description", ""),
            output_types=ja_data.get("output_description", ""),
            description=ja_data.get("description", ""),
            senior_instruction=ja_data.get("senior_instruction", ""),
        ))

    # ── Human Steps ──
    human_steps: list[HumanStep] = []
    for idx, hs_data in enumerate(llm_result.get("human_steps", []), 1):
        tid = hs_data.get("task_id", "")
        node = node_by_tid.get(tid, {})
        human_steps.append(HumanStep(
            id=f"human-{idx}",
            task_id=tid,
            label=hs_data.get("label", node.get("label", tid)),
            reason=hs_data.get("reason", ""),
            is_hybrid_human_part=hs_data.get("is_hybrid_human_part", False),
            node_id=node.get("node_id", ""),
        ))

    # LLM이 놓친 Human 태스크 보충
    llm_human_tids = {h.task_id for h in human_steps}
    for node in classified_nodes:
        tid = node["task_id"]
        if tid in llm_human_tids:
            continue
        if node["classification"] == "인간 수행 필요":
            human_steps.append(HumanStep(
                id=f"human-{len(human_steps)+1}",
                task_id=tid,
                label=node["label"],
                reason=node.get("reason", ""),
                is_hybrid_human_part=False,
                node_id=node.get("node_id", ""),
            ))

    # ── Senior Agent ──
    sa_data = llm_result.get("senior_agent", {})
    opt_data = llm_result.get("workflow_optimization", {})

    senior = SeniorAgent(
        id="senior-ai-1",
        name=sa_data.get("name", f"{process_name} Senior AI Orchestrator"),
        junior_agents=junior_agents,
        human_steps=human_steps,
        description=sa_data.get("description", ""),
    )

    # 오케스트레이션 전략을 description에 추가
    strategy = sa_data.get("orchestration_strategy", "")
    if strategy:
        senior.description += f"\n\n오케스트레이션 전략: {strategy}"

    improvement = opt_data.get("improvement_notes", "")
    if improvement:
        senior.description += f"\n개선 효과: {improvement}"

    # ── 오케스트레이션 흐름 ──
    senior.orchestration_flow = _build_orchestration_flow(
        as_is_sheet, junior_agents, human_steps
    )

    # orchestration_flow가 비어있으면 순차 흐름 생성
    if not senior.orchestration_flow:
        senior.orchestration_flow = _build_sequential_flow(junior_agents, human_steps)

    # ── 실행 스텝 ──
    execution_steps = _build_execution_steps(senior)

    # ── React Flow ──
    react_flow = _generate_react_flow(senior, as_is_sheet)

    # ── 요약 ──
    summary = _build_summary(senior, classified_nodes)

    # LLM 최적화 정보 추가
    if opt_data:
        summary["optimization"] = {
            "parallel_opportunities": opt_data.get("parallel_opportunities", []),
            "sequential_dependencies": opt_data.get("sequential_dependencies", []),
            "improvement_notes": improvement,
        }

    return ToBeWorkflow(
        senior_agent=senior,
        execution_steps=execution_steps,
        react_flow=react_flow,
        summary=summary,
    )


# ── To-Be 생성 (규칙 기반 fallback) ──────────────────────────────────────────

def generate_tobe(
    as_is_sheet: WorkflowSheet,
    classification_results: dict[str, dict],
    process_name: str = "",
) -> ToBeWorkflow:
    """규칙 기반 To-Be Workflow 생성 (LLM fallback)."""
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

    # 5. Senior Agent 정의
    senior = SeniorAgent(
        id="senior-ai-1",
        name=f"{process_name or as_is_sheet.name} Senior AI Orchestrator",
        junior_agents=junior_agents,
        human_steps=human_steps,
        description=(
            f"신규 생성된 오케스트레이터 Agent입니다. "
            f"{len(junior_agents)}개 Junior AI Agent의 실행 순서를 관리하고, "
            f"각 Agent 간 산출물 정합성을 검증하며, "
            f"Human 수행 단계({len(human_steps)}건)로의 핸드오프를 제어합니다."
        ),
    )

    # 6. 오케스트레이션 흐름
    senior.orchestration_flow = _build_orchestration_flow(
        as_is_sheet, junior_agents, human_steps
    )
    if not senior.orchestration_flow:
        senior.orchestration_flow = _build_sequential_flow(junior_agents, human_steps)

    # 7. 실행 스텝
    execution_steps = _build_execution_steps(senior)

    # 8. React Flow JSON
    react_flow = _generate_react_flow(senior, as_is_sheet)

    # 9. 요약
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

    # 워크플로우 노드가 있으면 노드 기반 매핑
    if sheet.nodes:
        for node in sorted(sheet.nodes.values(), key=lambda n: (n.y, n.x)):
            if node.level not in ("L4", "L5"):
                continue
            cr = results.get(node.task_id, {})
            if not cr:
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
    else:
        # 노드가 없으면 분류 결과 기반으로 직접 생성
        for tid, cr in sorted(results.items(), key=lambda x: _natural_sort_key(x[0])):
            classified.append({
                "node_id": tid,
                "task_id": tid,
                "label": cr.get("task_name", tid),
                "level": "L5" if tid.count(".") >= 3 else "L4",
                "classification": cr.get("label", "미분류"),
                "reason": cr.get("reason", ""),
                "hybrid_note": cr.get("hybrid_note", ""),
                "input_types": cr.get("input_types", ""),
                "output_types": cr.get("output_types", ""),
            })

    return classified


def _natural_sort_key(s: str) -> list:
    parts = re.split(r'(\d+)', s)
    return [int(p) if p.isdigit() else p for p in parts if p]


def _split_hybrid_tasks(classified_nodes: list[dict]) -> list[dict]:
    """AI+Human 태스크를 AI 파트와 Human 파트로 분할합니다."""
    split = []
    for node in classified_nodes:
        if node["classification"] == "AI + Human":
            ai_part, human_part = _parse_hybrid_note(node["hybrid_note"])
            split.append({
                **node,
                "split_type": "ai_part",
                "split_label": f"{node['label']} (AI)",
                "split_description": ai_part or "데이터 수집/분석/초안 작성",
            })
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
    if not note:
        return "", ""
    ai_match = re.search(r'AI\s*파트[:\s]*([^/]+)', note)
    human_match = re.search(r'Human\s*파트[:\s]*(.+)', note)
    return (
        ai_match.group(1).strip() if ai_match else "",
        human_match.group(1).strip() if human_match else "",
    )


def _group_junior_agents(
    sheet: WorkflowSheet,
    split_tasks: list[dict],
    classification_results: dict[str, dict],
) -> list[JuniorAgent]:
    """같은 L4 내에서 연속 AI L5 태스크를 Junior Agent로 묶습니다."""
    if not split_tasks:
        return []

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
        return cls == "AI 수행 가능" or (cls == "AI + Human" and split_type == "ai_part")

    def _l4_id_of(task: dict) -> str:
        tid = task.get("task_id", "")
        parts = tid.split(".")
        if len(parts) >= 4:
            return ".".join(parts[:4])
        return tid

    # L4별로 L5 태스크 그루핑
    l4_groups: dict[str, list[dict]] = defaultdict(list)
    standalone: list[dict] = []

    for task in split_tasks:
        if task.get("level") == "L5":
            l4_groups[_l4_id_of(task)].append(task)
        elif _is_ai_capable(task):
            standalone.append(task)

    # 각 L4 내에서 연속 AI 태스크 묶기
    all_groups: list[list[dict]] = []
    for l4_id in sorted(l4_groups.keys(), key=lambda k: _task_sort_key(l4_groups[k][0])):
        tasks_in_l4 = sorted(l4_groups[l4_id], key=_task_sort_key)
        current_group: list[dict] = []
        for task in tasks_in_l4:
            if _is_ai_capable(task):
                current_group.append(task)
            else:
                if current_group:
                    all_groups.append(current_group)
                    current_group = []
        if current_group:
            all_groups.append(current_group)

    # Junior Agent 생성
    agents: list[JuniorAgent] = []
    agent_idx = 1

    for group_tasks in all_groups:
        agent_tasks = [
            AgentTask(
                task_id=t["task_id"],
                label=t.get("split_label", t["label"]),
                classification=t["classification"],
                reason=t.get("reason", ""),
                ai_part=t.get("split_description", ""),
                technique=_infer_single_technique(t),
                node_id=t["node_id"],
            )
            for t in group_tasks
        ]
        technique = _infer_technique(group_tasks, classification_results)
        first_label = group_tasks[0]["label"].split("(")[0].strip()
        name = (f"Agent {agent_idx}: {first_label} 외 {len(group_tasks)-1}건"
                if len(group_tasks) > 1
                else f"Agent {agent_idx}: {first_label}")

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

    for task in standalone:
        agents.append(JuniorAgent(
            id=f"junior-ai-{agent_idx}",
            name=f"Agent {agent_idx}: {task['label'].split('(')[0].strip()}",
            tasks=[AgentTask(
                task_id=task["task_id"],
                label=task.get("split_label", task["label"]),
                classification=task["classification"],
                reason=task.get("reason", ""),
                ai_part=task.get("split_description", ""),
                technique=_infer_single_technique(task),
                node_id=task["node_id"],
            )],
            technique=_infer_technique([task], classification_results),
            input_types=task.get("input_types", ""),
            output_types=task.get("output_types", ""),
            description="단독 L4 태스크 처리",
        ))
        agent_idx += 1

    return agents


def _infer_single_technique(task: dict) -> str:
    """개별 태스크의 AI 기법을 추론합니다."""
    text = (task.get("label", "") + " " + task.get("reason", "")).lower()
    techniques = []
    if any(kw in text for kw in ["수집", "조사", "검색", "외부", "크롤링"]):
        techniques.append("RAG")
    if any(kw in text for kw in ["작성", "생성", "초안", "보고서", "요약"]):
        techniques.append("LLM")
    if any(kw in text for kw in ["분석", "통계", "수치", "집계"]):
        techniques.append("Tabular 분석")
    if any(kw in text for kw in ["분류", "매핑", "규칙"]):
        techniques.append("규칙 기반")
    if any(kw in text for kw in ["유사", "매칭", "추천"]):
        techniques.append("임베딩 유사도")
    if any(kw in text for kw in ["군집", "그룹", "클러스터"]):
        techniques.append("Clustering")
    return " + ".join(techniques) if techniques else "LLM"


def _infer_technique(
    tasks: list[dict],
    classification_results: dict[str, dict],
) -> str:
    """태스크 그룹의 대표 AI 기법을 추론합니다."""
    all_techniques = set()
    for t in tasks:
        tech = _infer_single_technique(t)
        all_techniques.update(tech.split(" + "))
    return " + ".join(sorted(all_techniques)) if all_techniques else "LLM"


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
        elif task["classification"] == "AI + Human" and task.get("split_type") == "human_part":
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
    node_to_agent: dict[str, str] = {}
    for agent in junior_agents:
        for task in agent.tasks:
            node_to_agent[task.node_id] = agent.id
    for hs in human_steps:
        node_to_agent[hs.node_id] = hs.id

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


def _build_sequential_flow(
    junior_agents: list[JuniorAgent],
    human_steps: list[HumanStep],
) -> list[dict]:
    """오케스트레이션 흐름이 없을 때 순차 흐름을 생성합니다."""
    flow = []
    step = 1
    for agent in junior_agents:
        flow.append({
            "step": step,
            "is_parallel": False,
            "agents": [agent.id],
        })
        step += 1
    for hs in human_steps:
        flow.append({
            "step": step,
            "is_parallel": False,
            "agents": [hs.id],
        })
        step += 1
    return flow


def _build_execution_steps(senior: SeniorAgent) -> list[dict]:
    """To-Be 실행 스텝을 생성합니다."""
    steps = []
    step_num = 1
    for flow_step in senior.orchestration_flow:
        agents_in_step = []
        for agent_id in flow_step["agents"]:
            junior = next((j for j in senior.junior_agents if j.id == agent_id), None)
            if junior:
                agents_in_step.append({
                    "type": "junior_ai",
                    "agent_id": junior.id,
                    "agent_name": junior.name,
                    "technique": junior.technique,
                    "description": junior.description,
                    "senior_instruction": junior.senior_instruction,
                    "tasks": [
                        {
                            "task_id": t.task_id,
                            "label": t.label,
                            "technique": t.technique,
                        }
                        for t in junior.tasks
                    ],
                })
                continue
            human = next((h for h in senior.human_steps if h.id == agent_id), None)
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

    lanes = ["Senior AI", "Junior AI", "Human"]

    LANE_HEIGHT = 300
    NODE_GAP_X = 280
    START_X = 200
    START_Y = 50

    y_offsets = {
        "senior": START_Y,
        "junior": START_Y + LANE_HEIGHT,
        "human": START_Y + LANE_HEIGHT * 2,
    }

    current_x = START_X

    # Senior AI 노드
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

    for step_idx, flow_step in enumerate(senior.orchestration_flow):
        step_node_ids: list[str] = []
        branch_x = current_x

        for agent_id in flow_step["agents"]:
            # Junior Agent
            junior = next((j for j in senior.junior_agents if j.id == agent_id), None)
            if junior:
                jnode_id = f"tobe-{junior.id}"

                # Junior Agent 그룹 노드 (컨테이너)
                task_height = max(len(junior.tasks) * 60, 80)
                nodes.append({
                    "id": jnode_id,
                    "type": "l4",
                    "position": {"x": branch_x, "y": y_offsets["junior"]},
                    "data": {
                        "label": junior.name,
                        "level": "Junior AI",
                        "id": junior.id,
                        "description": junior.description,
                        "agentType": "junior",
                        "technique": junior.technique,
                        "taskCount": junior.task_count,
                        "seniorInstruction": junior.senior_instruction,
                    },
                })
                step_node_ids.append(jnode_id)

                # 하위 태스크 노드
                for ti, task in enumerate(junior.tasks):
                    task_node_id = f"tobe-task-{task.task_id}-{junior.id}-{ti}"
                    nodes.append({
                        "id": task_node_id,
                        "type": "l5",
                        "position": {
                            "x": branch_x + 20,
                            "y": y_offsets["junior"] + 80 + ti * 60,
                        },
                        "data": {
                            "label": task.label,
                            "level": "L5",
                            "id": task.task_id,
                            "description": task.ai_part,
                            "classification": task.classification,
                            "technique": task.technique,
                        },
                    })
                    # 태스크 간 순차 엣지
                    if ti == 0:
                        edges.append({
                            "id": f"e-{jnode_id}-{task_node_id}",
                            "source": jnode_id,
                            "target": task_node_id,
                            "type": "smoothstep",
                            "animated": False,
                            "style": {"stroke": "#f2a0af", "strokeWidth": 1.5},
                            "markerEnd": {"type": "arrowclosed", "color": "#f2a0af"},
                        })
                    else:
                        prev_task_id = f"tobe-task-{junior.tasks[ti-1].task_id}-{junior.id}-{ti-1}"
                        edges.append({
                            "id": f"e-{prev_task_id}-{task_node_id}",
                            "source": prev_task_id,
                            "target": task_node_id,
                            "type": "smoothstep",
                            "animated": False,
                            "style": {"stroke": "#f2a0af", "strokeWidth": 1.5},
                            "markerEnd": {"type": "arrowclosed", "color": "#f2a0af"},
                        })

                branch_x += NODE_GAP_X
                continue

            # Human 노드
            human = next((h for h in senior.human_steps if h.id == agent_id), None)
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

        # 이전 스텝 → 현재 스텝 엣지
        for snid in step_node_ids:
            for prev_id in prev_step_node_ids:
                edge_label = ""
                if prev_id == senior_node_id:
                    # Senior → Junior: 기동 지시 라벨
                    junior = next((j for j in senior.junior_agents if f"tobe-{j.id}" == snid), None)
                    if junior and junior.senior_instruction:
                        edge_label = junior.senior_instruction[:30]
                    else:
                        edge_label = "기동 지시"
                edges.append({
                    "id": f"e-{prev_id}-{snid}",
                    "source": prev_id,
                    "target": snid,
                    "type": "smoothstep",
                    "animated": True,
                    "style": {"stroke": "#a62121", "strokeWidth": 2.5},
                    "markerEnd": {"type": "arrowclosed", "color": "#a62121"},
                    "label": edge_label,
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
                "description": j.description,
                "senior_instruction": j.senior_instruction,
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "label": t.label,
                        "technique": t.technique,
                    }
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
