"""
채용 (Recruitment) 선도사 AI 적용 사례 — 레퍼런스 벤치마킹 (curated).

Doosan HR L2 '채용 기획' · '채용 운영' 프로세스에 매칭되는 사전 정의 사례.
main.py 에 포함시키기엔 컨텐츠가 커서 별도 파일로 분리.

**용도**: Task 이름 attribution
- AI task 이름이 이 사례의 매칭 키워드를 포함하면, Task 이름 앞에 벤치마킹 title 을
  prefix 로 붙여 "이 AI 기능이 어떤 벤치마킹에서 왔는지" 명시.
  예: '대화형 AI 사전 스크리닝 (Knock-out 질문)'
      → '입사지원서 Pre-screen - 대화형 AI 사전 스크리닝 (Knock-out 질문)'
- 프론트엔드는 prefix 부분을 파란색으로 강조 (벤치마킹 출처임을 시각화)

Title 은 반드시 원본 그대로 유지 (어디서 왔는지 정확히 표시하기 위함).
Player 명칭 / 상세 설명 / 적용 구간 은 여기 저장 안 함 (Task 이름 attribution 에 불필요).
"""
from __future__ import annotations

from typing import TypedDict


class RecruitReferenceBenchmark(TypedDict):
    case_no: int
    title: str                     # 벤치마킹 사례 제목 (attribution prefix 원본)
    match_keywords: list[str]      # Task 이름 매칭 키워드 (부분 문자열, 대소문자 무시)
    applicable_l2: list[str]       # 두산 L2 매칭 (UI 레퍼런스 블록 표시 조건)


# ─────────────────────────────────────────────────────────────────────
# [채용] 선도사 AI 적용 사례 제목 목록 (7건)
# ─────────────────────────────────────────────────────────────────────
# match_keywords 는 Step 2 LLM 이 생성할 만한 Junior AI task 명을 고려해 선정.
# 하나의 키워드만 맞아도 매칭 (여러 사례가 겹치면 먼저 정의된 사례 우선).

RECRUIT_REFERENCE_BENCHMARKS: list[RecruitReferenceBenchmark] = [
    {
        "case_no": 1,
        "title": "'스킬 추론' 기반 채용 전략 수립 지원",
        "match_keywords": [
            "스킬 추론", "스킬 갭", "스킬 gap", "스킬 분석",
            "인력 계획", "충원 계획", "헤드카운트", "채용 전략",
            "내부 인재 육성", "내부 채용",
        ],
        "applicable_l2": ["채용 기획"],
    },
    {
        "case_no": 2,
        "title": "AI 챗봇을 활용한 지원자 문의 상시 응대",
        "match_keywords": [
            "챗봇", "Chatbot", "chatbot",
            "문의 응대", "지원자 응대", "FAQ", "Q&A",
            "실시간 응대", "24/7",
        ],
        "applicable_l2": ["채용 운영"],
    },
    {
        "case_no": 3,
        "title": "지원자 맞춤형 공고 추천",
        "match_keywords": [
            "공고 추천", "맞춤 공고", "맞춤형 공고",
            "직무 추천", "공고 매칭", "CV 분석",
        ],
        "applicable_l2": ["채용 운영"],
    },
    {
        "case_no": 4,
        "title": "지원자별 적합도 계산 및 후보자 Shortlist 자동 생성",
        "match_keywords": [
            "적합도", "Shortlist", "shortlist", "쇼트리스트",
            "후보자 매칭", "지원자-직무 매칭", "우선순위 라우팅", "우선순위",
            "후보자 선별", "후보 리스트",
        ],
        "applicable_l2": ["채용 운영"],
    },
    {
        "case_no": 5,
        "title": "입사지원서 Pre-screen",
        "match_keywords": [
            "Pre-screen", "pre-screen", "pre screen", "프리스크린",
            "사전 스크리닝", "사전스크리닝", "초기 스크리닝", "스크리닝",
            "Knock-out", "knock-out", "knockout", "Knock out",
            "자격 요건", "자격요건 검증", "지원자격 검토",
            "서류 자동 필터링",
        ],
        "applicable_l2": ["채용 운영"],
    },
    {
        "case_no": 6,
        "title": "전형 일정 자동 조율",
        "match_keywords": [
            "일정 조율", "일정조율", "면접 일정", "전형 일정",
            "캘린더", "스케줄링", "Scheduling", "scheduling",
            "일정 자동", "일정 제안", "일정 확정",
        ],
        "applicable_l2": ["채용 운영"],
    },
    {
        "case_no": 7,
        "title": "신규입사자 온보딩 자동화",
        "match_keywords": [
            "온보딩", "Onboarding", "onboarding",
            "입사 안내", "입사 준비", "신규입사자",
            "계정 생성", "입사서류", "입사 Workflow",
        ],
        "applicable_l2": ["채용 운영"],
    },
]


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def get_reference_benchmarks_by_l2(l2_names: list[str]) -> list[RecruitReferenceBenchmark]:
    """주어진 L2 이름 목록과 매칭되는 레퍼런스 벤치마킹 사례 반환 (UI 표시용)."""
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


def match_benchmark_for_task(task_name: str) -> RecruitReferenceBenchmark | None:
    """Task 이름 키워드 기반으로 매칭되는 레퍼런스 사례 1건 반환 (없으면 None).

    매칭 규칙:
    - Task 이름에 match_keywords 중 어느 하나라도 부분 문자열로 포함되면 매칭
    - 대소문자 무시
    - 여러 사례가 겹치면 RECRUIT_REFERENCE_BENCHMARKS 에서 먼저 정의된 사례 우선
    """
    if not task_name:
        return None
    tn = task_name.lower()
    for bm in RECRUIT_REFERENCE_BENCHMARKS:
        for kw in bm["match_keywords"]:
            if kw.lower() in tn:
                return bm
    return None


def attribute_task_name(task_name: str) -> tuple[str, str | None]:
    """Task 이름에 매칭되는 벤치마킹 title 이 있으면 prefix 된 이름 반환.

    Returns:
        (display_label, benchmark_source_title_or_None)
        - 매칭: ("입사지원서 Pre-screen - 대화형 AI 사전 스크리닝 (Knock-out 질문)",
                "입사지원서 Pre-screen")
        - 미매칭: (원본 task_name, None)
    """
    if not task_name:
        return task_name or "", None
    bm = match_benchmark_for_task(task_name)
    if not bm:
        return task_name, None
    return f"{bm['title']} - {task_name}", bm["title"]
