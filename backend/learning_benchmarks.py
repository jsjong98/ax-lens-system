"""
교육 (Learning & Development) 선도사 AI 적용 사례 — Background BM (PwC 큐레이션).

Doosan HR L2 '교육 기획' · '교육 운영' 프로세스에 자동 주입되는 기본 벤치마킹 데이터.

**동작 원칙** (recruit/evaluation/compensation_benchmarks.py 와 동일 패턴):
- 엑셀 L2 매칭 시 _wf_benchmark_table['__background__'] 에 자동 주입 (is_background=True)
- Step 1 기본 설계 프롬프트에 모두 포함됨 → Perplexity 검색 없이도 Step 1 정상 실행
- UI 에서 파란색으로 하이라이트, '추가 벤치마킹' 버튼으로 동적 보강 가능
- Task 이름 attribution (attribute_task_name) 에도 동일 매칭 키워드 사용

**데이터 소스** (PwC Analysis 슬라이드 원문 기반):
- MIT Sloan – The Learning System at IBM: A Case Study (Qin & Kochan, 2020)
- IBM – Watson Talent: Business Case for AI in HR
- Josh Bersin – IBM in HR Marketplace (2020)
- MS Tech Community (2026.2); Microsoft Learn – People Skills Overview
- Microsoft Inside Track – Viva Learning & LinkedIn Learning Hub Case (2024)
- Novartis – L&D Programs & Channels; René Gessenich (Digital HR Leaders Podcast 2022)
- Simon Brown (CLO, Novartis) – Enabling 130,000 Employees to Grow; Gloat – Novartis Case Study

**교육 Value Chain** (PwC 정의):
니즈 정의/분석 → 콘텐츠/과정설계 → 운영/실행 → 평가/성과관리 → 교육→배치 연계

**핵심 컨셉**:
- IBM = '스킬 기반 커리어 연계 개인화' — 스킬 데이터가 커리어 의사결정의 핵심 기준
- Microsoft = '업무 흐름 속 자연스러운 학습' — 교육을 일상 업무 환경에 내장 (Zero-touch)
- Novartis = '교육 → 프로젝트 연계 · 즉시 배치' — 교육을 실제 배치·성과로 연결
"""
from __future__ import annotations

from typing import TypedDict


# ═══════════════════════════════════════════════════════════════════
# 1) 사례별 핵심 정보
# ═══════════════════════════════════════════════════════════════════

class LearningCase(TypedDict):
    case_no: int
    title: str                     # 벤치마킹 사례 제목 (attribution prefix 원본)
    match_keywords: list[str]      # Task 이름 매칭 키워드
    applicable_l2: list[str]       # 두산 L2 매칭 (UI 표시 조건)
    companies: list[str]           # 해당 사례 적용 Player


# 교육 도메인 L2 매칭 — 두산 L2 '교육 기획', '교육 운영'
_L2_LEARN_PLANNING = ["교육 기획", "교육"]
_L2_LEARN_OPS      = ["교육 운영", "교육"]
_L2_LEARN_ALL      = ["교육 기획", "교육 운영", "교육"]


LEARNING_CASES: list[LearningCase] = [
    {
        "case_no": 1,
        "title": "스킬 자동 추론 + 맞춤 콘텐츠 추천 + Gap 산출",
        "match_keywords": [
            "스킬 추론", "스킬 자동 추론", "스킬 프로파일링",
            "스킬 Gap 산출", "스킬 Gap 분석", "맞춤 콘텐츠", "콘텐츠 추천",
            "People Skills", "니즈 분석", "니즈 정의", "교육 니즈",
        ],
        "applicable_l2": _L2_LEARN_PLANNING,
        "companies": ["IBM", "Microsoft"],
    },
    {
        "case_no": 2,
        "title": "스킬 수요 감소 선제 예측 + 리스킬링 연계",
        "match_keywords": [
            "스킬 수요", "수요 예측", "스킬 수요 예측", "교육 수요 예측",
            "리스킬링", "Reskilling", "reskilling", "At-risk", "at-risk",
            "선제 예측", "노동시장 트렌드", "직무코드",
        ],
        "applicable_l2": _L2_LEARN_PLANNING,
        "companies": ["Novartis"],
    },
    {
        "case_no": 3,
        "title": "개인별 맞춤 학습 콘텐츠·경로 자동 큐레이션",
        "match_keywords": [
            "학습 콘텐츠", "콘텐츠 큐레이션", "학습 경로", "커리큘럼",
            "학습 콘텐츠 맵핑", "콘텐츠 설계", "과정 설계", "커리큘럼 구성",
            "Tag Advisor", "학습 카탈로그", "맞춤 학습",
            "LinkedIn Learning", "linkedin learning", "Coursera", "coursera",
        ],
        "applicable_l2": _L2_LEARN_ALL,
        "companies": ["IBM", "Microsoft", "Novartis"],
    },
    {
        "case_no": 4,
        "title": "업무 Tool 내 로그인 없이 학습 (Zero-touch)",
        "match_keywords": [
            "Teams 학습", "Outlook 학습", "Viva Learning", "viva learning",
            "업무 Tool 학습", "Zero-touch", "zero-touch", "로그인 없이",
            "업무 흐름 학습", "업무 중 학습", "업무 내 학습", "학습 배포",
        ],
        "applicable_l2": _L2_LEARN_OPS,
        "companies": ["Microsoft"],
    },
    {
        "case_no": 5,
        "title": "AI 역할극 기반 실전 시뮬레이션 코칭",
        "match_keywords": [
            "시뮬레이션 코칭", "시뮬레이션 훈련", "역할극", "AI 역할극",
            "실전 시뮬레이션", "AI 코칭", "가상 고객", "Quantified",
            "실전 상황", "업무 시뮬레이션",
        ],
        "applicable_l2": _L2_LEARN_OPS,
        "companies": ["Novartis"],
    },
    {
        "case_no": 6,
        "title": "개인별 학습 로드맵 + 커리어 경로 AI 안내",
        "match_keywords": [
            "학습 로드맵", "학습로드맵", "커리어 경로", "커리어경로",
            "Your Learning", "your learning", "학습 안내", "멘토 추천",
            "커리어 안내", "로드맵 제공",
        ],
        "applicable_l2": _L2_LEARN_OPS,
        "companies": ["IBM"],
    },
    {
        "case_no": 7,
        "title": "스킬 숙련도 변화 추적 + 조직 대시보드",
        "match_keywords": [
            "스킬 숙련도", "숙련도 변화", "숙련도 추적", "학습 효과 측정",
            "교육 효과", "효과 측정", "Copilot Analytics", "copilot analytics",
            "학습 성과", "교육 성과", "평가 성과관리", "성과 측정",
            "스킬 Gap 현황", "교육 이수",
        ],
        "applicable_l2": _L2_LEARN_OPS,
        "companies": ["IBM", "Microsoft", "Novartis"],
    },
    {
        "case_no": 8,
        "title": "스킬 기반 내부 인력 매칭 + 프로젝트 즉시 배치",
        "match_keywords": [
            "내부 인력 매칭", "내부인력매칭", "프로젝트 매칭", "프로젝트 배치",
            "Blue Match", "blue match", "Match 플랫폼",
            "교육 배치", "배치 연계", "교육 배치 연계", "프로젝트 즉시 배치",
            "내부 공식", "이동 승진",
        ],
        "applicable_l2": _L2_LEARN_OPS,
        "companies": ["IBM", "Novartis"],
    },
    {
        "case_no": 9,
        "title": "업무 Tool 내 전문가 자동 검색·연결",
        "match_keywords": [
            "전문가 검색", "전문가 연결", "전문가 추천",
            "스킬 보유자", "사내 스킬", "AI 스킬 보유자",
            "프로파일 카드", "사내 전문가",
        ],
        "applicable_l2": _L2_LEARN_OPS,
        "companies": ["Microsoft"],
    },
]


# ═══════════════════════════════════════════════════════════════════
# 2) Player 프로파일 — IBM / Microsoft / Novartis
# ═══════════════════════════════════════════════════════════════════

class PlayerProfile(TypedDict):
    name: str
    theme: str
    focus: str
    key_points: list[str]
    core_solution: str
    ai_technology: list[str]
    source: str


LEARNING_PLAYERS: list[PlayerProfile] = [
    {
        "name": "IBM",
        "theme": "스킬 기반 커리어 연계 개인화",
        "focus": (
            "AI 가 추론한 스킬 프로파일을 기반으로 개인별 맞춤형 교육 추천부터 내부 배치까지 "
            "全 단계 초개인화. 스킬 데이터가 커리어 의사결정의 핵심 기준으로 작동"
        ),
        "key_points": [
            "22개+ 데이터 소스 (Jira 프로젝트, Workday 직무, 저작물·특허, 교육이력·배치) 결합 → 스킬 자동 추론",
            "Watson - Tag Advisor 기반 학습 콘텐츠 카탈로그 (80,000+ 학습 활동, 40+ 콘텐츠 소스 통합, 내부 제작 60% + 외부 교육 (Coursera·edX) 40%)",
            "Your Learning 플랫폼: 개인별 학습 로드맵 + 커리어 경로 멘토 추천 + 팀별 필수 과정 지정 (추천 알고리즘이 직원 반응 학습으로 지속 개선)",
            "Blue Match: 스킬 기반 내부 공식 매칭 (이동·승진 27%) → 인재 Pool 기반 배치 → 자발적 참여 방식",
            "MIT Sloan 공동 연구로 학습 ↔ 매출 성과 연계 효과 측정",
        ],
        "core_solution": "People Skills + IBM Skills Taxonomy + Watson - Tag Advisor + Your Learning + Blue Match",
        "ai_technology": [
            "NLP + ML 기반 스킬 추론", "추천 알고리즘 (직원 반응 학습)",
            "효과 측정 분석 엔진", "Blue Match 스킬 매칭",
        ],
        "source": (
            "MIT Sloan – The Learning System at IBM: A Case Study (Qin & Kochan, 2020); "
            "IBM – Watson Talent: Business Case for AI in HR; "
            "Josh Bersin – IBM in HR Marketplace (2020)"
        ),
    },
    {
        "name": "Microsoft",
        "theme": "업무 흐름 속 자연스러운 학습",
        "focus": (
            "교육 영역 內 AI 적용 영역은 IBM 과 유사하나, 교육의 全 과정이 업무 흐름 속에 "
            "자연스럽게 발생되는 구조로 System 연계가 되어 있다는 것이 차별점 "
            "(교육을 일상 업무 환경에 내장, 학습 접근성 극대화)"
        ),
        "key_points": [
            "Microsoft 그래프 데이터 (오피스 문서·이메일·채팅·회의) 에서 AI 가 스킬 자동 추론 (M365 Copilot/Viva 라이선스에 포함) — 유저 액션 불필요, 직원은 확인·편집만 수행 (Zero-touch)",
            "MS 스킬 체계 (Taxonomy) ↔ 학습 콘텐츠 카탈로그 매핑 (링크드인 Learning 16,000+ 과정 + 외부 LMS 연동 가능)",
            "Viva Learning (Teams 탭에 내장): 별도 로그인 없이 업무 중 학습 검색·수강, 동료가 콘텐츠 공유, Copilot 이 학습 경로 추천",
            "Copilot Analytics 대시보드: 조직 스킬 분포·Gap 시각화 + 팀별 스킬 변화 추적",
            "스킬 탐색 → 전문가 연결: 'AI 스킬 보유자 찾아줘' → 프로파일 확인 → 채팅·회의 후 연결",
        ],
        "core_solution": "Microsoft 그래프 데이터 + Viva Learning + Copilot Analytics + LinkedIn Learning",
        "ai_technology": [
            "스킬 자동 추론 (Zero-touch)", "Copilot 학습 추천",
            "조직 스킬 분포 분석", "AI 전문가 매칭",
        ],
        "source": (
            "MS Tech Community (2026.2); Microsoft Learn – People Skills Overview; "
            "Microsoft Inside Track – Viva Learning & LinkedIn Learning Hub Case (2024)"
        ),
    },
    {
        "name": "Novartis",
        "theme": "교육 → 프로젝트 연계 · 즉시 배치",
        "focus": (
            "스킬 수요 변화 선제 감지 및 신규 업무에 대한 시뮬레이션 훈련, 그리고 신규 프로젝트 "
            "대상 Skill 기반 인력 배치 등 교육의 전 영역에서 AI 도입. 교육을 실제 배치·성과로 "
            "연결하는 실행 중심 구조"
        ),
        "key_points": [
            "직무코드 (약 3.3만개) 통합 + 노동시장 트렌드 + 내부 직원 보유 스킬 + 사업 전략 방향 결합",
            "스킬 수요 예측: At-risk 직무·스킬 식별 → 전환 가능 스킬 매핑 → 선제적 리스킬링 기회 제공",
            "AI 업무 시뮬레이션 훈련: 실전 상황 (AI 가 가상 고객 역할 수행) → 구성원 대응 → AI 피드백",
            "Match 플랫폼: 스킬 ↔ 교육 ↔ 프로젝트 매칭 → 로테이션·프로젝트 매칭, 타 부서 파견·영구 이동",
            "교육 콘텐츠 소싱: Coursera 190개 대학 과정, LinkedIn Learning, 기타 디지털 리터러시 과정",
            "적용 규모: 130,000+ 직원 대상 Enabling Program 운영",
        ],
        "core_solution": "스킬 수요 예측 + AI 시뮬레이션 코칭 + Match 플랫폼",
        "ai_technology": [
            "ML 기반 스킬 수요 예측", "AI 역할 시뮬레이션 코칭 (Quantified)",
            "스킬-프로젝트 매칭", "노동시장 트렌드 분석",
        ],
        "source": (
            "Novartis – L&D Programs & Channels; "
            "René Gessenich (Novartis) – Digital HR Leaders Podcast (2022); "
            "Simon Brown (CLO, Novartis) – Enabling 130,000 Employees to Grow; "
            "Gloat – Novartis Case Study"
        ),
    },
]


# ═══════════════════════════════════════════════════════════════════
# 3) 통합 시사점
# ═══════════════════════════════════════════════════════════════════

INTEGRATED_INSIGHTS: dict[str, str] = {
    "headline": (
        "교육 AI 는 단순 추천 기능이 아니라, 스킬 데이터 기반으로 수요 예측 - 콘텐츠 설계 - "
        "업무 內 학습 - 효과 측정 - 배치 연계까지 全 과정을 연결하는 운영체계로 고도화 됨"
    ),
    "summary": (
        "스킬 DB 를 공통 언어로 교육 全 단계를 AI 가 연결하고, 업무 흐름 안에서 학습이 "
        "자연스럽게 이루어지는 구조 확립"
    ),
    "ai_process_principle": (
        "AI 가 추론한 스킬 프로파일이 니즈 분석 → 콘텐츠 설계 → 운영 → 평가 → 배치까지 "
        "全 단계를 하나의 데이터로 관통한다. 교육의 시작점이 '과정 카탈로그' 가 아닌 "
        "'개인별 스킬 Gap' 이 되며, Gap 분석 결과가 콘텐츠 추천·학습 경로·배치·코칭까지 "
        "자동으로 흘러가는 구조를 지향한다."
    ),
    "ai_application_principle": (
        "전사 공통 스킬 분류체계 (도메인 → 카테고리 → 개별 스킬) 정의가 AI 적용의 사전 조건 "
        "(추론·추천·매칭 시 필수). 단일 AI Agent 가 교육 value chain 의 각 단계를 개별적으로 "
        "지원하고 단계 간 산출물을 다음 단계로 연결. 통합 Skill DB 기반으로 단일 AI Agent 가 "
        "여러 value chain 을 관통하는 구조 有."
    ),
    "value_chain": (
        "교육 value chain: 니즈 정의/분석 → 콘텐츠/과정설계 → 운영/실행 → 평가/성과관리 → 교육→배치 연계"
    ),
}


# ═══════════════════════════════════════════════════════════════════
# 4) 벤치마킹 테이블 row 데이터
# ═══════════════════════════════════════════════════════════════════

_COMPANY_META: dict[str, dict[str, str]] = {
    "IBM": {
        "company_type": "Tech 선도",
        "industry": "IT 솔루션",
        "infrastructure": "People Skills + IBM Skills Taxonomy + Watson - Tag Advisor + Your Learning + Blue Match",
    },
    "Microsoft": {
        "company_type": "Tech 선도",
        "industry": "IT 솔루션",
        "infrastructure": "Microsoft 그래프 데이터 + Viva Learning + Copilot Analytics + LinkedIn Learning",
    },
    "Novartis": {
        "company_type": "非Tech 실제 구현",
        "industry": "글로벌 제약·헬스케어",
        "infrastructure": "스킬 수요 예측 시스템 + AI 시뮬레이션 코칭 (Quantified) + Match 플랫폼",
    },
}


_CASE_ROW_DETAILS: dict[tuple[int, str], dict[str, str]] = {
    (1, "IBM"): {
        "ai_adoption_goal": "수집된 데이터 기반 스킬 추론 (스킬 프로파일이 全 교육의 기반)",
        "ai_technology": "NLP + ML 기반 스킬 자동 추론 · 스킬 Gap 산출",
        "key_data": "22개+ 데이터 소스 (Jira 프로젝트, Workday 직무, 저작물·특허, 교육이력·배치)",
        "adoption_method": "People Skills 시스템 (스킬+숙련도 추론 → 커리어 트랙 Gap 산출)",
        "use_case": (
            "22개+ 데이터 소스를 결합하여 NLP+ML 기반으로 직원 스킬을 자동 추론. "
            "IBM Skills Taxonomy 와 매핑하여 개인별 스킬 Gap 자동 산출. "
            "스킬 자동 추론 결과가 全 교육 사이클의 기반"
        ),
        "outcome": "직원 개입 없이 데이터 기반 스킬 프로파일링 + 정량 Gap 산출",
        "implication": "**전사 공통 스킬 분류체계 (Taxonomy) 구축** 이 AI 추론·추천·매칭의 선행 조건",
    },
    (1, "Microsoft"): {
        "ai_adoption_goal": "업무 중 자연스럽게 니즈 감지 · 스킬 프로파일 자동 갱신 (Zero-touch)",
        "ai_technology": "Microsoft 그래프 데이터 분석 · 스킬 자동 추론",
        "key_data": "M365 (오피스 문서, 이메일 송수신, 채팅 메시지, 회의 참여자료)",
        "adoption_method": "M365 Copilot/Viva 라이선스 활용 (2026.2 포함)",
        "use_case": (
            "Microsoft 그래프 데이터 (M365 업무 활동) 에서 AI 가 직원 스킬을 자동 추론·프로파일링. "
            "M365 업무 활동이 스킬 프로파일을 상시 자동 갱신 (Zero-touch) — 유저 액션 불필요, "
            "직원이 확인·편집만 수행"
        ),
        "outcome": "Zero-touch 스킬 프로파일링 + 일상 업무 활동의 학습 신호 자동 포착",
        "implication": "**업무 Tool 통합 데이터 (M365 그래프 등)** 가 스킬 추론 정확도의 핵심",
    },
    (2, "Novartis"): {
        "ai_adoption_goal": "AI 기반 스킬 수요 예측 → At-risk 스킬 보유 직원 사전 식별 → 리스킬링 연계",
        "ai_technology": "ML 기반 스킬 수요 예측 · 노동시장 트렌드 분석",
        "key_data": "직무코드 (약 3.3만개) · 노동시장 트렌드 · 내부 직원 보유 스킬 · 사업 전략 방향",
        "adoption_method": "스킬 수요 예측 모델 (At-risk 식별 → 전환 가능 스킬 매핑 → 선제 리스킬링)",
        "use_case": (
            "외부 노동시장 데이터 (스킬 성장/감소 트렌드, 경쟁사 직무 벤치마크) + 내부 데이터 결합 → "
            "AI 기반 스킬 수요 예측. At-risk 직무·스킬 식별 → 전환 가능 스킬 매핑 → 선제적 리스킬링 기회 제공"
        ),
        "outcome": "시장 변화 사전 대응 + 인력 손실 사전 방지",
        "implication": "**노동시장 트렌드 + 내부 직무코드** 데이터 결합이 선제적 리스킬링의 전제",
    },
    (3, "IBM"): {
        "ai_adoption_goal": "스킬 체계와 학습 콘텐츠 맵핑 → 개인별 맞춤 콘텐츠 자동 큐레이션",
        "ai_technology": "Watson - Tag Advisor (NLP 기반 콘텐츠 태깅) · 추천 알고리즘",
        "key_data": "IBM Skills Taxonomy · 학습 콘텐츠 카탈로그 (80,000+ 학습 활동)",
        "adoption_method": "Watson - Tag Advisor 기반 콘텐츠 자동 태깅 + 카탈로그 통합",
        "use_case": (
            "IBM 스킬 체계 (Taxonomy) 와 학습 콘텐츠 카탈로그 매핑. Watson - Tag Advisor 가 "
            "80,000+ 학습 활동을 자동 분류·태깅 (40+ 콘텐츠 소스 통합, 내부 제작 60% + "
            "외부 교육 (Coursera·edX) 40%)"
        ),
        "outcome": "콘텐츠 분류 자동화 + 외부 콘텐츠 통합 → 개인별 정밀 추천 가능",
        "implication": "**대규모 학습 콘텐츠 라이브러리 + 자동 태깅 시스템** 이 정밀 추천의 기반",
    },
    (3, "Microsoft"): {
        "ai_adoption_goal": "스킬 체계와 학습 콘텐츠 맵핑 → MS 업무 툴 내 학습 연계",
        "ai_technology": "Copilot 추천 알고리즘 · 스킬 매핑",
        "key_data": "MS 스킬 체계 (Taxonomy) · LinkedIn Learning 16,000+ 과정 · 외부 LMS",
        "adoption_method": "Viva Learning + LinkedIn Learning 카탈로그 통합",
        "use_case": (
            "MS 스킬 체계와 학습 콘텐츠 카탈로그 매핑 (LinkedIn Learning 16,000+ 과정 + "
            "외부 LMS 연동 가능). Copilot 이 추천 알고리즘 운영"
        ),
        "outcome": "외부 (LinkedIn) 와 내부 콘텐츠 통합 + Copilot 기반 자동 추천",
        "implication": "**LinkedIn Learning 같은 외부 LMS 연동** 으로 콘텐츠 다양성 확보",
    },
    (3, "Novartis"): {
        "ai_adoption_goal": "스킬 기반 교육 콘텐츠 설계 (At-risk 스킬 보유 직원 맞춤)",
        "ai_technology": "AI 시뮬레이션 + 외부 콘텐츠 큐레이션",
        "key_data": "스킬 수요 예측 결과 · 외부 학습 콘텐츠 (Coursera, LinkedIn Learning)",
        "adoption_method": "리스킬링 과정 설계 (At-risk 스킬 보유 직원 맞춤 교육 과정 구성)",
        "use_case": (
            "At-risk 스킬 보유 직원에게 필요한 교육 과정 구성. 교육 콘텐츠 소싱: Coursera "
            "190개 대학 과정 + LinkedIn Learning + 기타 디지털 리터러시 과정. 투입 프로젝트 "
            "맞춤 설계 (190개 대학 큐레이션 + AI 시뮬레이션)"
        ),
        "outcome": "리스킬링 대상별 맞춤 교육 과정 자동 설계",
        "implication": "**리스킬링 과정 설계** 는 외부 학습 플랫폼과의 큐레이션 연계가 효율적",
    },
    (4, "Microsoft"): {
        "ai_adoption_goal": "업무 중 바로 수강 가능토록 MS 업무 툴 내 학습 연계 (Zero-touch)",
        "ai_technology": "Viva Learning Teams 통합 · Copilot 학습 추천",
        "key_data": "M365 업무 활동 컨텍스트 · 학습 콘텐츠 카탈로그",
        "adoption_method": "Viva Learning (Teams 탭에 내장)",
        "use_case": (
            "Viva Learning 이 Teams 탭에 내장되어 별도 로그인 없이 업무 중 학습 가능. "
            "Teams 에서 학습 검색·수강 + 동료가 콘텐츠 공유 + Copilot 이 학습 경로 추천"
        ),
        "outcome": "학습 접근성 극대화 + 별도 LMS 로그인 마찰 제거",
        "implication": "**업무 Tool (Teams/Outlook) 내 학습 내장** 이 학습 접근성·실행률의 결정 요인",
    },
    (5, "Novartis"): {
        "ai_adoption_goal": "교육 과정의 일환으로 AI 기반 신규 업무 시뮬레이션 진행",
        "ai_technology": "AI 역할 시뮬레이션 코칭 (Quantified)",
        "key_data": "실전 상황 시나리오 · 가상 고객 역할 데이터",
        "adoption_method": "Quantified 솔루션 활용 (영업 상황 AI 시뮬레이션 + 개인화 피드백·코칭)",
        "use_case": (
            "AI 역할 시뮬레이션 코칭. 실전 상황 시뮬레이션 흐름: 실전 상황 제시 "
            "(AI 가 가상 고객 역할 수행) → 구성원 대응 → AI 피드백"
        ),
        "outcome": "실전 역량 강화 + 1:1 개인화 피드백 자동화",
        "implication": "**역할극·시뮬레이션 기반 학습** 은 단순 콘텐츠 시청 대비 학습 효과·전이성 우수",
    },
    (6, "IBM"): {
        "ai_adoption_goal": "개인별 맞춤형 학습·커리어 경로 연계 (Your Learning 플랫폼)",
        "ai_technology": "Your Learning 추천 알고리즘 (학습 콘텐츠 추천 → 직원 반응 학습 → 추천 개선)",
        "key_data": "개인 스킬 프로파일 · 학습 콘텐츠 카탈로그 · 커리어 트랙 데이터",
        "adoption_method": "Your Learning 플랫폼 (학습 로드맵 + 커리어 경로 멘토 추천 + 팀별 필수 과정)",
        "use_case": (
            "Your Learning 플랫폼에서 개인별 학습 로드맵 생성, 커리어 경로 멘토 추천, 팀별 필수 "
            "과정 지정. 추천 알고리즘이 직원 반응을 학습하여 지속 개선"
        ),
        "outcome": "개인별 정밀 학습 로드맵 + 커리어 의사결정 지원",
        "implication": "**추천 알고리즘의 지속 학습 (직원 반응 피드백 루프)** 이 추천 정밀도의 핵심",
    },
    (7, "IBM"): {
        "ai_adoption_goal": "Skill 기반 교육 이후 해당 인력의 성과 측정",
        "ai_technology": "효과 측정 분석 엔진 (MIT Sloan 공동 연구)",
        "key_data": "교육 전후 스킬 숙련도 · 학습 이력 · 매출 성과 데이터",
        "adoption_method": "효과 측정 분석 엔진",
        "use_case": (
            "교육 전후 Skill 숙련도 변화 추적, 학습 ↔ 매출 성과 연계 효과 측정 (MIT Sloan 공동 연구)"
        ),
        "outcome": "교육 ROI 정량 측정 + 학습-성과 연계 데이터화",
        "implication": "**학습-성과 연계 측정** 은 학회 공동 연구 같은 객관성 확보 장치 필요",
    },
    (7, "Microsoft"): {
        "ai_adoption_goal": "Skill 기반 교육 이후 해당 인력의 성과 측정 + 조직 차원 가시화",
        "ai_technology": "Copilot Analytics 대시보드",
        "key_data": "조직 스킬 분포 · Gap 데이터 · 팀별 스킬 변화",
        "adoption_method": "Copilot Analytics 대시보드",
        "use_case": (
            "Copilot Analytics 대시보드로 조직 스킬 현황 조회. 조직 스킬 분포·Gap 시각화 + "
            "팀별 스킬 변화 추적"
        ),
        "outcome": "조직 차원 스킬 거버넌스 가능 + 팀별 변화 가시화",
        "implication": "**조직 스킬 대시보드** 가 Skill 거버넌스의 의사결정 인터페이스",
    },
    (7, "Novartis"): {
        "ai_adoption_goal": "프로젝트 투입 성공률 기반 측정 (학습시간 + 스킬 갭 해소율 + 프로젝트 투입 성공률)",
        "ai_technology": "스킬 Gap 현황 분석 · 학습 참여 지표 모니터링",
        "key_data": "스킬 갭 해소 현황 · 직무 클러스터별 역량 · 학습 참여 지표",
        "adoption_method": "스킬 Gap 현황 분석",
        "use_case": (
            "스킬 갭 해소 현황 추적 + 직무 클러스터별 역량 분석 + 학습 참여 지표 모니터링"
        ),
        "outcome": "교육 효과를 비즈니스 산출물 (프로젝트 투입 성공률) 로 직접 측정",
        "implication": "**교육 효과를 사업 성과 (프로젝트 성공률) 로 측정** 하는 KPI 구조 필요",
    },
    (8, "IBM"): {
        "ai_adoption_goal": "Blue Match 시스템 기반 스킬 및 교육을 고려한 배치",
        "ai_technology": "Blue Match (스킬 기반 내부 공식 매칭)",
        "key_data": "직원 스킬 프로파일 · 내부 포지션 · 평가/채용 시스템 데이터",
        "adoption_method": "Blue Match + HR 시스템 연동 (채용·평가)",
        "use_case": (
            "Blue Match 시스템: 스킬 기반 ↔ 내부 공식 매칭 (이동·승진 27%) → 인재 Pool 기반 "
            "배치 → 내부 공식 매칭·추천 → 직원 자발적 참여 방식. HR 시스템 (채용·평가) 와 연동"
        ),
        "outcome": "내부 이동·승진의 27% 가 Blue Match 매칭으로 발생 + 자발적 참여 문화",
        "implication": "**자발적 참여 (Self-service) 매칭** 모델이 외부 채용 비용 절감과 직원 만족 동시 달성",
    },
    (8, "Novartis"): {
        "ai_adoption_goal": "교육 완료 인력을 프로젝트에 즉시 배치",
        "ai_technology": "Match 플랫폼 (스킬 ↔ 교육 ↔ 프로젝트 매칭)",
        "key_data": "스킬 데이터 · 교육 이수 데이터 · 프로젝트 요구 스킬",
        "adoption_method": "Match 플랫폼",
        "use_case": (
            "Match 플랫폼이 스킬 ↔ 교육 ↔ 프로젝트 매칭. 로테이션·프로젝트 매칭 + 타 부서 "
            "파견·영구 이동. 교육 ↔ 프로젝트 배치 1:1 즉시 매칭"
        ),
        "outcome": "교육-배치 사이의 시간 격차 제거 + 인력 활용도 극대화",
        "implication": "**교육-배치 1:1 즉시 연결** 이 교육 투자의 ROI 정점",
    },
    (9, "Microsoft"): {
        "ai_adoption_goal": "AI 기반 사내 스킬 보유자 추천 (전문가 매칭)",
        "ai_technology": "스킬 기반 전문가 추천 · AI 매칭",
        "key_data": "프로파일 카드 (직원 스킬·이력) · 업무 Tool 내 활동 데이터",
        "adoption_method": "스킬 탐색 → 전문가 연결 (Teams 통합)",
        "use_case": (
            "'AI 스킬 보유자 찾아줘' → 스킬 기반 전문가 추천 → 프로파일 확인 → 채팅·회의 후 연결. "
            "업무 Tool 내 전문가 검색·연결 (별도 시스템 불필요)"
        ),
        "outcome": "사내 전문가 발굴·활용 자동화 + 협업 마찰 제거",
        "implication": "**프로파일 카드 + 업무 Tool 통합** 이 사내 전문가 활용도의 결정 요인",
    },
}


# ═══════════════════════════════════════════════════════════════════
# 5) Helpers — recruit/evaluation/compensation 과 동일 시그니처
# ═══════════════════════════════════════════════════════════════════

def build_background_benchmark_rows(filter_l2: list[str] | None = None) -> list[dict]:
    """Background BM row 리스트 (BenchmarkTableRow 형식 + is_background=True)."""
    filter_set = {str(n).strip() for n in filter_l2} if filter_l2 else None
    rows: list[dict] = []
    for case in LEARNING_CASES:
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
                "benchmark_domain": "learning",
            })
    return rows


def get_background_cases_for_tasks(tasks) -> list[LearningCase]:
    if not tasks:
        return []
    l2_names = {getattr(t, "l2", "") or "" for t in tasks}
    l2_set = {n for n in l2_names if n}
    if not l2_set:
        return []
    return [c for c in LEARNING_CASES if any(l2 in l2_set for l2 in c["applicable_l2"])]


def get_background_cases_by_l2(l2_names: list[str]) -> list[LearningCase]:
    if not l2_names:
        return []
    l2_set = {str(n).strip() for n in l2_names if n}
    return [c for c in LEARNING_CASES if any(l2 in l2_set for l2 in c["applicable_l2"])]


def match_benchmark_for_task(task_name: str) -> LearningCase | None:
    if not task_name:
        return None
    tn = task_name.lower()
    for case in LEARNING_CASES:
        for kw in case["match_keywords"]:
            if kw.lower() in tn:
                return case
    return None


def attribute_task_name(task_name: str) -> tuple[str, str | None]:
    if not task_name:
        return task_name or "", None
    case = match_benchmark_for_task(task_name)
    if not case:
        return task_name, None
    return f"{case['title']} - {task_name}", case["title"]


def format_players_for_prompt(players: list[PlayerProfile]) -> str:
    if not players:
        return ""
    lines = ["## 🏛 Background BM — Player 개요 (Doosan HR 큐레이션 · 교육 도메인)"]
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
        "## 💡 Background BM — 통합 시사점 (교육 도메인)\n"
        f"**Headline**: {ii['headline']}\n\n"
        f"**핵심 Summary**: {ii['summary']}\n\n"
        f"**AI 기반 프로세스 원칙**: {ii['ai_process_principle']}\n\n"
        f"**AI 적용 방식 원칙**: {ii['ai_application_principle']}\n\n"
        f"**Value Chain**: {ii['value_chain']}\n"
    )


def get_applicable_players_for_tasks(tasks) -> list[PlayerProfile]:
    """교육 도메인 L2 가 매칭되면 3 사 프로필 전체 반환, 아니면 빈 리스트."""
    applicable_cases = get_background_cases_for_tasks(tasks)
    if not applicable_cases:
        return []
    return list(LEARNING_PLAYERS)
