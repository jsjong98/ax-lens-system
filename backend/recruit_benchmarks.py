"""
채용 (Recruitment) 선도사 AI 적용 사례 — 레퍼런스 벤치마킹 (curated).

Doosan HR L2 '채용 기획' · '채용 운영' 프로세스에 매칭되는 사전 정의 사례.
main.py 에 포함시키기엔 컨텐츠가 커서 별도 파일로 분리.

- 프론트엔드: 일반 Perplexity/캡쳐 벤치마킹과 구분하여 파란색으로 강조 표시
- Step 1 프롬프트: 벤치마킹 컨텍스트에 동등하게 주입되어 기본 설계 생성 시 활용

Player 명칭은 원본 그대로 유지 (IBM / GM / Siemens).
"""
from __future__ import annotations

from typing import TypedDict


class RecruitReferenceBenchmark(TypedDict):
    case_no: int
    title: str                     # 사례 제목
    companies: list[str]           # 적용 Player (정확한 명칭)
    stage: str                     # 적용 구간
    description: str               # 상세 설명 원문
    applicable_l2: list[str]       # 두산 L2 매칭 (예: '채용 기획', '채용 운영')


# ─────────────────────────────────────────────────────────────────────
# [채용] 선도사 AI 적용 기능별 상세 설명 (7건)
# ─────────────────────────────────────────────────────────────────────

RECRUIT_REFERENCE_BENCHMARKS: list[RecruitReferenceBenchmark] = [
    {
        "case_no": 1,
        "title": "'스킬 추론' 기반 채용 전략 수립 지원",
        "companies": ["IBM"],
        "stage": "채용 전략·기획",
        "description": (
            "인력 충원 요청이 발생한 포지션의 스킬 요구사항을 파악하고, 내부 스킬 Data를 "
            "기반으로 보유 스킬과 수요 스킬 간의 Gap을 분석한다. 이를 통해 내부 인재 육성(내부 "
            "채용)으로 충당 가능한지, 혹은 외부 채용이 필요한지를 AI가 의사결정 지원한다. "
            "단순한 헤드카운트 계획이 아닌, 스킬 데이터 기반의 전략적 채용 계획 수립이 핵심이다."
        ),
        "applicable_l2": ["채용 기획"],
    },
    {
        "case_no": 2,
        "title": "AI 챗봇을 활용한 지원자 문의 상시 응대",
        "companies": ["GM", "IBM"],
        "stage": "모집·유입 → 소싱 → 지원자 평가·운영",
        "description": (
            "24/7 상시 운영되는 AI 챗봇을 통해 지원자의 지원 방법, 자격 요건, 필수 역량, "
            "전형 일정, 직무 정보, 우대 조건 등 반복적인 문의를 자동 응대한다. GM의 경우 "
            "'Ev-E'라는 대화형 AI 챗봇을 구축하여 대규모 지원자 응대를 처리하며, IBM은 "
            "'AskHR' 플랫폼을 통해 동일한 기능을 구현한다. 채용 담당자의 반복 업무 부담을 "
            "줄이고, 지원자 경험(Candidate Experience)을 개선하는 데 핵심 역할을 한다."
        ),
        "applicable_l2": ["채용 운영"],
    },
    {
        "case_no": 3,
        "title": "지원자 맞춤형 공고 추천",
        "companies": ["Siemens"],
        "stage": "모집·유입 → 소싱",
        "description": (
            "지원자의 CV 및 보유 스킬 데이터를 분석하여, 스킬 기반으로 직무-지원자 간 매칭을 "
            "고도화하고 지원자에게 최적의 채용 공고를 추천한다. RPA 및 Data Parsing 기술로 "
            "원본 파일에서 텍스트를 검출하고, NLP 기반으로 보유/요구 스킬을 추출하여 스킬 DB와 "
            "정규화·매핑한다. 지원자 입장에서는 탐색 비용 감소, 기업 입장에서는 적합도 높은 "
            "지원자 유입률 향상 효과를 동시에 달성한다."
        ),
        "applicable_l2": ["채용 운영"],
    },
    {
        "case_no": 4,
        "title": "지원자별 적합도 계산 및 후보자 Shortlist 자동 생성",
        "companies": ["Siemens", "IBM"],
        "stage": "소싱 → 지원자 평가·운영",
        "description": (
            "내부 인재 Pool 및 외부 지원자를 대상으로 채용 공고별 스킬/지식/경험 기반의 "
            "적합도를 계산하고, Pool 내 우선 검토 후보자 리스트를 자동으로 생성한다. Siemens는 "
            "스킬 매칭 기반 직무 적합도 정량 평가 및 Scoring을 통해 지원자 선별의 정밀도를 "
            "높이며, IBM은 인재 Pool 기반 적합 후보 매칭 및 우선순위화를 수행한다. 채용 "
            "담당자의 수작업 스크리닝을 대체하여 소싱 속도와 선발 품질을 동시에 향상시킨다."
        ),
        "applicable_l2": ["채용 운영"],
    },
    {
        "case_no": 5,
        "title": "입사지원서 Pre-screen",
        "companies": ["GM", "IBM"],
        "stage": "소싱 → 지원자 평가·운영",
        "description": (
            "지원자의 CV 및 입사지원서에서 텍스트를 추출하고, 자격 요건 충족 여부를 자동으로 "
            "분류(충족/미충족/검토 필요)한다. GM은 AI 챗봇 'Ev-E'를 통해 지원자와의 대화를 통해 "
            "자격요건 충족 여부를 1차 검증하고 규칙 기반 필터링 알고리즘을 적용한다. IBM은 "
            "지원서 텍스트 추출 후 자격 충족 여부 자동 필터링을 수행한다. 대규모 지원자가 "
            "발생하는 환경에서 채용 담당자가 실질적인 평가에만 집중할 수 있도록 선행 업무를 "
            "자동화하는 것이 핵심 목적이다."
        ),
        "applicable_l2": ["채용 운영"],
    },
    {
        "case_no": 6,
        "title": "전형 일정 자동 조율",
        "companies": ["GM"],
        "stage": "지원자 평가·운영",
        "description": (
            "면접 일정 제안, 선택, 확정, 변경 등의 일정 관련 업무를 AI가 자동으로 처리한다. "
            "캘린더 API 연동을 통해 면접관과 지원자의 가용 일정을 실시간으로 반영하며 면접 "
            "일정을 자동 조율한다. GM의 경우 대규모 제조기업 특성상 포지션 오픈 및 지원자 "
            "유입이 상시 대량 발생하는 구조이기 때문에, 수작업 일정 조율에 소요되는 리소스를 "
            "최소화하고 채용 사이클 타임을 단축하는 효과를 실현한다."
        ),
        "applicable_l2": ["채용 운영"],
    },
    {
        "case_no": 7,
        "title": "신규입사자 온보딩 자동화",
        "companies": ["IBM"],
        "stage": "채용 후속관리",
        "description": (
            "합격자 확정 이후 입사 Workflow를 자동으로 실행하여 데이터 이관, 계정 생성, 입사 "
            "안내, 입사서류 징구 등 온보딩 전 과정을 자동화한다. IBM의 'AskHR' 플랫폼을 "
            "활용하여 신규입사자에게 온보딩 진행 방향을 안내하고, 채용 담당자의 개입 없이도 "
            "입사 준비가 완결되는 구조를 구현한다. 채용과 온보딩 간의 단절 없이 데이터가 "
            "연속적으로 흐르는 End-to-End 자동화가 핵심 설계 원칙이다."
        ),
        "applicable_l2": ["채용 운영"],
    },
]


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def get_reference_benchmarks_by_l2(l2_names: list[str]) -> list[RecruitReferenceBenchmark]:
    """주어진 L2 이름 목록과 매칭되는 레퍼런스 벤치마킹 사례 반환.

    매칭 로직: 각 사례의 applicable_l2 중 하나라도 l2_names 에 있으면 포함.
    (부분 문자열 매칭 아님 — 정확한 L2 이름 일치)
    """
    if not l2_names:
        return []
    l2_set = {str(name).strip() for name in l2_names if name}
    return [
        bm for bm in RECRUIT_REFERENCE_BENCHMARKS
        if any(l2 in l2_set for l2 in bm["applicable_l2"])
    ]


def get_reference_benchmarks_for_tasks(tasks) -> list[RecruitReferenceBenchmark]:
    """엑셀 task 리스트에서 L2 추출 후 매칭되는 레퍼런스 반환."""
    if not tasks:
        return []
    l2_names = list({getattr(t, "l2", "") or "" for t in tasks})
    l2_names = [n for n in l2_names if n]
    return get_reference_benchmarks_by_l2(l2_names)


def format_references_for_prompt(references: list[RecruitReferenceBenchmark]) -> str:
    """Step 1 프롬프트 주입용 텍스트 포맷."""
    if not references:
        return ""
    lines = ["## 📚 레퍼런스 벤치마킹 (Doosan HR 큐레이션 - 채용 도메인)"]
    for bm in references:
        players = " · ".join(bm["companies"])
        lines.append("")
        lines.append(f"[{bm['case_no']}] **{bm['title']}**")
        lines.append(f"   · 적용 Player: {players}")
        lines.append(f"   · 적용 구간: {bm['stage']}")
        lines.append(f"   · 설명: {bm['description']}")
    return "\n".join(lines) + "\n"
