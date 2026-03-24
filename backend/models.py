"""
models.py — 공통 Pydantic 데이터 모델
"""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ── Task 관련 ────────────────────────────────────────────────────────────────

class Task(BaseModel):
    id: str = Field(..., description="L5 Task ID (예: 1.1.1.1)")
    l2_id: str = ""
    l2: str = Field(..., description="Major Process (L2) 명")
    l3_id: str = ""
    l3: str = Field(..., description="Unit Process (L3) 명")
    l4_id: str = ""
    l4: str = Field(..., description="Activity (L4) 명")
    l4_description: str = Field("", description="Activity (L4) 설명 (없는 경우 빈 문자열)")
    name: str = Field(..., description="L5 Task 명")
    description: str = Field("", description="L5 Task 설명")
    performer: str = Field("", description="수행주체 내용 (자유 텍스트)")

    # A-1. 수행주체 체크박스 (M~P열)
    performer_executive: str = Field("", description="A-1. 수행주체: 임원")
    performer_hr: str = Field("", description="A-1. 수행주체: HR")
    performer_manager: str = Field("", description="A-1. 수행주체: 현업 팀장")
    performer_member: str = Field("", description="A-1. 수행주체: 현업 구성원")

    # D-1. Pain Point (Q~W열)
    pain_time: str = Field("", description="D-1. Pain Point: 시간/속도")
    pain_accuracy: str = Field("", description="D-1. Pain Point: 정확성")
    pain_repetition: str = Field("", description="D-1. Pain Point: 반복/수작업")
    pain_data: str = Field("", description="D-1. Pain Point: 정보/데이터")
    pain_system: str = Field("", description="D-1. Pain Point: 시스템/도구")
    pain_communication: str = Field("", description="D-1. Pain Point: 의사소통/협업")
    pain_other: str = Field("", description="D-1. Pain Point: 기타")

    # E-2. Output 유형 (X~AB열)
    output_system: str = Field("", description="E-2. Output: 시스템 반영")
    output_document: str = Field("", description="E-2. Output: 문서/보고서")
    output_communication: str = Field("", description="E-2. Output: 커뮤니케이션")
    output_decision: str = Field("", description="E-2. Output: 의사결정")
    output_other: str = Field("", description="E-2. Output: 기타")

    # F-1. 업무 판단 로직 (AC~AE열)
    logic_rule_based: str = Field("", description="F-1. 업무 판단 로직: Rule-based (규칙 기반)")
    logic_human_judgment: str = Field("", description="F-1. 업무 판단 로직: 사람 판단")
    logic_mixed: str = Field("", description="F-1. 업무 판단 로직: 혼합")

    # F-2~F-3 (AF~AG열)
    remark: str = Field("", description="F-2. 비고")
    standard_or_specialized: str = Field("", description="F-3. 표준 vs. 특화 구분")


# ── 분류 결과 관련 ────────────────────────────────────────────────────────────

LabelType = Literal["AI", "AI + Human", "Human", "미분류"]


class StageAnalysis(BaseModel):
    """3단계 Knock-out 각 단계의 분석 결과"""
    passed: bool = True
    note: str = Field("", description="해당 단계 판단 근거 (통과 시 빈 문자열 가능)")


class ClassificationResult(BaseModel):
    task_id: str
    label: LabelType = "미분류"
    reason: str = ""
    provider: str = Field("openai", description="분류에 사용된 API 제공자 (openai | anthropic)")
    criterion: str = Field(
        "",
        description="인간 수행 필요 시 적용된 knock-out 단계 (예: '1단계: 규제 측면'). AI 수행 가능이면 빈 문자열.",
    )
    # 3단계 Knock-out 단계별 분석
    stage1: StageAnalysis = Field(default_factory=StageAnalysis, description="1단계: 규제 측면 분석")
    stage2: StageAnalysis = Field(default_factory=StageAnalysis, description="2단계: 확정/승인 업무 분석")
    stage3: StageAnalysis = Field(default_factory=StageAnalysis, description="3단계: 상호작용 업무 분석")
    hybrid_check: bool = Field(False, description="AI+Human 하이브리드 패턴 해당 여부")
    hybrid_note: str = Field("", description="AI+Human 패턴 근거 및 AI/Human 역할 설명")
    input_types: str = Field(
        "",
        description="감지된 Input 유형 쉼표 구분 (예: '시스템 데이터, 문서/서류'). AI 수행 가능 태스크의 부가 정보.",
    )
    output_types: str = Field(
        "",
        description="감지된 Output 유형 쉼표 구분 (예: '시스템 반영, 문서/보고서'). AI 수행 가능 태스크의 부가 정보.",
    )
    ai_prerequisites: str = Field(
        "",
        description="AI 수행 필요 여건 — AI가 해당 업무를 수행하기 위한 전제조건·인프라·데이터 요건 (AI 수행 가능/AI+Human인 경우만 기재)",
    )
    manually_edited: bool = False


class ClassificationResultUpdate(BaseModel):
    label: LabelType
    reason: Optional[str] = None


# ── 분류기 설정 ────────────────────────────────────────────────────────────────

class ClassifierSettings(BaseModel):
    criteria_prompt: str = Field(
        "",
        description="LLM에 전달할 추가 분류 기준 텍스트",
    )
    api_key: str = Field("", description="OpenAI API 키 (비어있으면 환경변수 사용)")
    model: str = Field("gpt-5.4", description="사용할 OpenAI 모델명")
    anthropic_api_key: str = Field("", description="Anthropic API 키 (비어있으면 환경변수 사용)")
    anthropic_model: str = Field("claude-sonnet-4-6", description="사용할 Anthropic 모델명")
    batch_size: int = Field(1, ge=1, le=50, description="배치당 Task 수")
    temperature: float = Field(0.0, ge=0.0, le=2.0)


# ── 분류 요청 ────────────────────────────────────────────────────────────────

class ClassifyRequest(BaseModel):
    task_ids: Optional[list[str]] = Field(
        None, description="분류할 Task ID 목록. None이면 전체 처리"
    )
    settings: Optional[ClassifierSettings] = None
    provider: str = Field("openai", description="분류에 사용할 API 제공자 (openai | anthropic)")


# ── API 응답 ─────────────────────────────────────────────────────────────────

class TaskListResponse(BaseModel):
    total: int
    tasks: list[Task]


class ResultsResponse(BaseModel):
    total: int
    classified: int
    unclassified: int
    results: list[ClassificationResult]


class StatsResponse(BaseModel):
    total: int
    ai_count: int
    hybrid_count: int
    human_count: int
    unclassified_count: int
    ai_ratio: float
    hybrid_ratio: float
    human_ratio: float
    by_l3: list[dict]
