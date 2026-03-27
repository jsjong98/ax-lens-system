"""
project_design_generator.py — 과제 설계서 자동 생성기

분류 결과 + To-Be Workflow 결과를 기반으로
과제 설계서를 LLM(Claude)으로 생성합니다.

과제 설계서 구조:
  7. AI Service Flow — To-Be Workflow (Senior AI, Junior AI, HR 담당자)
  8. AI 기술 유형 — 체크박스 + 기술 이름
  9. Input / Output — 내부/외부 Input + Output
  별첨. Agent 정의서 (향후 확장)
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any


# ── 데이터 모델 ───────────────────────────────────────────────────────────────

@dataclass
class AIServiceFlowStep:
    """AI Service Flow의 개별 단계."""
    step_order: int
    step_name: str
    actor: str          # "Input" | "Senior AI" | "Junior AI" | "HR 담당자"
    description: str = ""
    sub_steps: list[str] = field(default_factory=list)


@dataclass
class AIServiceFlow:
    """7. AI Service Flow 전체."""
    steps: list[AIServiceFlowStep] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)   # 최상단 Input 데이터 목록


@dataclass
class AITechType:
    """AI 기술 유형 카테고리."""
    category: str                    # "생성형 모델", "판별·예측 모델" 등
    sub_types: list[str] = field(default_factory=list)      # 하위 유형 전체 목록
    checked: list[str] = field(default_factory=list)        # 체크된 항목들


@dataclass
class AITechInfo:
    """8. AI 기술 유형 전체."""
    tech_types: list[AITechType] = field(default_factory=list)
    tech_names: list[str] = field(default_factory=list)     # 구체적 기술 이름


@dataclass
class InputOutput:
    """9. Input / Output."""
    input_internal: list[str] = field(default_factory=list)   # 내부 Input
    input_external: list[str] = field(default_factory=list)   # 외부 Input
    output: list[str] = field(default_factory=list)


@dataclass
class ProcessingStep:
    """처리 로직의 개별 단계 (방법론 및 주요 기술)."""
    step_number: int
    step_name: str               # 예: "모니터링 전략 수립 (키워드·소스·주기 설정)"
    method: str                  # 예: "LLM 기반 전략 추론"
    result: str                  # 예: "Junior AI 실행 지시"


@dataclass
class AgentDefinition:
    """별첨: Agent 정의서 (Agent별 1장)."""
    agent_id: str
    agent_name: str
    agent_type: str = ""                                       # "Senior AI" | "Junior AI"
    roles: list[str] = field(default_factory=list)             # Agent 역할 (bullet 리스트)
    # 처리 로직
    input_data: list[str] = field(default_factory=list)        # Input 상세 목록
    processing_steps: list[ProcessingStep] = field(default_factory=list)  # 방법론 및 주요 기술
    output_data: list[str] = field(default_factory=list)       # Output 상세 목록
    # Service Flow 내 위치 (미니맵용)
    flow_step_orders: list[int] = field(default_factory=list)  # 이 Agent가 담당하는 flow step 순서


@dataclass
class ProjectDesign:
    """과제 설계서 전체."""
    project_title: str = ""
    ai_service_flow: AIServiceFlow = field(default_factory=AIServiceFlow)
    ai_tech_info: AITechInfo = field(default_factory=AITechInfo)
    input_output: InputOutput = field(default_factory=InputOutput)
    agent_definitions: list[AgentDefinition] = field(default_factory=list)


# ── 기본 AI 기술 유형 카테고리 정의 ────────────────────────────────────────────

DEFAULT_TECH_CATEGORIES = [
    AITechType(
        category="생성형 모델",
        sub_types=["텍스트 생성", "요약·재작성·질의응답", "멀티모달 생성·이해", "정보 추출"],
        checked=[],
    ),
    AITechType(
        category="판별·예측 모델",
        sub_types=["예측", "군집·분류", "추천·랭킹"],
        checked=[],
    ),
    AITechType(
        category="인식 모델",
        sub_types=["OCR", "음성 인식"],
        checked=[],
    ),
    AITechType(
        category="의사결정·최적화 모델",
        sub_types=["최적화"],
        checked=[],
    ),
    AITechType(
        category="자동화",
        sub_types=["RPA"],
        checked=[],
    ),
]


def project_design_to_dict(pd: ProjectDesign) -> dict:
    """ProjectDesign → JSON-serializable dict."""
    return {
        "project_title": pd.project_title,
        "ai_service_flow": {
            "inputs": pd.ai_service_flow.inputs,
            "steps": [
                {
                    "step_order": s.step_order,
                    "step_name": s.step_name,
                    "actor": s.actor,
                    "description": s.description,
                    "sub_steps": s.sub_steps,
                }
                for s in pd.ai_service_flow.steps
            ],
        },
        "ai_tech_info": {
            "tech_types": [
                {
                    "category": t.category,
                    "sub_types": t.sub_types,
                    "checked": t.checked,
                }
                for t in pd.ai_tech_info.tech_types
            ],
            "tech_names": pd.ai_tech_info.tech_names,
        },
        "input_output": {
            "input_internal": pd.input_output.input_internal,
            "input_external": pd.input_output.input_external,
            "output": pd.input_output.output,
        },
        "agent_definitions": [
            {
                "agent_id": a.agent_id,
                "agent_name": a.agent_name,
                "agent_type": a.agent_type,
                "roles": a.roles,
                "input_data": a.input_data,
                "processing_steps": [
                    {
                        "step_number": ps.step_number,
                        "step_name": ps.step_name,
                        "method": ps.method,
                        "result": ps.result,
                    }
                    for ps in a.processing_steps
                ],
                "output_data": a.output_data,
                "flow_step_orders": a.flow_step_orders,
            }
            for a in pd.agent_definitions
        ],
    }


# ── LLM 프롬프트 ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """당신은 PwC의 HR 디지털 전환 아키텍트입니다.
AI 업무 자동화 분류 결과와 To-Be Workflow 설계 결과를 바탕으로
과제 설계서를 작성합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【사고 과정】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step A. AI Service Flow 설계
  — To-Be Workflow에서 각 단계를 수행 주체(Input/Senior AI/Junior AI/HR 담당자)별로 분류합니다.
  — Senior AI는 전략 수립·모니터링 등 오케스트레이션 역할입니다.
  — Junior AI는 데이터 수집·분석·생성 등 실행 역할입니다.
  — HR 담당자는 검토·승인·최종 의사결정 역할입니다.
  — Input은 워크플로우에 들어가는 초기 데이터/자료입니다.

Step B. AI 기술 유형 분석
  — 각 AI Agent가 사용하는 기술을 분석하여 아래 카테고리에서 체크합니다.
  — 카테고리:
    1) 생성형 모델: 텍스트 생성 / 요약·재작성·질의응답 / 멀티모달 생성·이해 / 정보 추출
    2) 판별·예측 모델: 예측 / 군집·분류 / 추천·랭킹
    3) 인식 모델: OCR / 음성 인식
    4) 의사결정·최적화 모델: 최적화
    5) 자동화: RPA
  — 구체적인 기술 이름도 나열합니다 (예: Web Crawling, RAG, LLM, Topic Modeling 등).

Step C. Input/Output 정의
  — 내부 Input: 사내 시스템·데이터·문서 등
  — 외부 Input: 외부 매체·DB·API 등
  — Output: 최종 산출물

Step D. Agent 정의서 (별첨) — Agent별 1장씩 상세 작성
  — 각 Agent에 대해:
    1) Agent 개요: Agent 명, 유형(Senior/Junior AI), 역할(구체적 bullet 리스트)
    2) 처리 로직:
       - Input: 이 Agent가 받는 구체적 데이터/자료 목록 (괄호로 부연 설명)
       - 방법론 및 주요 기술: 번호별 단계명 + 사용 기법 → 산출물
       - Output: 이 Agent가 생성하는 구체적 산출물 목록
    3) flow_step_orders: 이 Agent가 담당하는 AI Service Flow의 step_order 번호들

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【출력 형식】 — 반드시 아래 JSON 형식만 출력하세요 (마크다운 코드블록 허용)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```json
{
  "ai_service_flow": {
    "inputs": ["외부 HRD 매체", "학술 DB", "자사 교육 체계 현황 데이터"],
    "steps": [
      {
        "step_order": 1,
        "step_name": "모니터링 전략 수립",
        "actor": "Senior AI",
        "description": "키워드, 소스, 주기를 설정",
        "sub_steps": ["키워드 설정", "소스 선정", "주기 결정"]
      },
      {
        "step_order": 2,
        "step_name": "외부 소스 자동 크롤링·수집",
        "actor": "Junior AI",
        "description": "외부 HRD 매체에서 자동으로 데이터 수집"
      }
    ]
  },
  "ai_tech_info": {
    "tech_types": [
      {
        "category": "생성형 모델",
        "checked": ["정보 추출", "텍스트 생성"]
      },
      {
        "category": "판별·예측 모델",
        "checked": ["군집·분류"]
      },
      {
        "category": "인식 모델",
        "checked": []
      },
      {
        "category": "의사결정·최적화 모델",
        "checked": []
      },
      {
        "category": "자동화",
        "checked": []
      }
    ],
    "tech_names": ["Web Crawling/Scraping", "RAG", "LLM", "Topic Modeling", "Embedding 기반 유사도 분석"]
  },
  "input_output": {
    "input_internal": ["자사 교육 체계 현황", "기존 벤치마킹 이력"],
    "input_external": ["외부 HRD 매체(ATD, SHRM)", "학술 DB"],
    "output": ["벤치마킹 내용 및 Implication 보고서", "벤치마킹 질문 리스트"]
  },
  "agent_definitions": [
    {
      "agent_id": "senior-1",
      "agent_name": "HRD 트렌드 전략 오케스트레이터",
      "agent_type": "Senior AI",
      "roles": [
        "외부 HRD 트렌드 수집 전략(키워드·소스·주기) 수립",
        "수집·분류된 트렌드와 자사 교육 체계 간 Gap 분석",
        "벤치마킹 전략 방향성 도출 및 Junior AI 실행 오케스트레이션"
      ],
      "input_data": [
        "자사 교육 체계 현황 (과정 목록, 역량 모델, 체계도)",
        "Junior AI 분류 결과 (주제별 라벨링)",
        "벤치마킹 이력 및 경영진 방침"
      ],
      "processing_steps": [
        {
          "step_number": 1,
          "step_name": "모니터링 전략 수립",
          "method": "LLM 전략 추론",
          "result": "Junior AI 지시"
        },
        {
          "step_number": 2,
          "step_name": "트렌드·자사 Gap 분석",
          "method": "Embedding 유사도",
          "result": "Gap 우선순위"
        },
        {
          "step_number": 3,
          "step_name": "벤치마킹 방향성 도출",
          "method": "LLM 종합 분석",
          "result": "중점 영역 기준"
        }
      ],
      "output_data": [
        "모니터링 전략서 (키워드, 소스, 주기)",
        "Gap 분석 리포트 (영역, 유사도, 순위)",
        "벤치마킹 방향성 (중점 영역, 대상)"
      ],
      "flow_step_orders": [1, 4]
    },
    {
      "agent_id": "junior-1",
      "agent_name": "외부 트렌드 수집·분석 Agent",
      "agent_type": "Junior AI",
      "roles": [
        "외부 HRD 매체/학술 DB에서 트렌드 데이터 자동 크롤링·수집",
        "수집된 데이터의 주제별 분류 및 요약 생성"
      ],
      "input_data": [
        "Senior AI 전략 (키워드, 소스, 주기)",
        "외부 HRD 매체 URL 목록"
      ],
      "processing_steps": [
        {
          "step_number": 1,
          "step_name": "외부 소스 크롤링·수집",
          "method": "Web Crawling",
          "result": "원문 데이터"
        },
        {
          "step_number": 2,
          "step_name": "트렌드 요약 생성",
          "method": "LLM + Topic Model",
          "result": "트렌드 브리핑"
        }
      ],
      "output_data": [
        "원문 데이터 (출처 포함)",
        "트렌드 분류·요약 브리핑"
      ],
      "flow_step_orders": [2, 3]
    }
  ]
}
```

【주의사항】
- ai_service_flow.steps는 워크플로우 순서대로 나열하세요.
- actor는 반드시 "Input", "Senior AI", "Junior AI", "HR 담당자" 중 하나입니다.
- tech_types의 category는 5개 고정 카테고리만 사용하세요.
- checked에는 해당 카테고리의 sub_types 중 실제 사용되는 것만 넣으세요.
- tech_names에는 구체적 기술·프레임워크 이름을 넣으세요.
- input_output의 내부/외부를 명확히 구분하세요.
- agent_definitions에는 Senior AI, Junior AI 모두 포함하세요.
- agent_definitions의 roles는 이 Agent가 하는 역할을 구체적 bullet 리스트로 작성하세요. (최대 3~4개)
- agent_definitions의 input_data는 **최대 3~4개 항목**으로 유사한 것끼리 묶어서 작성하세요.
  예: "자사 교육 체계 현황 (과정 목록, 역량 모델, 교육 체계도)" ← 이렇게 괄호 안에 세부사항을 나열.
  절대 10개 이상 나열하지 마세요. 유사한 항목은 반드시 하나로 통합하세요.
- agent_definitions의 output_data도 **최대 3~4개 항목**으로 묶어서 작성하세요.
  예: "Gap 분석 리포트 (Gap 영역, 유사도 점수, 우선순위)" ← 세부 산출물은 괄호 안에.
- agent_definitions의 processing_steps는 **최대 3~4단계**로 작성하세요.
  step_name은 20자 이내, method는 15자 이내, result는 15자 이내로 간결하게.
- agent_definitions의 flow_step_orders는 이 Agent가 ai_service_flow.steps에서 담당하는 step_order 번호 배열입니다.
"""


def _build_user_prompt(
    tasks: list[dict],
    classification_results: dict[str, dict],
    tobe_data: dict | None,
    process_name: str,
) -> str:
    """LLM에 전달할 사용자 프롬프트를 구성합니다."""
    lines: list[str] = []
    lines.append(f"# 프로세스: {process_name}\n")

    # 분류 통계
    total = len(classification_results)
    ai_count = sum(1 for r in classification_results.values() if r.get("label") == "AI")
    hybrid_count = sum(1 for r in classification_results.values() if r.get("label") == "AI + Human")
    human_count = sum(1 for r in classification_results.values() if r.get("label") == "Human")

    lines.append("## 분류 결과 통계")
    lines.append(f"- 전체 Task: {total}개")
    if total:
        lines.append(f"- AI: {ai_count}개 ({ai_count/total*100:.1f}%)")
        lines.append(f"- AI + Human: {hybrid_count}개 ({hybrid_count/total*100:.1f}%)")
        lines.append(f"- Human: {human_count}개 ({human_count/total*100:.1f}%)")
    lines.append("")

    # Task 목록 + 분류 결과
    lines.append("## L5 Task 목록 및 분류 결과")
    for t in tasks:
        tid = t.get("id", "")
        cr = classification_results.get(tid, {})
        label = cr.get("label", "미분류")
        reason = cr.get("reason", "")
        l4 = t.get("l4", "")
        name = t.get("name", "")
        description = t.get("description", "")

        lines.append(f"- [{tid}] L4={l4} | {name}")
        if description:
            lines.append(f"  설명: {description}")
        lines.append(f"  분류: {label} | 사유: {reason}")
        input_types = cr.get("input_types", "")
        output_types = cr.get("output_types", "")
        if input_types:
            lines.append(f"  Input 유형: {input_types}")
        if output_types:
            lines.append(f"  Output 유형: {output_types}")
    lines.append("")

    # To-Be Workflow 정보
    if tobe_data:
        lines.append("## To-Be Workflow 설계 결과")

        # agents
        agents = tobe_data.get("agents", [])
        if agents:
            lines.append(f"### AI Agent ({len(agents)}개)")
            for agent in agents:
                agent_name = agent.get("agent_name", agent.get("name", ""))
                agent_type = agent.get("agent_type", "")
                technique = agent.get("ai_technique", agent.get("technique", ""))
                desc = agent.get("description", "")
                assigned = agent.get("assigned_tasks", agent.get("tasks", []))
                task_names = []
                for at in assigned:
                    if isinstance(at, dict):
                        task_names.append(at.get("task_name", at.get("label", "")))
                    elif isinstance(at, str):
                        task_names.append(at)

                lines.append(f"- {agent_name} ({agent_type}, 기법: {technique})")
                lines.append(f"  설명: {desc}")
                if task_names:
                    lines.append(f"  담당 Task: {', '.join(task_names)}")

                # input/output 정보
                for at in assigned:
                    if isinstance(at, dict):
                        inp = at.get("input_data", [])
                        out = at.get("output_data", [])
                        if inp:
                            lines.append(f"  Input: {', '.join(inp)}")
                        if out:
                            lines.append(f"  Output: {', '.join(out)}")

        # execution flow
        exec_steps = tobe_data.get("execution_steps", tobe_data.get("execution_flow", []))
        if exec_steps:
            lines.append("### 실행 흐름")
            for step in exec_steps:
                step_label = step.get("label", step.get("step_name", ""))
                step_type = step.get("type", step.get("step_type", ""))
                desc = step.get("description", "")
                lines.append(f"  · {step_label} ({step_type}): {desc}")

        # summary
        summary = tobe_data.get("summary", tobe_data.get("blueprint_summary", ""))
        if summary:
            if isinstance(summary, dict):
                lines.append(f"### 요약: {json.dumps(summary, ensure_ascii=False)}")
            else:
                lines.append(f"### 요약: {summary}")

        lines.append("")

    return "\n".join(lines)


def _parse_llm_response(text: str) -> dict:
    """LLM 응답에서 JSON을 추출합니다."""
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()

    brace_start = text.find("{")
    if brace_start == -1:
        raise ValueError("JSON 응답을 찾을 수 없습니다.")

    depth = 0
    for i in range(brace_start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[brace_start:i + 1])

    return json.loads(text[brace_start:])


def _dict_to_project_design(data: dict, project_title: str = "") -> ProjectDesign:
    """JSON dict → ProjectDesign 변환."""
    # AI Service Flow
    flow_data = data.get("ai_service_flow", {})
    flow_steps = []
    for s in flow_data.get("steps", []):
        flow_steps.append(AIServiceFlowStep(
            step_order=s.get("step_order", 0),
            step_name=s.get("step_name", ""),
            actor=s.get("actor", ""),
            description=s.get("description", ""),
            sub_steps=s.get("sub_steps", []),
        ))

    # AI Tech Info
    tech_data = data.get("ai_tech_info", {})
    tech_types = []
    for t in tech_data.get("tech_types", []):
        category = t.get("category", "")
        checked = t.get("checked", [])
        # 기본 카테고리에서 sub_types 가져오기
        default = next((d for d in DEFAULT_TECH_CATEGORIES if d.category == category), None)
        sub_types = default.sub_types if default else t.get("sub_types", [])
        tech_types.append(AITechType(
            category=category,
            sub_types=sub_types,
            checked=checked,
        ))

    # 누락된 카테고리 추가
    existing_cats = {t.category for t in tech_types}
    for default_cat in DEFAULT_TECH_CATEGORIES:
        if default_cat.category not in existing_cats:
            tech_types.append(AITechType(
                category=default_cat.category,
                sub_types=default_cat.sub_types,
                checked=[],
            ))

    # Input/Output
    io_data = data.get("input_output", {})

    # Agent Definitions
    agent_defs = []
    for a in data.get("agent_definitions", []):
        # processing_steps 파싱
        p_steps = []
        for ps in a.get("processing_steps", []):
            p_steps.append(ProcessingStep(
                step_number=ps.get("step_number", 0),
                step_name=ps.get("step_name", ""),
                method=ps.get("method", ""),
                result=ps.get("result", ""),
            ))

        agent_defs.append(AgentDefinition(
            agent_id=a.get("agent_id", ""),
            agent_name=a.get("agent_name", ""),
            agent_type=a.get("agent_type", ""),
            roles=a.get("roles", []),
            input_data=a.get("input_data", []),
            processing_steps=p_steps,
            output_data=a.get("output_data", []),
            flow_step_orders=a.get("flow_step_orders", []),
        ))

    return ProjectDesign(
        project_title=project_title,
        ai_service_flow=AIServiceFlow(
            inputs=flow_data.get("inputs", []),
            steps=flow_steps,
        ),
        ai_tech_info=AITechInfo(
            tech_types=tech_types,
            tech_names=tech_data.get("tech_names", []),
        ),
        input_output=InputOutput(
            input_internal=io_data.get("input_internal", []),
            input_external=io_data.get("input_external", []),
            output=io_data.get("output", []),
        ),
        agent_definitions=agent_defs,
    )


# ── LLM 호출 ─────────────────────────────────────────────────────────────────

async def generate_project_design_with_llm(
    tasks: list[dict],
    classification_results: dict[str, dict],
    tobe_data: dict | None = None,
    process_name: str = "HR 프로세스",
    project_title: str = "",
    api_key: str = "",
    model: str = "claude-sonnet-4-6",
) -> ProjectDesign:
    """Claude LLM을 사용하여 과제 설계서를 생성합니다."""
    import anthropic

    api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("Anthropic API 키가 설정되지 않았습니다.")

    user_prompt = _build_user_prompt(tasks, classification_results, tobe_data, process_name)

    client = anthropic.AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.3,
    )

    text = response.content[0].text
    parsed = _parse_llm_response(text)
    return _dict_to_project_design(parsed, project_title=project_title)


# ── Fallback: 규칙 기반 생성 ──────────────────────────────────────────────────

def generate_project_design_fallback(
    tasks: list[dict],
    classification_results: dict[str, dict],
    tobe_data: dict | None = None,
    process_name: str = "HR 프로세스",
    project_title: str = "",
) -> ProjectDesign:
    """LLM 없이 규칙 기반으로 과제 설계서를 생성합니다."""

    # Agent 정보 추출 (tobe_data에서)
    agents_raw = tobe_data.get("agents", []) if tobe_data else []
    agent_defs: list[AgentDefinition] = []
    all_techniques: set[str] = set()
    all_input: set[str] = set()
    all_output: set[str] = set()

    for idx, a in enumerate(agents_raw):
        technique = a.get("ai_technique", a.get("technique", "LLM"))
        all_techniques.add(technique)
        assigned = a.get("assigned_tasks", a.get("tasks", []))
        task_names = []
        inp_data = []
        out_data = []
        for at in assigned:
            if isinstance(at, dict):
                task_names.append(at.get("task_name", at.get("label", "")))
                inp_data.extend(at.get("input_data", []))
                out_data.extend(at.get("output_data", []))
        all_input.update(inp_data)
        all_output.update(out_data)

        desc = a.get("description", "")
        agent_defs.append(AgentDefinition(
            agent_id=a.get("agent_id", a.get("id", "")),
            agent_name=a.get("agent_name", a.get("name", "")),
            agent_type=a.get("agent_type", "Junior AI"),
            roles=[desc] if desc else task_names,
            input_data=inp_data if inp_data else ["업무 데이터"],
            processing_steps=[
                ProcessingStep(
                    step_number=i + 1,
                    step_name=tn,
                    method=technique,
                    result="처리 결과",
                )
                for i, tn in enumerate(task_names)
            ],
            output_data=out_data if out_data else ["처리 결과"],
            flow_step_orders=[idx + 2],
        ))

    # Flow steps 기본 생성
    steps = [
        AIServiceFlowStep(1, "전략 수립 및 오케스트레이션", "Senior AI", "전체 워크플로우 조율"),
    ]
    for i, ad in enumerate(agent_defs):
        if ad.agent_type != "Senior AI":
            steps.append(AIServiceFlowStep(
                i + 2, ad.agent_name, "Junior AI", ad.roles[0] if ad.roles else "",
            ))
    steps.append(AIServiceFlowStep(
        len(steps) + 1, "검토 및 최종 승인", "HR 담당자", "결과물 검토 및 승인",
    ))

    # 기본 체크 추론
    checked_gen = []
    technique_str = " ".join(all_techniques).lower()
    if any(k in technique_str for k in ["llm", "gpt", "생성", "텍스트"]):
        checked_gen.append("텍스트 생성")
    if any(k in technique_str for k in ["rag", "요약", "qa", "질의"]):
        checked_gen.append("요약·재작성·질의응답")
    if any(k in technique_str for k in ["추출", "extract"]):
        checked_gen.append("정보 추출")

    checked_pred = []
    if any(k in technique_str for k in ["분류", "클러스터", "군집", "classif"]):
        checked_pred.append("군집·분류")
    if any(k in technique_str for k in ["추천", "랭킹", "recommend"]):
        checked_pred.append("추천·랭킹")

    tech_types = [
        AITechType("생성형 모델", ["텍스트 생성", "요약·재작성·질의응답", "멀티모달 생성·이해", "정보 추출"], checked_gen),
        AITechType("판별·예측 모델", ["예측", "군집·분류", "추천·랭킹"], checked_pred),
        AITechType("인식 모델", ["OCR", "음성 인식"], []),
        AITechType("의사결정·최적화 모델", ["최적화"], []),
        AITechType("자동화", ["RPA"], []),
    ]

    return ProjectDesign(
        project_title=project_title or f"{process_name} AI 자동화",
        ai_service_flow=AIServiceFlow(
            inputs=list(all_input)[:5] if all_input else ["업무 데이터"],
            steps=steps,
        ),
        ai_tech_info=AITechInfo(
            tech_types=tech_types,
            tech_names=list(all_techniques) or ["LLM"],
        ),
        input_output=InputOutput(
            input_internal=list(all_input)[:5] if all_input else ["사내 시스템 데이터"],
            input_external=["외부 데이터 소스"],
            output=list(all_output)[:5] if all_output else ["AI 분석 결과 보고서"],
        ),
        agent_definitions=agent_defs,
    )
