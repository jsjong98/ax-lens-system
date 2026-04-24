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
class InputSource:
    """업무 수행에 필요한 입력 데이터/자료원."""
    id: str
    name: str               # 입력 자료명 (예: "ERP 시스템 데이터", "교육 니즈 설문")
    source_type: str = ""   # 시스템, 문서, 외부데이터, 구두/메일 등
    description: str = ""
    related_task_ids: list[str] = field(default_factory=list)


@dataclass
class AgentTask:
    """Agent가 처리하는 개별 태스크."""
    task_id: str
    label: str
    classification: str     # "AI" | "AI + Human" | "Human"
    reason: str = ""
    ai_part: str = ""       # AI+Human일 때 AI가 하는 부분
    human_part: str = ""    # AI+Human일 때 사람이 하는 부분
    hybrid_note: str = ""
    technique: str = ""     # 개별 태스크의 AI 기법
    ai_tech_category: str = ""   # AI 기술 대분류 (생성형 모델, 판별·예측 모델 등)
    ai_tech_type: str = ""       # AI 기술 세부유형 (텍스트 생성, 군집·분류 등)
    node_id: str = ""       # 원본 워크플로우 노드 ID


@dataclass
class JuniorAgent:
    """순차 파이프라인을 처리하는 Junior AI Agent."""
    id: str
    name: str
    tasks: list[AgentTask] = field(default_factory=list)
    technique: str = ""     # LLM, RAG, Clustering, 규칙 기반 등
    ai_tech_category: str = ""   # AI 기술 대분류
    ai_tech_type: str = ""       # AI 기술 세부유형
    input_types: str = ""
    output_types: str = ""
    input_sources: list[InputSource] = field(default_factory=list)
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
    """Senior AI orchestrator — 오케스트레이션 역할 메타데이터.
    워크플로우 구조적 복잡도(Q1/Q2/Q3) 판단에서 필요할 때만 생성됨.
    """
    id: str
    name: str
    description: str = ""
    orchestration_strategy: str = ""


@dataclass
class ToBeWorkflow:
    """To-Be Workflow 전체 — Junior/Human/Input 은 항상 존재, Senior 는 선택."""
    process_name: str = ""
    junior_agents: list[JuniorAgent] = field(default_factory=list)
    human_steps: list[HumanStep] = field(default_factory=list)
    input_sources: list[InputSource] = field(default_factory=list)
    orchestration_flow: list[dict] = field(default_factory=list)
    senior_agent: SeniorAgent | None = None
    execution_steps: list[dict] = field(default_factory=list)
    react_flow: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)

    @property
    def total_junior_tasks(self) -> int:
        return sum(j.task_count for j in self.junior_agents)


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

Step B. 입력 데이터(Input) 식별
  — 각 업무 묶음이 수행되려면 어떤 입력 데이터/자료가 필요한지 식별합니다.
  — 입력 유형: 시스템 데이터, 문서/서류, 외부 데이터, 구두/메일 요청 등
  — 동일 입력이 여러 Agent에서 사용될 수 있습니다 (중복 허용).

Step C. 역할 분담 설계
  — 실제 회사에서 사원·주임급 직원이 여러 개의 세부 업무를 순차적으로 처리하듯이,
    Junior AI Agent 하나가 여러 L5 태스크를 순서대로 처리하는 것이 자연스러운지 판단합니다.
  — 사람이 중간에 개입해야 하는 업무(검토·승인·판단)가 있으면 그 지점에서 끊습니다.

Step D. AI 기술 유형 매칭
  — 각 태스크의 특성을 보고 아래 【AI 기술 유형 분류 체계】에서
    가장 적합한 "대분류 > 세부유형"을 선택합니다.
  — 하나의 태스크에 여러 기술이 조합될 수 있습니다.

Step E. 오케스트레이션 전략
  — Senior AI가 각 Junior Agent를 어떤 순서로 기동하고,
    Agent 간 산출물을 어떻게 전달할지 전략을 수립합니다.
  — 독립적인 Agent끼리는 병렬 수행이 가능한지 검토합니다.

위 사고 과정을 거친 뒤, 최종 결과만 JSON으로 출력하세요.
(사고 과정 자체는 출력하지 마세요)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【4대 범위 정의】 — To-Be 워크플로우의 구성 요소
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ Input (입력 데이터/자료)
  - 업무 수행에 필요한 입력 데이터, 문서, 시스템 정보 등
  - 각 Junior Agent 또는 Human이 업무를 시작하기 위해 받아야 하는 자료
  - 예: ERP 데이터, 설문 결과, 규정 문서, 외부 벤치마크 자료, 이전 단계 산출물

■ Senior AI Agent (Orchestrator) = 대리·과장급 관리자 — **선택적으로 생성**
  - 워크플로우의 구조적 복잡도를 보고 **필요할 때만** 생성 (아래 Q1/Q2/Q3 판단)
  - As-Is에 없던 새로운 엔티티로 신규 생성
  - 팀장이 팀원들에게 업무를 배분하고 진행 상황을 관리하듯이,
    모든 Junior Agent의 실행 순서를 관리
  - Junior Agent 간 산출물 전달 및 정합성 검증
  - Human 수행 단계로의 핸드오프 제어
  - 각 Junior Agent에게 기동 지시(어떤 범위와 기준으로 수행할지) 전달

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【🔑 Senior AI 생성 여부 판단 — 매우 중요】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Senior AI는 항상 만들지 않습니다.** 아래 3가지 질문을 평가한 뒤 **하나라도 Yes** 이면
Senior AI 를 생성하고, **세 가지 모두 No** 이면 Senior AI 를 **생성하지 마세요**
(출력 JSON 의 `senior_agent` 값을 `null` 로 두거나 키 자체를 생략).

평가 초점: **워크플로우의 구조적 복잡성**

### Q1. 여러 이질적인 작업자 참여
"서로 다른 역량·도구·권한을 가진 2개 이상의 작업자(AI Agent 또는 인간)가 참여하며,
이들 간 **작업 위임 & 결과 통합**이 필요한가?"
- Yes: 이질적 작업자 2+ 참여, 위임·통합 필요
- No: 단일 또는 동종 Agent 로 처리 가능

"이질적 작업자" 조작적 정의 (아래 중 하나 이상 충족):
  (a) 서로 다른 시스템 접근 권한 — 예: HR 담당자(인사 DB) + 현업 팀장(업무시스템)
  (b) 서로 다른 프로세스 담당 — 예: 채용 담당자 + 교육 담당자
  (c) 조직 외부 이해관계자 — 예: 헤드헌터, 외부 평가기관, 아웃소싱 업체

### Q2. 비선형 작업 의존성
"Task 간에 **분기 / 병렬 / merge 등 단순 순차(A→B→C)를 넘는 의존 구조**가 존재하는가?"
- Yes: 분기·병렬·합류 구조 존재
- No: 단순 순차 흐름 (A→B→C→D)

### Q3. Cross-Task 상태 관리
"앞선 Task의 결과가 **후속 Task 의 입력·조건·경로를 결정**하여,
전체 워크플로우의 **누적 상태(state)를 추적·전달**해야 하는가?"
- Yes: 누적 상태 추적·전달 필요
- No: Task 간 독립적이거나 단순 전달만 하면 충분

### 판단 예시
- ✅ Senior 필요: Q1=Yes (HR+현업+외부 3자), Q2=Yes (분기·병렬), Q3=Yes (상태 추적)
- ❌ Senior 불필요: Q1=No (HR 단독), Q2=No (선형), Q3=No (단순 전달) → `senior_agent: null`

### 출력 규약
- Senior 생성 시: `senior_agent` 에 name/description/orchestration_strategy 포함
- Senior 미생성 시: `senior_agent: null` 또는 키 생략
- 생성 여부와 판단 근거를 `senior_decision` 필드에 한 줄로 기록:
  예: "Q1 Yes (HR+현업 이질 협업), Q2 No, Q3 Yes → 생성"
  예: "Q1 No (단일 HR), Q2 No (선형), Q3 No (단순 전달) → 미생성"

■ Junior AI Agent = 사원·주임급 실무자
  - 같은 L4 안에서 연속된 AI L5 태스크 2개 이상을 묶어 순차 파이프라인으로 처리
  - 예: 사원이 "자료 수집 → 분석 → 보고서 초안 작성"을 연달아 하는 것과 같음
  - Human 태스크가 중간에 끼면 그룹을 끊고 새 Agent 생성
  - 각 Agent마다 구체적인 AI 기술 유형을 지정 (아래 참조)
  - L5 태스크가 1개뿐이면 단독 Agent로 생성

■ Human (HR 담당자) = 사람이 직접 해야 하는 역할
  - "Human" 태스크 수행
  - "AI + Human" 태스크의 Human 파트(검토·승인·판단) 수행

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【AI 기술 유형 분류 체계】 — 대분류 > 세부유형 형식으로 지정
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 생성형 모델 — 학습된 패턴을 바탕으로 새로운 결과물을 생성·변환하는 모델
   · 텍스트 생성 — 문장, 문서, 메시지, 코드 등을 자동 생성
     예) 이메일 초안 작성, 보고서 문안 생성, 공지문 초안 작성
   · 요약·재작성·질의응답 — 입력 내용을 축약·변형하거나 질문에 응답
     예) 회의록 요약, 문서 재작성, 규정 기반 질의응답
   · 멀티모달 생성·이해 — 텍스트+이미지+표 등 다양한 형태를 함께 해석·생성
     예) 이미지 설명 생성, 표·문서 동시 해석 답변, 첨부화면·문의 기반 대응안 작성
   · 정보 추출 — 비정형 텍스트에서 필요 항목을 구조화된 정보로 정리
     예) 계약서 핵심 조항 추출, 이력서 경력 항목 정리, VOC 원인/조치 추출

2. 판별·예측 모델 — 데이터 특성을 기반으로 구분·예측·우선순위 판단
   · 예측 — 과거 데이터 패턴으로 미래 수치/가능성 예측
     예) 수요 예측, 이탈 가능성 예측, 장애 발생 가능성 예측
   · 군집·분류 — 속성/유사성에 따라 자동 구분·그룹화
     예) 문의 유형 분류, 고객 세그먼트 군집화, 문서 카테고리 분류
   · 추천·랭킹 — 적합도·유사성·우선순위를 계산해 정렬·추천
     예) 콘텐츠 추천, 우선 검토 대상 문서 랭킹, 후보자 우선순위 추천

3. 인식 모델 — 비정형 입력을 읽고 식별하여 구조화된 데이터로 변환
   · OCR — 문서/이미지 안의 문자를 텍스트로 변환
     예) 스캔 문서 텍스트 추출, 영수증 항목 추출, 신청서 필드값 추출
   · 음성 인식 — 음성을 텍스트로 변환
     예) 회의 음성 전사, 상담 녹취 텍스트 변환, 음성 명령 텍스트화

4. 의사결정·최적화 모델 — 목표와 제약조건을 반영해 최적 결과 도출
   · 최적화 — 다양한 제약조건을 반영한 최적의 결과 도출
     예) 근무 일정 편성, 배송 경로 최적화, 예산/인력 배분 최적화

5. 자동화 — 모델 결과를 업무 흐름과 연결해 시스템 상의 작업을 자동 수행
   · RPA — 정해진 규칙에 따라 시스템 Action을 자동 수행
     예) ERP 입력 자동화, 시스템 간 데이터 이관, 승인 요청 등록·결과 발송

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【출력 형식】 JSON만 출력
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{
  "input_sources": [
    {
      "id": "input-1",
      "name": "교육 니즈 설문 데이터",
      "source_type": "시스템",
      "description": "전사 교육 니즈 서베이 결과 데이터",
      "related_agent_ids": ["junior-ai-1"]
    },
    {
      "id": "input-2",
      "name": "외부 HRD 트렌드 자료",
      "source_type": "외부데이터",
      "description": "외부 HRD 매체 및 벤치마크 자료",
      "related_agent_ids": ["junior-ai-1"]
    }
  ],
  "junior_agents": [
    {
      "agent_name": "니즈 분석",
      "l4_id": "1.6.1",
      "task_ids": ["1.6.1.1", "1.6.1.2", "1.6.1.3", "1.6.1.4"],
      "ai_tech_per_task": {
        "1.6.1.1": {"category": "생성형 모델", "type": "요약·재작성·질의응답", "technique": "LLM"},
        "1.6.1.2": {"category": "판별·예측 모델", "type": "군집·분류", "technique": "Clustering"},
        "1.6.1.3": {"category": "생성형 모델", "type": "정보 추출", "technique": "RAG"},
        "1.6.1.4": {"category": "생성형 모델", "type": "텍스트 생성", "technique": "LLM"}
      },
      "agent_technique_summary": "LLM + RAG + Clustering",
      "description": "교육 니즈를 분석하고 외부 자료를 수집하여 시사점을 도출하는 파이프라인",
      "senior_instruction": "키워드·소스·범위 설정 후 기동. 완료 시 니즈 분석 보고서 수령",
      "input_source_ids": ["input-1", "input-2"],
      "input_description": "교육 니즈 설문, 외부 HRD 매체",
      "output_description": "니즈 분석 보고서, Implication 도출"
    }
  ],
  "human_steps": [
    {
      "task_id": "1.6.3.6",
      "label": "경영진 보고",
      "reason": "최종 의사결정 및 보고는 인간 고유 영역",
      "is_hybrid_human_part": false,
      "input_source_ids": ["input-3"]
    }
  ],
  "senior_agent": {
    "name": "교육체계 수립 Senior AI Orchestrator",
    "description": "Junior Agent의 실행을 관리하고, Agent 간 산출물을 전달하며, Human 단계 핸드오프를 제어하는 오케스트레이터",
    "orchestration_strategy": "Agent 1, 2를 병렬 기동 → 산출물 수령 → Agent 3에 전달 → Human 검토·승인 → 보고"
  },
  "senior_decision": "Q1 Yes (HR+현업 이질), Q2 Yes (병렬), Q3 Yes (상태 추적) → 생성",
  "workflow_optimization": {
    "parallel_opportunities": ["Agent 1과 Agent 2는 독립적이므로 병렬 수행 가능"],
    "sequential_dependencies": ["Agent 3은 Agent 1·2의 산출물이 필요하므로 순차"],
    "improvement_notes": "병렬 수행으로 기존 대비 처리 시간 약 30% 단축 가능"
  }
}

■ 유의사항:
  - input_sources: 전체 워크플로우에서 사용되는 입력 데이터 목록. related_agent_ids로 어떤 Agent가 사용하는지 연결
  - ai_tech_per_task: 각 태스크별로 category(대분류), type(세부유형), technique(구현 기법)를 지정
  - task_ids에는 AI 태스크와 AI+Human의 AI 파트만 포함
  - Human 태스크와 AI+Human의 Human 파트는 human_steps에 포함
  - 같은 L4 안에서만 묶을 것 (L4 경계를 넘지 않음)
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

    # ── Input Sources ──
    input_sources: list[InputSource] = []
    for inp_data in llm_result.get("input_sources", []):
        input_sources.append(InputSource(
            id=inp_data.get("id", f"input-{len(input_sources)+1}"),
            name=inp_data.get("name", ""),
            source_type=inp_data.get("source_type", ""),
            description=inp_data.get("description", ""),
            related_task_ids=inp_data.get("related_agent_ids", []),
        ))

    # ── Junior Agents ──
    junior_agents: list[JuniorAgent] = []
    for idx, ja_data in enumerate(llm_result.get("junior_agents", []), 1):
        task_ids = ja_data.get("task_ids", [])
        ai_tech_map = ja_data.get("ai_tech_per_task", {})
        # 하위호환: 이전 형식 techniques_per_task도 지원
        techniques_map = ja_data.get("techniques_per_task", {})

        agent_tasks = []
        for tid in task_ids:
            node = node_by_tid.get(tid, {})
            if not node:
                continue
            tech_info = ai_tech_map.get(tid, {})
            if isinstance(tech_info, dict):
                category = tech_info.get("category", "")
                ai_type = tech_info.get("type", "")
                technique = tech_info.get("technique", "LLM")
            else:
                category = ""
                ai_type = ""
                tech_list = techniques_map.get(tid, ["LLM"])
                technique = " + ".join(tech_list) if isinstance(tech_list, list) else str(tech_list)

            agent_tasks.append(AgentTask(
                task_id=tid,
                label=node.get("label", tid),
                classification=node.get("classification", "AI"),
                reason=node.get("reason", ""),
                ai_part=node.get("hybrid_note", ""),
                technique=technique,
                ai_tech_category=category,
                ai_tech_type=ai_type,
                node_id=node.get("node_id", ""),
            ))

        if not agent_tasks:
            continue

        # Agent 레벨의 대표 AI 기술 유형 결정
        agent_categories = [t.ai_tech_category for t in agent_tasks if t.ai_tech_category]
        agent_types = [t.ai_tech_type for t in agent_tasks if t.ai_tech_type]

        # Agent에 연결된 Input Sources
        agent_id = f"junior-ai-{idx}"
        agent_input_source_ids = ja_data.get("input_source_ids", [])
        agent_inputs = [s for s in input_sources if agent_id in s.related_task_ids
                        or s.id in agent_input_source_ids]

        junior_agents.append(JuniorAgent(
            id=agent_id,
            name=ja_data.get("agent_name", f"Agent {idx}"),
            tasks=agent_tasks,
            technique=ja_data.get("agent_technique_summary", "LLM"),
            ai_tech_category=agent_categories[0] if agent_categories else "",
            ai_tech_type=" + ".join(dict.fromkeys(agent_types)) if agent_types else "",
            input_types=ja_data.get("input_description", ""),
            output_types=ja_data.get("output_description", ""),
            input_sources=agent_inputs,
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
        if node["classification"] == "Human":
            human_steps.append(HumanStep(
                id=f"human-{len(human_steps)+1}",
                task_id=tid,
                label=node["label"],
                reason=node.get("reason", ""),
                is_hybrid_human_part=False,
                node_id=node.get("node_id", ""),
            ))

    # ── 오케스트레이션 흐름 ── (Senior 유무와 무관하게 먼저 계산)
    orchestration_flow = _build_orchestration_flow(
        as_is_sheet, junior_agents, human_steps
    )
    if not orchestration_flow:
        orchestration_flow = _build_sequential_flow(junior_agents, human_steps)

    # ── Senior Agent ── Q1/Q2/Q3 판정 결과를 LLM 이 `senior_agent` 로 전달
    # null / 누락 / 빈 dict 이면 Senior 미생성
    opt_data = llm_result.get("workflow_optimization", {})
    sa_data = llm_result.get("senior_agent")
    decision_note = llm_result.get("senior_decision", "")

    senior: SeniorAgent | None = None
    if isinstance(sa_data, dict) and sa_data:
        senior_desc = sa_data.get("description", "")
        improvement = opt_data.get("improvement_notes", "")
        if improvement:
            senior_desc += f"\n개선 효과: {improvement}"
        senior = SeniorAgent(
            id="senior-ai-1",
            name=sa_data.get("name", f"{process_name} Senior AI Orchestrator"),
            description=senior_desc,
            orchestration_strategy=sa_data.get("orchestration_strategy", ""),
        )

    workflow = ToBeWorkflow(
        process_name=process_name or as_is_sheet.name,
        junior_agents=junior_agents,
        human_steps=human_steps,
        input_sources=input_sources,
        orchestration_flow=orchestration_flow,
        senior_agent=senior,
    )

    # ── 실행 스텝 / React Flow / 요약 ──
    workflow.execution_steps = _build_execution_steps(workflow)
    workflow.react_flow = _generate_react_flow(workflow, as_is_sheet)
    workflow.summary = _build_summary(workflow, classified_nodes)

    # LLM 최적화 정보 + 판정 근거 추가
    if opt_data:
        workflow.summary["optimization"] = {
            "parallel_opportunities": opt_data.get("parallel_opportunities", []),
            "sequential_dependencies": opt_data.get("sequential_dependencies", []),
            "improvement_notes": opt_data.get("improvement_notes", ""),
        }
    if decision_note:
        workflow.summary["senior_decision"] = decision_note

    return workflow


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

    # 5. 전체 Input Sources 수집
    all_input_sources: list[InputSource] = []
    for agent in junior_agents:
        all_input_sources.extend(agent.input_sources)

    # 6. 오케스트레이션 흐름
    orchestration_flow = _build_orchestration_flow(
        as_is_sheet, junior_agents, human_steps
    )
    if not orchestration_flow:
        orchestration_flow = _build_sequential_flow(junior_agents, human_steps)

    # 7. Senior AI 필요 여부 판단 (Q1/Q2/Q3 규칙 기반 heuristic)
    senior, decision_note = _decide_senior_rule_based(
        junior_agents, human_steps, orchestration_flow,
        process_name or as_is_sheet.name,
    )

    workflow = ToBeWorkflow(
        process_name=process_name or as_is_sheet.name,
        junior_agents=junior_agents,
        human_steps=human_steps,
        input_sources=all_input_sources,
        orchestration_flow=orchestration_flow,
        senior_agent=senior,
    )

    # 8. 실행 스텝 / React Flow / 요약
    workflow.execution_steps = _build_execution_steps(workflow)
    workflow.react_flow = _generate_react_flow(workflow, as_is_sheet)
    workflow.summary = _build_summary(workflow, classified_nodes)
    workflow.summary["senior_decision"] = decision_note

    return workflow


def _decide_senior_rule_based(
    junior_agents: list[JuniorAgent],
    human_steps: list[HumanStep],
    orchestration_flow: list[dict],
    process_name: str,
) -> tuple[SeniorAgent | None, str]:
    """규칙 기반 fallback: Q1/Q2/Q3 heuristic 로 Senior AI 필요 여부 판단.

    - Q1 (이질 작업자): Junior + Human 혼재 → Yes
    - Q2 (비선형 의존): orchestration_flow 에 병렬 스텝 존재 → Yes
    - Q3 (cross-task 상태): Junior 3개 이상 → 약한 Yes 시그널
    셋 다 No 이면 Senior 미생성.
    """
    q1 = bool(junior_agents) and bool(human_steps)
    q2 = any(step.get("is_parallel") for step in orchestration_flow)
    q3 = len(junior_agents) >= 3

    if not (q1 or q2 or q3):
        note = (
            f"Q1 No (Junior {len(junior_agents)}/Human {len(human_steps)} 단독), "
            f"Q2 No (선형), Q3 No → 미생성"
        )
        return None, note

    reasons = []
    if q1:
        reasons.append(f"Q1 Yes (Junior+Human 혼재: {len(junior_agents)}/{len(human_steps)})")
    if q2:
        reasons.append("Q2 Yes (병렬 스텝)")
    if q3:
        reasons.append(f"Q3 Yes (Junior {len(junior_agents)}개)")
    note = ", ".join(reasons) + " → 생성"

    senior = SeniorAgent(
        id="senior-ai-1",
        name=f"{process_name} Senior AI Orchestrator",
        description=(
            f"{len(junior_agents)}개 Junior AI Agent의 실행 순서를 관리하고, "
            f"각 Agent 간 산출물 정합성을 검증하며, "
            f"Human 수행 단계({len(human_steps)}건)로의 핸드오프를 제어합니다."
        ),
    )
    return senior, note


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
        return cls == "AI" or (cls == "AI + Human" and split_type == "ai_part")

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
        agent_tasks = []
        for t in group_tasks:
            cat, atype, tech = _infer_ai_tech(t)
            agent_tasks.append(AgentTask(
                task_id=t["task_id"],
                label=t.get("split_label", t["label"]),
                classification=t["classification"],
                reason=t.get("reason", ""),
                ai_part=t.get("split_description", ""),
                technique=tech,
                ai_tech_category=cat,
                ai_tech_type=atype,
                node_id=t["node_id"],
            ))

        technique = _infer_technique(group_tasks, classification_results)
        first_label = group_tasks[0]["label"].split("(")[0].strip()
        name = (f"Agent {agent_idx}: {first_label} 외 {len(group_tasks)-1}건"
                if len(group_tasks) > 1
                else f"Agent {agent_idx}: {first_label}")

        agent_categories = [t.ai_tech_category for t in agent_tasks if t.ai_tech_category]
        agent_types = [t.ai_tech_type for t in agent_tasks if t.ai_tech_type]

        # 규칙 기반 Input Sources 추론
        input_sources = _infer_input_sources(group_tasks, f"junior-ai-{agent_idx}")

        agents.append(JuniorAgent(
            id=f"junior-ai-{agent_idx}",
            name=name,
            tasks=agent_tasks,
            technique=technique,
            ai_tech_category=agent_categories[0] if agent_categories else "",
            ai_tech_type=" + ".join(dict.fromkeys(agent_types)) if agent_types else "",
            input_types=group_tasks[0].get("input_types", ""),
            output_types=group_tasks[-1].get("output_types", ""),
            input_sources=input_sources,
            description=f"{len(agent_tasks)}개 L5 태스크의 순차 처리 파이프라인",
        ))
        agent_idx += 1

    for task in standalone:
        cat, atype, tech = _infer_ai_tech(task)
        input_sources = _infer_input_sources([task], f"junior-ai-{agent_idx}")
        agents.append(JuniorAgent(
            id=f"junior-ai-{agent_idx}",
            name=f"Agent {agent_idx}: {task['label'].split('(')[0].strip()}",
            tasks=[AgentTask(
                task_id=task["task_id"],
                label=task.get("split_label", task["label"]),
                classification=task["classification"],
                reason=task.get("reason", ""),
                ai_part=task.get("split_description", ""),
                technique=tech,
                ai_tech_category=cat,
                ai_tech_type=atype,
                node_id=task["node_id"],
            )],
            technique=_infer_technique([task], classification_results),
            ai_tech_category=cat,
            ai_tech_type=atype,
            input_types=task.get("input_types", ""),
            output_types=task.get("output_types", ""),
            input_sources=input_sources,
            description="단독 L4 태스크 처리",
        ))
        agent_idx += 1

    return agents


def _infer_ai_tech(task: dict) -> tuple[str, str, str]:
    """개별 태스크의 AI 기술 대분류, 세부유형, 기법을 추론합니다.
    Returns: (category, type, technique)
    """
    text = (task.get("label", "") + " " + task.get("reason", "")).lower()

    # 자동화/RPA 패턴
    if any(kw in text for kw in ["입력", "등록", "이관", "발송", "자동화", "rpa"]):
        return "자동화", "RPA", "RPA"
    # 인식 모델
    if any(kw in text for kw in ["ocr", "스캔", "영수증", "인식"]):
        return "인식 모델", "OCR", "OCR"
    if any(kw in text for kw in ["음성", "녹취", "전사", "stt"]):
        return "인식 모델", "음성 인식", "음성 인식"
    # 의사결정·최적화
    if any(kw in text for kw in ["최적화", "편성", "배분", "스케줄"]):
        return "의사결정·최적화 모델", "최적화", "최적화"
    # 판별·예측 모델
    if any(kw in text for kw in ["예측", "이탈", "전망"]):
        return "판별·예측 모델", "예측", "예측 모델"
    if any(kw in text for kw in ["군집", "그룹", "클러스터", "세그먼트"]):
        return "판별·예측 모델", "군집·분류", "Clustering"
    if any(kw in text for kw in ["분류", "매핑", "카테고리"]):
        return "판별·예측 모델", "군집·분류", "규칙 기반"
    if any(kw in text for kw in ["추천", "랭킹", "우선순위"]):
        return "판별·예측 모델", "추천·랭킹", "추천 모델"
    # 생성형 모델
    if any(kw in text for kw in ["추출", "항목", "조항", "정리"]):
        return "생성형 모델", "정보 추출", "LLM"
    if any(kw in text for kw in ["요약", "재작성", "질의", "답변", "qa"]):
        return "생성형 모델", "요약·재작성·질의응답", "RAG"
    if any(kw in text for kw in ["이미지", "멀티모달", "표", "화면"]):
        return "생성형 모델", "멀티모달 생성·이해", "멀티모달 LLM"
    if any(kw in text for kw in ["작성", "생성", "초안", "보고서", "문서", "기안"]):
        return "생성형 모델", "텍스트 생성", "LLM"
    if any(kw in text for kw in ["수집", "조사", "검색", "외부", "크롤링"]):
        return "생성형 모델", "요약·재작성·질의응답", "RAG"
    if any(kw in text for kw in ["분석", "통계", "수치", "집계"]):
        return "생성형 모델", "정보 추출", "LLM"

    # 기본값
    return "생성형 모델", "텍스트 생성", "LLM"


def _infer_input_sources(tasks: list[dict], agent_id: str) -> list[InputSource]:
    """태스크 그룹의 입력 데이터를 추론합니다 (규칙 기반 fallback용)."""
    sources: list[InputSource] = []
    seen: set[str] = set()
    idx = 1

    for task in tasks:
        input_types = task.get("input_types", "")
        if not input_types:
            continue
        for inp in input_types.split(","):
            inp = inp.strip()
            if not inp or inp in seen:
                continue
            seen.add(inp)

            # 입력 유형 추론
            if any(kw in inp for kw in ["시스템", "ERP", "SAP", "DB"]):
                source_type = "시스템"
            elif any(kw in inp for kw in ["문서", "서류", "규정", "매뉴얼"]):
                source_type = "문서"
            elif any(kw in inp for kw in ["외부", "벤치마크", "법령"]):
                source_type = "외부데이터"
            else:
                source_type = "기타"

            sources.append(InputSource(
                id=f"{agent_id}-input-{idx}",
                name=inp,
                source_type=source_type,
                description="",
                related_task_ids=[agent_id],
            ))
            idx += 1

    return sources


def _infer_single_technique(task: dict) -> str:
    """개별 태스크의 AI 기법을 추론합니다 (하위호환)."""
    _, _, technique = _infer_ai_tech(task)
    return technique


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
    """Human 태스크 + AI+Human의 Human 파트를 추출합니다."""
    steps = []
    step_idx = 1
    for task in split_tasks:
        if task["classification"] == "Human":
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


def _build_execution_steps(workflow: ToBeWorkflow) -> list[dict]:
    """To-Be 실행 스텝을 생성합니다."""
    steps = []
    step_num = 1
    for flow_step in workflow.orchestration_flow:
        agents_in_step = []
        for agent_id in flow_step["agents"]:
            junior = next((j for j in workflow.junior_agents if j.id == agent_id), None)
            if junior:
                agents_in_step.append({
                    "type": "junior_ai",
                    "agent_id": junior.id,
                    "agent_name": junior.name,
                    "technique": junior.technique,
                    "ai_tech_category": junior.ai_tech_category,
                    "ai_tech_type": junior.ai_tech_type,
                    "description": junior.description,
                    "senior_instruction": junior.senior_instruction,
                    "input_sources": [
                        {"id": s.id, "name": s.name, "source_type": s.source_type}
                        for s in junior.input_sources
                    ],
                    "tasks": [
                        {
                            "task_id": t.task_id,
                            "label": t.label,
                            "technique": t.technique,
                            "ai_tech_category": t.ai_tech_category,
                            "ai_tech_type": t.ai_tech_type,
                        }
                        for t in junior.tasks
                    ],
                })
                continue
            human = next((h for h in workflow.human_steps if h.id == agent_id), None)
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


# ── Agent 색상 팔레트 (PPT와 동일 10색) ───────────────────────────────────────
_AGENT_BLUE_PALETTE = [
    "#2E75B6",   # 1  파란
    "#00A6A0",   # 2  청록
    "#7B68C4",   # 3  보라
    "#5B9BD5",   # 4  하늘
    "#00827F",   # 5  틸
    "#4172C4",   # 6  남색
    "#2D8BBA",   # 7  바다
    "#8B5CF6",   # 8  연보라
    "#0E6E5C",   # 9  짙은 초록
    "#3A86FF",   # 10 밝은 파란
]


def _agent_color(idx: int) -> str:
    """Agent 인덱스에 대응하는 파란 계열 색상 hex를 반환."""
    return _AGENT_BLUE_PALETTE[idx % len(_AGENT_BLUE_PALETTE)]


# ── React Flow 생성 ───────────────────────────────────────────────────────────

def _generate_react_flow(
    workflow: ToBeWorkflow,
    as_is_sheet: WorkflowSheet,
) -> dict:
    """To-Be 워크플로우를 React Flow 호환 JSON으로 생성합니다."""
    nodes = []
    edges = []

    senior = workflow.senior_agent
    has_senior = senior is not None

    # Senior AI 없으면 lane 에서도 제외
    lanes = ["Input", "Senior AI", "Junior AI", "Human"] if has_senior \
        else ["Input", "Junior AI", "Human"]

    LANE_HEIGHT = 300
    NODE_GAP_X = 280
    START_X = 200
    START_Y = 50

    if has_senior:
        y_offsets = {
            "input": START_Y,
            "senior": START_Y + LANE_HEIGHT,
            "junior": START_Y + LANE_HEIGHT * 2,
            "human": START_Y + LANE_HEIGHT * 3,
        }
    else:
        y_offsets = {
            "input": START_Y,
            "junior": START_Y + LANE_HEIGHT,
            "human": START_Y + LANE_HEIGHT * 2,
        }

    current_x = START_X

    # Senior AI 노드 — 있을 때만 생성
    senior_node_id = "tobe-senior" if has_senior else ""
    if has_senior:
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

    # Junior Agent 인덱스 매핑 (색상용)
    junior_idx_map: dict[str, int] = {
        j.id: i for i, j in enumerate(workflow.junior_agents)
    }

    # 시작점: Senior 있으면 Senior 에서, 없으면 없음 (Input → Junior 직결)
    prev_step_node_ids: list[str] = [senior_node_id] if has_senior else []

    for step_idx, flow_step in enumerate(workflow.orchestration_flow):
        step_node_ids: list[str] = []
        branch_x = current_x

        for agent_id in flow_step["agents"]:
            # Junior Agent
            junior = next((j for j in workflow.junior_agents if j.id == agent_id), None)
            if junior:
                jnode_id = f"tobe-{junior.id}"
                j_color = _agent_color(junior_idx_map.get(junior.id, 0))

                # Input Source 노드 (Junior Agent 위에 배치)
                for si, src in enumerate(junior.input_sources):
                    inp_node_id = f"tobe-input-{src.id}"
                    nodes.append({
                        "id": inp_node_id,
                        "type": "l5",
                        "position": {
                            "x": branch_x + si * 140,
                            "y": y_offsets["input"] + 20,
                        },
                        "data": {
                            "label": src.name,
                            "level": "Input",
                            "id": src.id,
                            "description": src.description,
                            "agentType": "input",
                            "sourceType": src.source_type,
                        },
                    })
                    # Input → Junior Agent 엣지 (Agent별 고유 색상)
                    edges.append({
                        "id": f"e-{inp_node_id}-{jnode_id}",
                        "source": inp_node_id,
                        "target": jnode_id,
                        "type": "smoothstep",
                        "animated": False,
                        "style": {"stroke": j_color, "strokeWidth": 1.5},
                        "markerEnd": {"type": "arrowclosed", "color": j_color},
                        "label": src.source_type,
                    })

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
                        "ai_tech_category": junior.ai_tech_category,
                        "ai_tech_type": junior.ai_tech_type,
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
                            "ai_tech_category": task.ai_tech_category,
                            "ai_tech_type": task.ai_tech_type,
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
            human = next((h for h in workflow.human_steps if h.id == agent_id), None)
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
                if has_senior and prev_id == senior_node_id:
                    # Senior → Junior: 기동 지시 라벨
                    junior = next((j for j in workflow.junior_agents if f"tobe-{j.id}" == snid), None)
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

    # ── Junior → Senior 피드백 엣지 (GRAY #999999) — Senior 있을 때만 ──
    if has_senior:
        for junior in workflow.junior_agents:
            jnode_id = f"tobe-{junior.id}"
            edges.append({
                "id": f"e-feedback-{jnode_id}-{senior_node_id}",
                "source": jnode_id,
                "target": senior_node_id,
                "type": "smoothstep",
                "animated": False,
                "style": {"stroke": "#999999", "strokeWidth": 1.5, "strokeDasharray": "4 2"},
                "markerEnd": {"type": "arrowclosed", "color": "#999999"},
                "label": "결과 반환",
            })

    # ── Junior → HR 엣지 (GOLD #B48E04) — human_role이 있는 태스크의 Agent만 ──
    for junior in workflow.junior_agents:
        has_human = any(
            t.classification == "AI + Human" for t in junior.tasks
        )
        if has_human:
            jnode_id = f"tobe-{junior.id}"
            for hs in workflow.human_steps:
                hnode_id = f"tobe-{hs.id}"
                if any(t.task_id == hs.task_id for t in junior.tasks):
                    edges.append({
                        "id": f"e-jr-hr-{jnode_id}-{hnode_id}",
                        "source": jnode_id,
                        "target": hnode_id,
                        "type": "smoothstep",
                        "animated": False,
                        "style": {"stroke": "#B48E04", "strokeWidth": 2},
                        "markerEnd": {"type": "arrowclosed", "color": "#B48E04"},
                        "label": "검토 요청",
                    })

    # ── Senior → HR 감독 엣지 (RED #8B1A1A) — Senior 있을 때만 ──
    if has_senior and workflow.human_steps:
        for hs in workflow.human_steps:
            hnode_id = f"tobe-{hs.id}"
            edges.append({
                "id": f"e-supervision-{senior_node_id}-{hnode_id}",
                "source": senior_node_id,
                "target": hnode_id,
                "type": "smoothstep",
                "animated": False,
                "style": {"stroke": "#8B1A1A", "strokeWidth": 1.5, "strokeDasharray": "6 3"},
                "markerEnd": {"type": "arrowclosed", "color": "#8B1A1A"},
                "label": "감독",
            })

    return {
        "version": "1.0",
        "type": "tobe",
        "nodes": nodes,
        "edges": edges,
        "lanes": lanes,
    }


# ── 요약 ──────────────────────────────────────────────────────────────────────

def _build_summary(
    workflow: ToBeWorkflow,
    classified_nodes: list[dict],
) -> dict:
    """To-Be 워크플로우 요약 정보."""
    total = len(classified_nodes)
    ai_count = sum(1 for n in classified_nodes if n["classification"] == "AI")
    hybrid_count = sum(1 for n in classified_nodes if n["classification"] == "AI + Human")
    human_count = sum(1 for n in classified_nodes if n["classification"] == "Human")

    senior = workflow.senior_agent
    senior_payload = {
        "id": senior.id,
        "name": senior.name,
        "description": senior.description,
        "orchestration_strategy": senior.orchestration_strategy,
    } if senior else None

    return {
        "process_name": workflow.process_name,
        "total_tasks": total,
        "ai_tasks": ai_count,
        "hybrid_tasks": hybrid_count,
        "human_tasks": human_count,
        "automation_rate": round((ai_count + hybrid_count * 0.5) / max(total, 1) * 100, 1),
        "input_source_count": len(workflow.input_sources),
        "input_sources": [
            {
                "id": s.id,
                "name": s.name,
                "source_type": s.source_type,
                "description": s.description,
                "related_task_ids": s.related_task_ids,
            }
            for s in workflow.input_sources
        ],
        "junior_agent_count": len(workflow.junior_agents),
        "junior_agents": [
            {
                "id": j.id,
                "name": j.name,
                "technique": j.technique,
                "ai_tech_category": j.ai_tech_category,
                "ai_tech_type": j.ai_tech_type,
                "task_count": j.task_count,
                "description": j.description,
                "senior_instruction": j.senior_instruction,
                "input_sources": [
                    {"id": s.id, "name": s.name, "source_type": s.source_type}
                    for s in j.input_sources
                ],
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "label": t.label,
                        "technique": t.technique,
                        "ai_tech_category": t.ai_tech_category,
                        "ai_tech_type": t.ai_tech_type,
                    }
                    for t in j.tasks
                ],
            }
            for j in workflow.junior_agents
        ],
        "human_step_count": len(workflow.human_steps),
        "human_steps": [
            {
                "id": h.id,
                "label": h.label,
                "is_hybrid_part": h.is_hybrid_human_part,
                "reason": h.reason,
            }
            for h in workflow.human_steps
        ],
        "senior_agent": senior_payload,
    }
