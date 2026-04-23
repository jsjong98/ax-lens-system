"""
채용 (Recruitment) 선도사 AI 적용 사례 — Background BM (PwC 큐레이션).

Doosan HR L2 '채용 기획' · '채용 운영' 프로세스에 자동 주입되는 기본 벤치마킹 데이터.
main.py 에 포함시키기엔 컨텐츠가 커서 별도 파일로 분리.

**동작 원칙**:
- 엑셀 L2 매칭 시 _wf_benchmark_table['__background__'] 에 자동 주입 (is_background=True)
- Step 1 기본 설계 프롬프트에 모두 포함됨 → Perplexity 검색 없이도 Step 1 정상 실행
- UI 에서 파란색으로 하이라이트, '추가 벤치마킹' 버튼으로 동적 보강 가능
- Task 이름 attribution (attribute_task_name) 에도 동일 매칭 키워드 사용

**데이터 소스** (PwC Analysis 슬라이드 원문 기반):
- Siemens – How to Apply, Frequently Asked Questions (2025)
- Paradox – General Motors Case Study (2022)
- IBM – AI Agents for HR: watsonx Orchestrate (2025)
- The Josh Bersin Company 리포트 (Siemens/GM 관련)
"""
from __future__ import annotations

from typing import TypedDict


# ═══════════════════════════════════════════════════════════════════
# 1) 사례별 핵심 정보 — Task 이름 attribution + UI title chip 용
# ═══════════════════════════════════════════════════════════════════

class RecruitCase(TypedDict):
    case_no: int
    title: str                     # 벤치마킹 사례 제목 (attribution prefix 원본)
    match_keywords: list[str]      # Task 이름 매칭 키워드 (부분 문자열, 대소문자 무시)
    applicable_l2: list[str]       # 두산 L2 매칭 (UI 표시 조건)
    companies: list[str]           # 해당 사례 적용 Player (실명)


RECRUIT_CASES: list[RecruitCase] = [
    {
        "case_no": 1,
        "title": "'스킬 추론' 기반 채용 전략 수립 지원",
        "match_keywords": [
            "스킬 추론", "스킬 갭", "스킬 gap", "스킬 분석",
            "인력 계획", "충원 계획", "헤드카운트", "채용 전략",
            "내부 인재 육성", "내부 채용",
        ],
        "applicable_l2": ["채용", "채용 기획"],
        "companies": ["IBM"],
    },
    {
        "case_no": 2,
        "title": "AI 챗봇을 활용한 지원자 문의 상시 응대",
        "match_keywords": [
            "챗봇", "Chatbot", "chatbot", "문의 응대", "지원자 응대",
            "FAQ", "Q&A", "실시간 응대", "24/7",
        ],
        "applicable_l2": ["채용", "채용 운영"],
        "companies": ["GM", "IBM"],
    },
    {
        "case_no": 3,
        "title": "지원자 맞춤형 공고 추천",
        "match_keywords": [
            "공고 추천", "맞춤 공고", "맞춤형 공고",
            "직무 추천", "공고 매칭", "CV 분석",
        ],
        "applicable_l2": ["채용", "채용 운영"],
        "companies": ["Siemens"],
    },
    {
        "case_no": 4,
        "title": "지원자별 적합도 계산 및 후보자 Shortlist 자동 생성",
        "match_keywords": [
            "적합도", "Shortlist", "shortlist", "쇼트리스트",
            "후보자 매칭", "지원자-직무 매칭", "우선순위 라우팅", "우선순위",
            "후보자 선별", "후보 리스트",
        ],
        "applicable_l2": ["채용", "채용 운영"],
        "companies": ["Siemens", "IBM"],
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
        "applicable_l2": ["채용", "채용 운영"],
        "companies": ["GM", "IBM"],
    },
    {
        "case_no": 6,
        "title": "전형 일정 자동 조율",
        "match_keywords": [
            "일정 조율", "일정조율", "면접 일정", "전형 일정",
            "캘린더", "스케줄링", "Scheduling", "scheduling",
            "일정 자동", "일정 제안", "일정 확정",
        ],
        "applicable_l2": ["채용", "채용 운영"],
        "companies": ["GM"],
    },
    {
        "case_no": 7,
        "title": "신규입사자 온보딩 자동화",
        "match_keywords": [
            "온보딩", "Onboarding", "onboarding",
            "입사 안내", "입사 준비", "신규입사자",
            "계정 생성", "입사서류", "입사 Workflow",
        ],
        "applicable_l2": ["채용", "채용 운영"],
        "companies": ["IBM"],
    },
]


# ═══════════════════════════════════════════════════════════════════
# 2) Player 프로파일 — Siemens / GM / IBM 개요 (Step 1 프롬프트 주입용)
# ═══════════════════════════════════════════════════════════════════

class PlayerProfile(TypedDict):
    name: str
    theme: str                    # 핵심 Theme (한 줄)
    focus: str                    # 접근 방향
    key_points: list[str]         # 특징 bullet
    core_solution: str            # 핵심 솔루션 이름
    ai_technology: list[str]      # 기술 스택
    source: str                   # PPT 출처 주석


RECRUIT_PLAYERS: list[PlayerProfile] = [
    {
        "name": "Siemens",
        "theme": "스킬 기반 최적 인력 매칭 고도화",
        "focus": "산업기술 업종 특성에 맞는 고숙련·희소 기술 보유 인재 확보",
        "key_points": [
            "'기술 직무' 중심 채용 구조 (엔지니어링·기술 중심, 비즈니스 특성상 기술직군 채용 다수)",
            "'고숙련·희소 기술' 보유 인재 확보 중요 (고부가가치 산업군 시장의 핵심 동력은 '인적 자원')",
            "자체 구축 스킬 데이터베이스 보유 ('My Skills' 플랫폼 구축 및 운영)",
        ],
        "core_solution": "AI 기반 스킬 매칭 플랫폼 + My Skills",
        "ai_technology": ["NLP (자연어 처리)", "Data Parsing", "RPA", "ML/DL", "추천시스템", "워드 임베딩"],
        "source": "Siemens – How to Apply, FAQ (2025); Eightfold – 9 Companies Hire Better; Josh Bersin – Enterprise Talent Intelligence (2024)",
    },
    {
        "name": "GM",
        "theme": "대규모 채용 운영 효율화",
        "focus": "단순·반복적 채용 운영 업무를 AI 챗봇에 위임, 채용 담당자는 전략·기획성 업무에 집중",
        "key_points": [
            "구조적 High-Volume 채용환경 (대규모 제조기업 특성상 포지션 오픈·지원자 유입 상시 대량 발생)",
            "'지원자 경험 개선'을 핵심 과제로 고려 (원활한 채용 운영을 통한 지원자 경험 개선을 HR 핵심 과제로 선정)",
            "완성차 산업의 인재 채용 복잡성 증대 (전기차·SDV 중심의 비즈니스 모델 전환 영향으로 복합 인재 수요 확대)",
        ],
        "core_solution": "Ev-E (대화형 AI 챗봇)",
        "ai_technology": ["대화형 AI", "NLP", "Rule-based 필터링", "Calendar API 연동"],
        "source": "Paradox – General Motors Case Study (2022); Josh Bersin – GM Interview Scheduling Automation (2022); TechTarget – GM's Automated Recruiting (2024)",
    },
    {
        "name": "IBM",
        "theme": "스킬 기반 전략적 채용 계획 수립 + Agentic AI 기반 운영 자동화",
        "focus": "watsonx Orchestrate 를 통해 데이터·시스템·AI 에이전트를 유기적으로 연결하여 채용 전반 value chain 지능화·자동화",
        "key_points": [
            "채용 프로세스 內 세부 Task 를 수행하는 개별 AI Agent 개발 + Orchestration 구조로 연결",
            "스킬 기반 의사결정 지원 + 운영 자동화 동시 구현",
            "AskHR 플랫폼으로 지원자 응대부터 신규입사자 온보딩까지 End-to-End 자동화",
        ],
        "core_solution": "watsonx Orchestrate + AskHR",
        "ai_technology": [
            "OCR", "Automation", "NLP", "머신러닝", "딥러닝", "LLM",
            "최적화", "추천시스템", "Ranking/Scoring",
        ],
        "source": "IBM – AI Agents for HR: watsonx Orchestrate (2025); IBM – Talent Acquisition with watsonx Orchestrate (2025); IBM – AI in Recruiting (2025)",
    },
]


# ═══════════════════════════════════════════════════════════════════
# 3) 통합 시사점 — Step 1 프롬프트 강조 섹션
# ═══════════════════════════════════════════════════════════════════

INTEGRATED_INSIGHTS: dict[str, str] = {
    "headline": (
        "채용 영역에서 AI 도입의 효과를 극대화하기 위해서는 운영 자동화와 선발 고도화가 "
        "하나의 데이터 흐름 위에서 유기적으로 작동하도록 설계되어야 함"
    ),
    "summary": (
        "스킬 데이터 체계를 기반으로 최적 인재 선발 절차를 고도화하고, 반복적 채용 운영은 "
        "자동화하여 업무 효율성을 제고함"
    ),
    "ai_process_principle": (
        "채용 프로세스는 신입/경력/내부 채용 등 개별 프로세스 단위가 아닌, "
        "데이터 흐름 중심인 value chain 으로 정의되어야 한다. 개별 트랙별 분절된 프로세스로는 "
        "스킬 기반 요구 인력 분석 등이 효과적으로 구현되기 어렵다."
    ),
    "ai_application_principle": (
        "채용 전 단계의 데이터가 하나의 흐름으로 연결되는 통합 아키텍처 설계가 필요하며, "
        "AI 매칭·평가의 실질적 기반이 되는 직무-스킬 체계의 정의 및 스킬 DB 구축이 선행되어야 한다. "
        "지원자 데이터가 단계별로 누적되면서 프로세스 전반에서 유기적으로 연결되는 구조를 지향한다."
    ),
    "value_chain": (
        "채용 value chain: 채용 전략·기획 → 모집·유입 → 소싱 → 서류·면접 전형 운영 및 평가 → 채용 후속관리"
    ),
}


# ═══════════════════════════════════════════════════════════════════
# 4) 벤치마킹 테이블 row 데이터 — _wf_benchmark_table 자동 주입용
#    (사례 × 회사) 조합으로 각 row 생성 (총 10 행)
#    구조: main.py 의 BenchmarkTableRow 와 동일 + is_background=True + benchmark_case_no
# ═══════════════════════════════════════════════════════════════════

# 회사별 고정 메타 (source 로 들어감)
_COMPANY_META: dict[str, dict[str, str]] = {
    "IBM": {
        "company_type": "Tech 선도",
        "industry": "IT 솔루션",
        "infrastructure": "watsonx Orchestrate + AskHR",
    },
    "GM": {
        "company_type": "非Tech 실제 구현",
        "industry": "완성차 제조",
        "infrastructure": "Ev-E 대화형 AI 챗봇 + Calendar API",
    },
    "Siemens": {
        "company_type": "非Tech 실제 구현",
        "industry": "산업기술 제조",
        "infrastructure": "AI 스킬 매칭 플랫폼 + My Skills DB",
    },
}


# 사례 × 회사 조합별 use_case / outcome / implication / ai_technology / key_data / adoption_method
# (dict key: (case_no, company))
_CASE_ROW_DETAILS: dict[tuple[int, str], dict[str, str]] = {
    (1, "IBM"): {
        "ai_adoption_goal": "스킬 데이터 기반 전략적 채용 계획 수립",
        "ai_technology": "LLM · 머신러닝 · 최적화 (watsonx Orchestrate)",
        "key_data": "스킬 Inventory · 인력 충원 요청 · 직무 체계 · 인사/조직 정보",
        "adoption_method": "watsonx Orchestrate 내 스킬 추론 Agent",
        "use_case": (
            "인력 충원 요청이 발생한 포지션의 스킬 요구사항을 파악하고 내부 스킬 Data 기반으로 "
            "보유 스킬-수요 스킬 간 Gap 을 분석, 내부 인재 육성(내부 채용) vs 외부 채용 여부를 "
            "AI 가 의사결정 지원"
        ),
        "outcome": "단순 헤드카운트 계획이 아닌 스킬 데이터 기반의 전략적 채용 계획 수립",
        "implication": "충원 의사결정 단계에 AI 를 도입하려면 **스킬 Inventory + 인력 Pool DB** 선행 구축 필요",
    },
    (2, "GM"): {
        "ai_adoption_goal": "대규모 지원자 응대 자동화 · 지원자 경험 개선",
        "ai_technology": "대화형 AI (Ev-E) · NLP · Rule-based 필터링",
        "key_data": "지원자 프로필 · 채용 공고 · FAQ DB",
        "adoption_method": "Ev-E 챗봇 배포 (웹·모바일 상시 가동)",
        "use_case": (
            "'Ev-E' 대화형 AI 챗봇을 통해 지원 방법·자격 요건·필수 역량·전형 일정·직무 정보·"
            "우대 조건 등 반복적인 문의를 24/7 자동 응대"
        ),
        "outcome": "채용 담당자 반복 업무 부담 감소 · Candidate Experience 개선",
        "implication": "고Volume 채용 환경에서 **챗봇 기반 문의 응대**는 단기 Quick Win 이 명확함",
    },
    (2, "IBM"): {
        "ai_adoption_goal": "지원자 응대 자동화 + 내부 HR 업무 통합",
        "ai_technology": "LLM · NLP · Agentic AI (AskHR)",
        "key_data": "지원자 DB · HR 정책 문서 · FAQ",
        "adoption_method": "AskHR 플랫폼 (watsonx Orchestrate 기반)",
        "use_case": (
            "'AskHR' 플랫폼을 통해 지원자 문의 응대와 내부 HR 문의를 동일 인터페이스로 처리. "
            "채용 외 HR 전 영역으로 확장 가능한 Agentic 구조"
        ),
        "outcome": "채용 챗봇을 HR 전체 플랫폼 일부로 통합 운영",
        "implication": "챗봇을 채용 국한이 아닌 **HR 전사 플랫폼**으로 기획하면 장기 ROI 확대",
    },
    (3, "Siemens"): {
        "ai_adoption_goal": "지원자-직무 스킬 매칭 고도화 · 적합 지원자 유입률 향상",
        "ai_technology": "NLP · Data Parsing · RPA · 추천시스템 · 워드 임베딩",
        "key_data": "지원자 CV · 공고 요구 스킬 · My Skills DB",
        "adoption_method": "AI 스킬 매칭 플랫폼 + 채용 Portal 연동",
        "use_case": (
            "지원자 CV 및 보유 스킬 데이터를 분석하여 스킬 기반 직무-지원자 매칭을 고도화하고 "
            "최적의 채용 공고를 추천 (예: 공고 A 95%, 공고 B 88%, 공고 C 72% 적합도)"
        ),
        "outcome": "지원자 탐색 비용 감소 · 기업 입장 적합도 높은 지원자 유입률 향상",
        "implication": "**직무-스킬 체계 + 스킬 DB** 가 선행되어야 매칭 품질 확보 가능",
    },
    (4, "Siemens"): {
        "ai_adoption_goal": "스킬 매칭 기반 지원자 선별 정밀도 향상",
        "ai_technology": "NLP · 추천시스템 · ML/DL · Scoring",
        "key_data": "CV · 채용 공고 · 스킬 DB (정규화·매핑된 보유/요구 스킬)",
        "adoption_method": "AI 매칭 플랫폼 내 Scoring 모듈",
        "use_case": (
            "지원자 CV 와 공고 요구 스킬을 스킬 DB 기준으로 정규화·매핑한 후 적합도를 정량 "
            "계산, Pool 내 우선 검토 후보자 Shortlist 를 자동 생성"
        ),
        "outcome": "수작업 스크리닝 대체 → 소싱 속도·선발 품질 동시 향상",
        "implication": "Shortlist 자동화는 **정량 Scoring 기준과 검증 룰셋** 이 핵심",
    },
    (4, "IBM"): {
        "ai_adoption_goal": "인재 Pool 기반 우선 검토 후보자 자동 매칭",
        "ai_technology": "Ranking/Scoring · 머신러닝 · 딥러닝",
        "key_data": "인재 Pool DB · 공고 요구 스펙 · 스킬/지식/경험 데이터",
        "adoption_method": "watsonx Orchestrate 의 Matching Agent",
        "use_case": (
            "내부 인재 Pool + 외부 지원자 대상 공고별 스킬/지식/경험 기반 적합도 계산, "
            "우선 검토 후보자 리스트를 자동 생성 (Pool 內 적합 후보 매칭 및 우선순위화)"
        ),
        "outcome": "내·외부 인재 통합 Pool 활용 · 선발 품질 동시 향상",
        "implication": "**내부 인재 Pool 구축 + 외부 지원자 통합 파이프라인** 설계가 장기 투자 필요",
    },
    (5, "GM"): {
        "ai_adoption_goal": "대규모 지원자 평가 사전 업무 자동화",
        "ai_technology": "대화형 AI (Ev-E) · Rule-based 필터링",
        "key_data": "지원자 응답 · 자격 요건 기준 · 입사지원서",
        "adoption_method": "Ev-E 챗봇 기반 Knock-out 대화 플로우",
        "use_case": (
            "지원자와의 대화를 통해 자격 요건 충족 여부를 1차 검증, 규칙 기반 필터링 알고리즘으로 "
            "충족/미충족/검토 필요로 자동 분류 (Pre-screen)"
        ),
        "outcome": "채용 담당자가 실질 평가에만 집중 가능 · 스크리닝 리드타임 단축",
        "implication": "챗봇 대화 기반 Pre-screen 은 **자격 룰셋 정의와 학습 데이터** 가 핵심",
    },
    (5, "IBM"): {
        "ai_adoption_goal": "지원서 자동 필터링 (서류 1차 스크리닝)",
        "ai_technology": "OCR · NLP · LLM · 분류 모델",
        "key_data": "입사지원서(CV) 텍스트 · 자격 요건 기준표",
        "adoption_method": "watsonx Orchestrate 의 Pre-screen Agent",
        "use_case": (
            "지원서 내 텍스트를 추출하고 자격 충족 여부를 자동 분류. 대규모 지원자 발생 환경에서 "
            "담당자가 실질 평가에만 집중할 수 있도록 선행 업무 자동화"
        ),
        "outcome": "스크리닝 처리량 증가 · 담당자 업무 고부가가치화",
        "implication": "LLM 기반 서류 분류는 **Ground Truth 레이블 데이터 확보** 후 도입 권장",
    },
    (6, "GM"): {
        "ai_adoption_goal": "면접 일정 조율 수작업 최소화 · 채용 사이클 타임 단축",
        "ai_technology": "대화형 AI · Calendar API · 규칙 기반 스케줄링",
        "key_data": "면접관·지원자 캘린더 · 전형 일정표",
        "adoption_method": "Ev-E + Calendar API 실시간 연동",
        "use_case": (
            "면접 일정 제안·선택·확정·변경을 AI 가 자동 처리. 캘린더 API 연동으로 면접관·지원자 "
            "가용 일정을 실시간 반영"
        ),
        "outcome": "일정 조율 리소스 최소화 · 채용 사이클 타임 단축",
        "implication": "완성차·대규모 제조업 구조에서 일정 자동화는 **리소스 절감이 즉시 체감**됨",
    },
    (7, "IBM"): {
        "ai_adoption_goal": "합격자 확정 이후 온보딩 Workflow 자동 실행",
        "ai_technology": "Automation · LLM · Agentic AI (AskHR)",
        "key_data": "합격자 정보 · 입사 준비 체크리스트 · 계정 시스템",
        "adoption_method": "AskHR 기반 온보딩 Agent (End-to-End 자동화)",
        "use_case": (
            "데이터 이관·계정 생성·입사 안내·입사서류 징구 등 온보딩 전 과정을 자동화. AskHR 이 "
            "신규입사자에게 온보딩 진행 방향을 안내하며 담당자 개입 없이도 입사 준비 완결"
        ),
        "outcome": "채용-온보딩 단절 없이 데이터가 연속 흐르는 End-to-End 자동화 실현",
        "implication": "온보딩 자동화 전제는 **채용 시스템-HRIS-계정 시스템 간 데이터 파이프라인**",
    },
}


# ═══════════════════════════════════════════════════════════════════
# 5) Helpers
# ═══════════════════════════════════════════════════════════════════

def build_background_benchmark_rows(filter_l2: list[str] | None = None) -> list[dict]:
    """Background BM row 리스트 (BenchmarkTableRow 형식 + is_background=True).

    Args:
        filter_l2: 주어지면 applicable_l2 매칭되는 사례만 포함. None 이면 전체.

    Returns:
        list of dicts matching BenchmarkTableRow schema (frontend/lib/api.ts)
        + is_background: True, benchmark_case_no: int, benchmark_title: str
    """
    filter_set = {str(n).strip() for n in filter_l2} if filter_l2 else None
    rows: list[dict] = []
    for case in RECRUIT_CASES:
        if filter_set and not any(l2 in filter_set for l2 in case["applicable_l2"]):
            continue
        case_no = case["case_no"]
        title = case["title"]
        for company in case["companies"]:
            meta = _COMPANY_META.get(company, {})
            detail = _CASE_ROW_DETAILS.get((case_no, company), {})
            if not detail:
                continue   # 정의 누락된 조합은 skip
            rows.append({
                "source": company,
                "company_type": meta.get("company_type", ""),
                "industry": meta.get("industry", ""),
                "process_area": title,   # 사례 제목이 process_area 역할 (UI 에서 한눈에 보이게)
                "ai_adoption_goal": detail["ai_adoption_goal"],
                "ai_technology": detail["ai_technology"],
                "key_data": detail["key_data"],
                "adoption_method": detail["adoption_method"],
                "use_case": detail["use_case"],
                "outcome": detail["outcome"],
                "infrastructure": meta.get("infrastructure", ""),
                "implication": detail["implication"],
                "url": "",   # PPT 원문에 URL 없음 (Source 주석은 Player 개요에 보존)
                # Background BM 플래그 (UI 파란색 하이라이트 + is_background 로 구분)
                "is_background": True,
                "benchmark_case_no": case_no,
                "benchmark_title": title,
            })
    return rows


def get_background_cases_for_tasks(tasks) -> list[RecruitCase]:
    """엑셀 task 리스트에서 L2 추출 후 매칭되는 사례 반환 (UI title chip 용)."""
    if not tasks:
        return []
    l2_names = {getattr(t, "l2", "") or "" for t in tasks}
    l2_set = {n for n in l2_names if n}
    if not l2_set:
        return []
    return [c for c in RECRUIT_CASES if any(l2 in l2_set for l2 in c["applicable_l2"])]


def get_background_cases_by_l2(l2_names: list[str]) -> list[RecruitCase]:
    """L2 이름 목록과 매칭되는 사례 반환."""
    if not l2_names:
        return []
    l2_set = {str(n).strip() for n in l2_names if n}
    return [c for c in RECRUIT_CASES if any(l2 in l2_set for l2 in c["applicable_l2"])]


def match_benchmark_for_task(task_name: str) -> RecruitCase | None:
    """Task 이름 키워드 기반으로 매칭되는 사례 1건 반환 (없으면 None)."""
    if not task_name:
        return None
    tn = task_name.lower()
    for case in RECRUIT_CASES:
        for kw in case["match_keywords"]:
            if kw.lower() in tn:
                return case
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
    case = match_benchmark_for_task(task_name)
    if not case:
        return task_name, None
    return f"{case['title']} - {task_name}", case["title"]


def format_players_for_prompt(players: list[PlayerProfile]) -> str:
    """Step 1 프롬프트 주입용 Player 개요 텍스트."""
    if not players:
        return ""
    lines = ["## 🏛 Background BM — Player 개요 (Doosan HR 큐레이션)"]
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
    """Step 1 프롬프트 주입용 통합 시사점 텍스트."""
    ii = INTEGRATED_INSIGHTS
    return (
        "## 💡 Background BM — 통합 시사점\n"
        f"**Headline**: {ii['headline']}\n\n"
        f"**핵심 Summary**: {ii['summary']}\n\n"
        f"**AI 기반 프로세스 원칙**: {ii['ai_process_principle']}\n\n"
        f"**AI 적용 방식 원칙**: {ii['ai_application_principle']}\n\n"
        f"**Value Chain**: {ii['value_chain']}\n"
    )


def get_applicable_players_for_tasks(tasks) -> list[PlayerProfile]:
    """채용 도메인 L2 가 매칭되면 3 사 프로필 전체 반환, 아니면 빈 리스트."""
    applicable_cases = get_background_cases_for_tasks(tasks)
    if not applicable_cases:
        return []
    return list(RECRUIT_PLAYERS)


# 하위 호환 (이전 reference 이름 사용하던 코드를 위한 alias — 점진 제거)
RECRUIT_REFERENCE_BENCHMARKS = RECRUIT_CASES
get_reference_benchmarks_by_l2 = get_background_cases_by_l2
get_reference_benchmarks_for_tasks = get_background_cases_for_tasks
