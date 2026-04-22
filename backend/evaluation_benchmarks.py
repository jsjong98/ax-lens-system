"""
평가 (Evaluation / Talent Management) 선도사 AI 적용 사례 — Background BM (PwC 큐레이션).

Doosan HR L2 '평가' · 'TM' · 'DS' · '육성' 등 평가/인사 의사결정 관련 프로세스에
자동 주입되는 기본 벤치마킹 데이터.

**동작 원칙** (recruit_benchmarks.py 와 동일 패턴):
- 엑셀 L2 매칭 시 _wf_benchmark_table['__background__'] 에 자동 주입 (is_background=True)
- Step 1 기본 설계 프롬프트에 모두 포함됨 → Perplexity 검색 없이도 Step 1 정상 실행
- UI 에서 파란색으로 하이라이트, '추가 벤치마킹' 버튼으로 동적 보강 가능
- Task 이름 attribution (attribute_task_name) 에도 동일 매칭 키워드 사용

**데이터 소스** (PwC Analysis 슬라이드 원문 기반):
- IBM – Trustworthy AI for Employee Experience
- IBM – Watson Talent: The Business Case for AI in HR
- Unilever – The future of skills: using tech to put people first
- Unilever – FLEX Experiences

**ER Value Chain** (PwC 정의):
전략·기준 설계 → 성과·역량 진단 → 인사리뷰 및 인사 결정 → 육성계획 및 후속관리
"""
from __future__ import annotations

from typing import TypedDict


# ═══════════════════════════════════════════════════════════════════
# 1) 사례별 핵심 정보
# ═══════════════════════════════════════════════════════════════════

class EvaluationCase(TypedDict):
    case_no: int
    title: str                     # 벤치마킹 사례 제목 (attribution prefix 원본)
    match_keywords: list[str]      # Task 이름 매칭 키워드 (부분 문자열, 대소문자 무시)
    applicable_l2: list[str]       # 두산 L2 매칭 (UI 표시 조건)
    companies: list[str]           # 해당 사례 적용 Player (실명)


# 평가 도메인 L2 매칭 후보 — 두산 L2 명칭이 확정되지 않아 가능한 후보 모두 포함
_L2_EVAL_PLANNING = ["평가 기획", "평가", "TM", "Talent Management"]
_L2_EVAL_OPS      = ["평가 운영", "평가", "TM", "DS", "Talent Management"]
_L2_DEVELOPMENT   = ["육성", "TM", "성장관리", "Career Development"]


EVALUATION_CASES: list[EvaluationCase] = [
    {
        "case_no": 1,
        "title": "스킬 기반 평가전략 및 기준체계 수립",
        "match_keywords": [
            "평가전략", "평가 전략", "평가기준", "평가 기준", "기준체계", "평가 체계",
            "Skill 체계", "스킬 체계", "Skill 체계 정비", "평가 체계 수립",
            "평가 제도", "평가제도",
        ],
        "applicable_l2": _L2_EVAL_PLANNING,
        "companies": ["IBM"],
    },
    {
        "case_no": 2,
        "title": "스킬 기반 역량 설계",
        "match_keywords": [
            "역량 설계", "역량설계", "역량 기준", "역할별 Skill", "역할별 스킬",
            "스킬 인벤토리", "Skill Inventory", "skill inventory",
            "직무 역량", "직무-스킬", "스킬 Taxonomy", "스킬 매핑",
        ],
        "applicable_l2": _L2_EVAL_PLANNING,
        "companies": ["Unilever"],
    },
    {
        "case_no": 3,
        "title": "AI 기반 성과·스킬·잠재력 통합 진단",
        "match_keywords": [
            "성과 진단", "성과진단", "역량 진단", "역량진단", "잠재력 진단", "잠재력",
            "성과 평가", "역량 평가", "통합 진단", "AI 평가", "평가 정밀도",
            "편향 탐지", "평가 편향", "Skill Inference", "스킬 추론",
            "Watson Analysis",
        ],
        "applicable_l2": _L2_EVAL_OPS,
        "companies": ["IBM"],
    },
    {
        "case_no": 4,
        "title": "스킬 기반 개인 역량 진단 및 전환 경로 도출",
        "match_keywords": [
            "개인 역량 진단", "개인역량진단", "스킬 Gap", "스킬 갭", "Skill Gap",
            "전환 경로", "재배치", "내부이동", "내부 이동", "리스킬", "업스킬",
            "Reskill", "Upskill", "스킬 프로파일",
        ],
        "applicable_l2": _L2_EVAL_OPS,
        "companies": ["Unilever"],
    },
    {
        "case_no": 5,
        "title": "내부인재 추천 및 승진 의사결정 지원",
        "match_keywords": [
            "내부인재 추천", "내부 인재 추천", "승진", "승진 의사결정", "승진의사결정",
            "보상 반영", "Payroll", "payroll", "HiRo", "인사결정", "인사 결정",
            "승진 후보", "보상 결정", "후보군 검토",
        ],
        "applicable_l2": _L2_EVAL_OPS,
        "companies": ["IBM"],
    },
    {
        "case_no": 6,
        "title": "직원 프로필 기반 프로젝트 매칭 고도화",
        "match_keywords": [
            "프로젝트 매칭", "직원 프로필", "직원프로필", "사내 프로젝트",
            "Flex Experiences", "flex experiences", "사내 인재 매칭",
            "역량 매칭", "프로젝트 적합도", "공정성 검사",
        ],
        "applicable_l2": _L2_EVAL_OPS,
        "companies": ["Unilever"],
    },
    {
        "case_no": 7,
        "title": "스킬 기반 맞춤형 육성경로 설계 및 커리어 지원",
        "match_keywords": [
            "육성경로", "육성 경로", "커리어 경로", "커리어 지원", "맞춤형 육성",
            "성장 경로", "학습 경로", "Blue Matching", "blue matching",
            "Myca", "myca", "Your Learning", "your learning",
            "IDP", "학습 추천", "학습 콘텐츠", "커리큘럼 추천",
        ],
        "applicable_l2": _L2_DEVELOPMENT,
        "companies": ["IBM"],
    },
]


# ═══════════════════════════════════════════════════════════════════
# 2) Player 프로파일 — IBM / Unilever 개요
# ═══════════════════════════════════════════════════════════════════

class PlayerProfile(TypedDict):
    name: str
    theme: str
    focus: str
    key_points: list[str]
    core_solution: str
    ai_technology: list[str]
    source: str


EVALUATION_PLAYERS: list[PlayerProfile] = [
    {
        "name": "IBM",
        "theme": "스킬 기반 평가·인사결정·육성 통합 고도화",
        "focus": (
            "Skill 분석 기반 평가 데이터를 기반으로 성과 예측, 승진·보상 의사결정 지원, "
            "경력·배치 추천까지 연계하는 Skill 기반 AI 평가 운영 체계 구축"
        ),
        "key_points": [
            "People Data Platform (Workforce 360): 35+ 시스템에 분산된 HR 데이터를 통합, 직원단위 HR 마스터 DB 구성",
            "AI Agent (HiRo Agent Orchestrate) 기반으로 승진 결정 → 보상 반영 → Payroll 연계까지 E2E 프로세스 수행",
            "스킬 분석 기반 배치(Blue Matching)·커리어 경로(Myca)·학습(Your Learning) 연계 육성 지원",
        ],
        "core_solution": "People Data Platform + HiRo Agent Orchestrate + Blue Matching · Myca · Your Learning",
        "ai_technology": [
            "Watson 평가 편향 탐지", "Skill Inference", "Watson Analysis",
            "HiRo Agent Orchestrate", "LLM 기반 문서 생성", "API 연계",
        ],
        "source": "IBM – Trustworthy AI for Employee Experience; IBM – Watson Talent: The Business Case for AI in HR",
    },
    {
        "name": "Unilever",
        "theme": "스킬 기반 내부인재 매칭·배치 고도화",
        "focus": (
            "AI 를 활용해 스킬 데이터를 기반으로 개인 역량을 진단하고, 이를 내부 프로젝트·직무와 "
            "연결함으로써 평가를 인력 재배치까지 확장"
        ),
        "key_points": [
            "글로벌 노동시장 데이터 + 기업 내부 데이터를 결합한 스킬 인벤토리 (직무당 평균 34개 스킬 식별)",
            "개인화 스킬 분석: 스킬 프로파일 생성 + 목표 직무·조직 필요 스킬과의 Gap 분석",
            "Flex Experiences: 스킬 적합도·성장 가능성·가용성을 종합한 AI 프로젝트 매칭 + 규칙·공정성 검사 (예산·조직 정책·승인 규칙 + 편향·차별 방지)",
        ],
        "core_solution": "Flex Experiences + 스킬 인벤토리",
        "ai_technology": [
            "NLP 기반 스킬 추출", "ML 기반 스킬 Taxonomy",
            "머신러닝 기반 적합도 점수화", "실시간 노동시장 데이터 반영",
            "규칙 기반 공정성·편향 방지 검사",
        ],
        "source": "Unilever – The future of skills: using tech to put people first; Unilever – FLEX Experiences",
    },
]


# ═══════════════════════════════════════════════════════════════════
# 3) 통합 시사점
# ═══════════════════════════════════════════════════════════════════

INTEGRATED_INSIGHTS: dict[str, str] = {
    "headline": (
        "평가 AX 는 결과 도출과 후속 인사 활용을 통합 HR·스킬 데이터 기반의 "
        "E2E 판단지원 체계로 고도화되고 있음"
    ),
    "summary": (
        "Skill 기반 통합 DB 와 AI 를 기반으로 진단·의사결정·육성계획까지 E2E 로 지원되며, "
        "결과의 재반영을 통해 데이터와 운영이 함께 정교화되는 구조로 설계됨"
    ),
    "ai_process_principle": (
        "평가 프로세스는 결과 확정 중심이 아니라, 기준 설계부터 인사결정·육성까지 연결되는 "
        "E2E 흐름으로 확장되어야 한다. 평가 결과가 단순 산출물에 그치지 않고 후속 인사 활용으로 "
        "이어져야 한다."
    ),
    "ai_application_principle": (
        "평가 AI 는 평가 결과 활용을 넘어, 스킬 진단·편향 감지 등 평가 결과 전 단계부터 판단을 "
        "지원해야 한다. 통합 HR·스킬 데이터 기반으로 진단·매칭·추천을 수행하는 데이터 기반 "
        "판단지원 구조로 구현되어야 한다."
    ),
    "value_chain": (
        "평가 value chain: 전략·기준 설계 → 성과·역량 진단 → 인사리뷰 및 인사 결정 → 육성계획 및 후속관리"
    ),
}


# ═══════════════════════════════════════════════════════════════════
# 4) 벤치마킹 테이블 row 데이터 — _wf_benchmark_table 자동 주입용
# ═══════════════════════════════════════════════════════════════════

_COMPANY_META: dict[str, dict[str, str]] = {
    "IBM": {
        "company_type": "Tech 선도",
        "industry": "IT 솔루션",
        "infrastructure": "People Data Platform + HiRo Agent Orchestrate + Workforce 360",
    },
    "Unilever": {
        "company_type": "非Tech 실제 구현",
        "industry": "글로벌 소비재",
        "infrastructure": "Flex Experiences + 스킬 인벤토리",
    },
}


_CASE_ROW_DETAILS: dict[tuple[int, str], dict[str, str]] = {
    (1, "IBM"): {
        "ai_adoption_goal": "AI 분석이 가능하도록 평가 기준과 Skill 체계 정비",
        "ai_technology": "Watson Analysis · Skill Inference",
        "key_data": "기존 평가 제도·기준 · Skill 체계 · 직무 정보",
        "adoption_method": "Watson Talent 기반 평가 체계·Skill Taxonomy 정비",
        "use_case": (
            "AI 분석이 가능하도록 평가 기준과 Skill 체계를 사전에 정비. 이후 단계인 "
            "성과·역량 진단에서 AI 가 활용 가능한 기반을 구축 (평가 항목·기준 표준화 + Skill DB 구성)"
        ),
        "outcome": "평가 기준 체계화 + AI 활용 가능한 스킬 Taxonomy 확보",
        "implication": "AI 평가 도입 전 **평가 기준과 Skill 체계의 일관된 정비** 가 선행되어야 함",
    },
    (2, "Unilever"): {
        "ai_adoption_goal": "인재 이동·배치가 가능하도록 역할별 필요 Skill 과 역량 기준 체계화",
        "ai_technology": "NLP 기반 스킬 추출 · ML 기반 스킬 Taxonomy",
        "key_data": "글로벌 노동시장 데이터 · 기업 내부 역할/직무 데이터",
        "adoption_method": "스킬 인벤토리 구축 + 직무당 스킬 매핑",
        "use_case": (
            "글로벌 노동시장 데이터와 내부 데이터를 결합해 역할별 필요 Skill 과 역량 기준을 체계화. "
            "직무당 평균 34개 스킬을 식별하여 추후 개인 역량 진단·매칭의 기반으로 활용"
        ),
        "outcome": "직무 전환·배치가 가능한 표준 Skill 체계 확보",
        "implication": "**직무-스킬 매핑 DB** 가 있어야 후속 매칭/진단 고도화 가능",
    },
    (3, "IBM"): {
        "ai_adoption_goal": "평가 정밀도와 인재 판단의 객관성 제고",
        "ai_technology": "Watson 평가 편향 탐지 · Skill Inference · Watson Analysis",
        "key_data": "프로젝트 결과 · 동료 피드백 · 다중 소스 분석 데이터",
        "adoption_method": "3 개 AI 모듈 통합 진단 (편향 탐지 + 스킬 추론 + 잠재력 분석)",
        "use_case": (
            "성과 등급, 스킬별 숙련도 레벨, 미래 잠재력 점수를 AI 가 통합 진단. "
            "Watson 평가 편향 탐지로 매니저 평가 데이터 분석·편향 점검, Skill Inference 로 "
            "직원 실제 업무활동에서 AI 가 스킬 추론, Watson Analysis 로 직원의 경험·프로젝트·"
            "학습·스킬 데이터를 바탕으로 미래 역할 적합성 및 성과 가능성 판단"
        ),
        "outcome": "평가 정밀도 향상 + 인재 판단 객관성 제고 + 편향 탐지를 통한 공정성 강화",
        "implication": "**편향 탐지 + 스킬 추론 + 잠재력 분석** 3 대 축을 동시 구현해야 E2E 정밀도 확보",
    },
    (4, "Unilever"): {
        "ai_adoption_goal": "스킬 Gap 분석 기반 내부이동·재배치 제안",
        "ai_technology": "NLP 스킬 추출 · 스킬 Gap 분석 · ML 기반 매칭",
        "key_data": "개인 스킬 프로파일 · 목표 직무/조직 필요 스킬 · 실시간 노동시장 데이터",
        "adoption_method": "스킬 인벤토리 + 개인화 스킬 분석 + 목표 기준 Gap 분석",
        "use_case": (
            "직원 ID 별 기본 인사정보·스킬 상세를 기반으로 스킬 프로파일을 생성하고, 목표 직무/"
            "조직 필요 스킬과의 Gap 을 분석. 결과를 바탕으로 내부 직무 전환 추천, 리스킬·업스킬 "
            "경로 설계, 조직차원의 인력 재배치·계획을 도출"
        ),
        "outcome": "조직 차원 인력 재배치·계획 수립 + 리스킬·업스킬 경로 자동 설계",
        "implication": "**개인 스킬 프로파일** 을 실시간 업데이트 하는 자동화 파이프라인 필요",
    },
    (5, "IBM"): {
        "ai_adoption_goal": "승진 후보 분석부터 보상 반영까지 연결하여 인사결정 일관성 제고",
        "ai_technology": "HiRo Agent Orchestrate · LLM 기반 문서 생성 · API 연계",
        "key_data": "승진 후보 데이터 · 평가·성과 이력 · 보상 체계",
        "adoption_method": "HiRo Agent 기반 E2E 승진-보상 자동화 (HR 매니저 + AI Agent 협업)",
        "use_case": (
            "HR 매니저가 승진 기준을 설정하면 HiRo Agent Orchestrate 가 승진 후보 데이터 수집·분석 "
            "(API 호출 + LLM 분석), 승진 결과 정리 및 의사결정 사항 취합 (LLM 기반 문서 생성), "
            "보상 반영 및 Payroll 연계 (API 호출) 까지 E2E 수행. 최종 인사 결정은 HR 매니저가 확정"
        ),
        "outcome": "승진 결정부터 보상 반영까지 일관성 있는 자동화 프로세스 구축",
        "implication": "**승진 의사결정 Agent** 는 HR-Payroll-평가 시스템 간 API 연결이 필수",
    },
    (6, "Unilever"): {
        "ai_adoption_goal": "직원 프로필·역량·경험 정보 기반 프로젝트 매칭 지원",
        "ai_technology": "머신러닝 기반 적합도 점수화 · 규칙 기반 공정성 검사",
        "key_data": "직원 프로필 · 프로젝트 요구 스킬 · 성장 가능성 · 가용성 · 조직 정책",
        "adoption_method": "Flex Experiences AI 프로젝트 매칭 시스템 (Flexible Experience)",
        "use_case": (
            "프로젝트 목표·기간, 필요 역할·스킬·경험, 필요 인원·시간투입 비율을 입력받아 "
            "AI 가 스킬 적합도·성장 가능성·경력 연관성·숙련도 수준·근무형태 등을 종합 점수화. "
            "동시에 예산·조직 정책·승인 규칙 적용 (최소 재직 기간, 비자/노동법 제한, 승인 필요 "
            "여부, 보상범위 적합성 등 24개의 규칙 검증) + 성별·인종·연령 등에 따른 편향·차별 "
            "방지 검사 수행"
        ),
        "outcome": "사내 프로젝트 매칭 제안 (내부 직무 전환 기회) + 직원 스킬·경력 프로필 자동 업데이트 (경험·숙련도 반영)",
        "implication": "**프로젝트 매칭에 공정성 검사** 를 내재화해야 편향·차별 이슈 방지 가능",
    },
    (7, "IBM"): {
        "ai_adoption_goal": "개인별 스킬 분석 기반 학습·이동·성장 경로 제안",
        "ai_technology": "Blue Matching · Myca · Your Learning · Skill Inference",
        "key_data": "개인 스킬 프로파일 · 목표 역할 · 학습 콘텐츠 · 조직 내 포지션",
        "adoption_method": "3 종 AI 서비스 연계 (Blue Matching: 포지션 매칭, Myca: 커리어 추천, Your Learning: 학습 추천)",
        "use_case": (
            "Skill Inference 기반 현재 스킬·숙련도 진단 + 목표 역할 대비 Skill Gap 분석을 "
            "기반으로, Blue Matching 이 '어떤 스킬을 보유하고 있는가?' 를 분석해 적합한 포지션 "
            "매칭 및 제안, Myca 는 '어떤 스킬이 부족한가?' 를 분석해 커리어 경로 추천, "
            "Your Learning 은 '어떤 학습이 필요한가?' 를 분석해 학습 콘텐츠 및 커리큘럼 추천"
        ),
        "outcome": "직원 개인별 맞춤형 육성 경로 자동 설계 + 학습-성장-이동의 연속성 확보",
        "implication": "**진단 → 경로 추천 → 학습 연결** 이 하나의 Agent 서비스로 통합되어야 EX 향상 가능",
    },
}


# ═══════════════════════════════════════════════════════════════════
# 5) Helpers — recruit_benchmarks 와 동일 시그니처
# ═══════════════════════════════════════════════════════════════════

def build_background_benchmark_rows(filter_l2: list[str] | None = None) -> list[dict]:
    """Background BM row 리스트 (BenchmarkTableRow 형식 + is_background=True)."""
    filter_set = {str(n).strip() for n in filter_l2} if filter_l2 else None
    rows: list[dict] = []
    for case in EVALUATION_CASES:
        if filter_set and not any(l2 in filter_set for l2 in case["applicable_l2"]):
            continue
        case_no = case["case_no"]
        title = case["title"]
        for company in case["companies"]:
            meta = _COMPANY_META.get(company, {})
            detail = _CASE_ROW_DETAILS.get((case_no, company), {})
            if not detail:
                continue
            rows.append({
                "source": company,
                "company_type": meta.get("company_type", ""),
                "industry": meta.get("industry", ""),
                "process_area": title,
                "ai_adoption_goal": detail["ai_adoption_goal"],
                "ai_technology": detail["ai_technology"],
                "key_data": detail["key_data"],
                "adoption_method": detail["adoption_method"],
                "use_case": detail["use_case"],
                "outcome": detail["outcome"],
                "infrastructure": meta.get("infrastructure", ""),
                "implication": detail["implication"],
                "url": "",
                "is_background": True,
                "benchmark_case_no": case_no,
                "benchmark_title": title,
                "benchmark_domain": "evaluation",   # 도메인 식별 (recruit/evaluation 구분용)
            })
    return rows


def get_background_cases_for_tasks(tasks) -> list[EvaluationCase]:
    """엑셀 task 리스트에서 L2 추출 후 매칭되는 사례 반환."""
    if not tasks:
        return []
    l2_names = {getattr(t, "l2", "") or "" for t in tasks}
    l2_set = {n for n in l2_names if n}
    if not l2_set:
        return []
    return [c for c in EVALUATION_CASES if any(l2 in l2_set for l2 in c["applicable_l2"])]


def get_background_cases_by_l2(l2_names: list[str]) -> list[EvaluationCase]:
    if not l2_names:
        return []
    l2_set = {str(n).strip() for n in l2_names if n}
    return [c for c in EVALUATION_CASES if any(l2 in l2_set for l2 in c["applicable_l2"])]


def match_benchmark_for_task(task_name: str) -> EvaluationCase | None:
    """Task 이름 키워드 기반 매칭 (recruit 와 다른 도메인이므로 별도 함수)."""
    if not task_name:
        return None
    tn = task_name.lower()
    for case in EVALUATION_CASES:
        for kw in case["match_keywords"]:
            if kw.lower() in tn:
                return case
    return None


def attribute_task_name(task_name: str) -> tuple[str, str | None]:
    """Task 이름에 매칭되는 벤치마킹 title 이 있으면 prefix 된 이름 반환."""
    if not task_name:
        return task_name or "", None
    case = match_benchmark_for_task(task_name)
    if not case:
        return task_name, None
    return f"{case['title']} - {task_name}", case["title"]


def format_players_for_prompt(players: list[PlayerProfile]) -> str:
    if not players:
        return ""
    lines = ["## 🏛 Background BM — Player 개요 (Doosan HR 큐레이션 · 평가 도메인)"]
    for p in players:
        lines.append("")
        lines.append(f"### {p['name']} — {p['theme']}")
        lines.append(f"- 접근: {p['focus']}")
        lines.append(f"- 핵심 솔루션: {p['core_solution']}")
        lines.append(f"- 기술 스택: {', '.join(p['ai_technology'])}")
        lines.append("- 특징:")
        for kp in p["key_points"]:
            lines.append(f"  · {kp}")
    return "\n".join(lines) + "\n"


def format_insights_for_prompt() -> str:
    ii = INTEGRATED_INSIGHTS
    return (
        "## 💡 Background BM — 통합 시사점 (평가 도메인)\n"
        f"**Headline**: {ii['headline']}\n\n"
        f"**핵심 Summary**: {ii['summary']}\n\n"
        f"**AI 기반 프로세스 원칙**: {ii['ai_process_principle']}\n\n"
        f"**AI 적용 방식 원칙**: {ii['ai_application_principle']}\n\n"
        f"**Value Chain**: {ii['value_chain']}\n"
    )


def get_applicable_players_for_tasks(tasks) -> list[PlayerProfile]:
    """평가 도메인 L2 가 매칭되면 2 사 프로필 전체 반환, 아니면 빈 리스트."""
    applicable_cases = get_background_cases_for_tasks(tasks)
    if not applicable_cases:
        return []
    return list(EVALUATION_PLAYERS)
