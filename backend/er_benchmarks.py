"""
ER (Employee Relations · 노사 관계) 선도사 AI 적용 사례 — Background BM (PwC 큐레이션).

Doosan HR L2 '집단노사' · '준법지원' 프로세스에 자동 주입되는 기본 벤치마킹 데이터.

**동작 원칙** (다른 도메인 모듈과 동일 패턴):
- 엑셀 L2 매칭 시 _wf_benchmark_table['__background__'] 에 자동 주입 (is_background=True)
- Step 1 기본 설계 프롬프트에 모두 포함됨 → Perplexity 검색 없이도 Step 1 정상 실행
- UI 에서 파란색으로 하이라이트
- Task 이름 attribution 에도 동일 매칭 키워드 사용

**데이터 소스** (PwC Analysis 슬라이드 원문 기반):
- Sodales Solutions – AI for Employee & Labor Relations
- Sodales – PSE (Puget Sound Energy) Customer Case Study
- Sodales – Spire Energy Customer Case Study (SAP Success Connect 2019)
- HR Acuity – Waymo Customer Story
- HR Acuity – AI & Compliance Guide for ER Teams
- olivER AI Companion
- HR Executive – Hitachi AI HR Companion "Skye" Case (2025)

**ER Value Chain** (PwC 정의):
이슈 식별 및 접수 → 사실관계 확인 및 기준 검토 → 대응 및 협의 실행 → 후속 조치 및 리스크 관리

**핵심 컨셉**:
- 집단노사 영역 (PSE/Spire/City of Saskatoon) = '신속한 노사 이슈 대응을 위한 준비/지원'
  → 인간의 대면 협상 및 최종 의사결정을 전제로, AI 가 이슈 탐지와 교섭 준비를 주도
- 준법지원 영역 (Waymo/Yelp/Hitachi/Pilot) = '이슈 대응의 체계화와 일관된 처리 기준 확립'
  → 최신 법령·사규 적용의 정확성과 일관성을 높이는 방향
- 통합 시사점: AI 가 데이터·프로세스 흐름을 연결하되, 협상·대응·의사결정 등 핵심 Action 은 사람이 수행
"""
from __future__ import annotations

from typing import TypedDict


# ═══════════════════════════════════════════════════════════════════
# 1) 사례별 핵심 정보
# ═══════════════════════════════════════════════════════════════════

class ERCase(TypedDict):
    case_no: int
    title: str
    match_keywords: list[str]
    applicable_l2: list[str]
    companies: list[str]


# ER L2 매칭 — 두산 L2 '집단노사', '준법지원' + ER 통합 후보
_L2_LABOR_RELATIONS = ["집단노사", "ER", "Employee Relations", "노사관계"]
_L2_COMPLIANCE      = ["준법지원", "ER", "Compliance", "준법"]


ER_CASES: list[ERCase] = [
    {
        "case_no": 1,
        "title": "노사 이슈 상시 모니터링 및 잠재 이슈 탐지",
        "match_keywords": [
            "노사 이슈", "노사이슈", "이슈 모니터링", "잠재 이슈", "잠재이슈",
            "이슈 탐지", "이슈탐지", "상시 모니터링", "조기 탐지", "조기탐지",
            "이상 패턴", "이상 징후", "ER 모니터링",
        ],
        "applicable_l2": _L2_LABOR_RELATIONS,
        "companies": ["PSE", "Spire"],
    },
    {
        "case_no": 2,
        "title": "분쟁 대응을 위한 사실관계 정리 및 조사 지원",
        "match_keywords": [
            "사실관계", "사실 관계", "분쟁 대응", "조사 지원", "조사지원",
            "사건 정보 요약", "조사 체크리스트", "사실관계 정리", "사건 조사",
            "교섭 요구", "노사 사실관계",
        ],
        "applicable_l2": _L2_LABOR_RELATIONS,
        "companies": ["PSE", "Spire"],
    },
    {
        "case_no": 3,
        "title": "분쟁 대응 전략 수립 지원",
        "match_keywords": [
            "대응 전략", "대응전략", "교섭 전략", "교섭전략",
            "협상 준비", "협상준비", "분쟁 대응 전략",
            "유사 선례", "옵션 분석", "교섭 아이디어",
        ],
        "applicable_l2": _L2_LABOR_RELATIONS,
        "companies": ["PSE", "City of Saskatoon"],
    },
    {
        "case_no": 4,
        "title": "사내 고충 접수 내용 자동 분류",
        "match_keywords": [
            "고충 접수", "고충접수", "고충 처리", "고충 분류",
            "신고 접수", "신고접수", "신고 분류", "이슈 분류",
            "초기 triage", "triage", "이슈 유형", "이슈 그룹",
            "위장 도급", "불법 파견", "사용자성",
        ],
        "applicable_l2": _L2_COMPLIANCE,
        "companies": ["Waymo", "Yelp"],
    },
    {
        "case_no": 5,
        "title": "AI Compliance Assistant 챗봇",
        "match_keywords": [
            "Compliance Assistant", "compliance assistant", "준법 챗봇",
            "Compliance 챗봇", "준법 Assistant", "규정 검색", "규정 검토",
            "법령 검토", "사규 검토", "법령 적용", "사규 적용",
            "olivER", "oliver", "Skye", "skye", "법률 쟁점",
        ],
        "applicable_l2": _L2_COMPLIANCE,
        "companies": ["Hitachi", "Pilot"],
    },
    {
        "case_no": 6,
        "title": "사건 처리 내역 자동 문서화",
        "match_keywords": [
            "처리 내역", "처리내역", "내역 문서화", "내역문서화",
            "사건 보고서", "보고서 생성", "Resolution Note", "resolution note",
            "사건 처리", "조치 이력", "조치이력", "처리 결과 문서",
            "조사 결과 문서", "통합 리포트",
        ],
        "applicable_l2": _L2_COMPLIANCE,
        "companies": ["Anonymous Company"],
    },
    {
        "case_no": 7,
        "title": "시스템 기반 후속 운영 자동화",
        "match_keywords": [
            "후속 운영 자동화", "후속운영자동화", "단체협약 자동화", "단협 자동화",
            "노조규칙", "단체협약", "단협", "Rule Engine", "rule engine",
            "시스템 Rule", "시스템 룰", "후속 절차 자동",
            "협약 적용", "내부 연동",
        ],
        "applicable_l2": _L2_LABOR_RELATIONS,
        "companies": ["PSE"],
    },
]


# ═══════════════════════════════════════════════════════════════════
# 2) Player 프로파일 — 집단노사 / 준법지원
# ═══════════════════════════════════════════════════════════════════

class PlayerProfile(TypedDict):
    name: str
    theme: str
    focus: str
    key_points: list[str]
    core_solution: str
    ai_technology: list[str]
    source: str


ER_PLAYERS: list[PlayerProfile] = [
    {
        "name": "집단노사 (PSE · Spire · City of Saskatoon)",
        "theme": "신속한 노사 이슈 대응을 위한 준비/지원",
        "focus": (
            "인간의 대면 협상 및 최종 의사결정을 전제로, AI 가 이슈 탐지와 교섭 준비를 주도하고 "
            "시스템 기반 자동화 기술이 후속 운영을 뒷받침하는 구조로 발전 중"
        ),
        "key_points": [
            "사전 예방 구간: 노사 이슈 상시 모니터링 및 잠재 이슈 탐지 (신호 통합 분석 → 이상 징후 식별 → 잠재 이슈 탐지·경고 Alert)",
            "사후 대응 구간: 노사 이슈 발생 시 AI 가 사건을 구조화·분석하여 담당자의 신속 대처 지원 (사실 관계 정리 + 조사 지원 + 후속 Action 추천)",
            "대응 준비 지원: 조사 결과 요약·유사 선례·옵션별 참고자료를 활용한 교섭 전략 수립 아이디어 제시 (협상 진행은 Human 수행)",
            "후속 조치 구간: ER 담당자가 협상 결과를 ER 시스템에 반영하면 관련 데이터가 최신으로 자동 업데이트됨 — 타결된 협약·규칙을 시스템 Rule 로 입력 → 인사정보·근태/급여 시스템 등 내부 연동 시스템 일괄 자동 반영",
        ],
        "core_solution": "Sodales Solutions (AI for Employee & Labor Relations)",
        "ai_technology": [
            "ML 기반 이상 패턴 감지", "신호 통합 분석",
            "문서 Parsing · 텍스트 추출", "다양한 문서 내 Text 인식·분석",
            "유사 선례 검색", "시스템 Rule Engine · API 연동",
        ],
        "source": (
            "Sodales Solutions – AI for Employee & Labor Relations; "
            "Sodales – PSE Customer Case Study; "
            "Sodales – Spire Energy Customer Case Study (SAP Success Connect 2019)"
        ),
    },
    {
        "name": "준법지원 (Waymo · Yelp · Hitachi · Pilot)",
        "theme": "이슈 대응의 체계화와 일관된 처리 기준 확립",
        "focus": (
            "AI 를 기반으로 최신 법령·사규 적용의 정확성과 일관성을 높이고, 이슈 대응의 체계화와 "
            "일관된 처리 기준 확보를 통해 준법 리스크 예방을 지원"
        ),
        "key_points": [
            "고충 접수 내용 자동 분류: 과거 고충·신고·조사 이력 데이터 기반으로 신규 이슈 자동 분류 및 일관된 대응 전략 수립 지원 (신고 내용 구조화 → 핵심 내용 분석 → 이슈 유형 분류)",
            "Compliance Assistant 챗봇: 사내 정책 및 규정 문서 기반 정보 검색 및 요약 + 규정 관련 사용자 문의 자동 응대 (질문 의도 해석 + 법률 쟁점 매핑 + 관련 규정 검색 + 조사 항목 생성)",
            "처리 내역 자동 문서화: ER 담당자의 현장 조사 데이터를 기반으로 AI 가 결과 보고서를 자동 생성 (사건 조사 보고서·노무자문 결과·회의록·징계내역 → 사건개요·처리이력·최종 집행내역 수록)",
            "준법지원 통합 DB 활용: 최신 법령, 관련 정책, 사내 규정 등 ER 유관 데이터를 통합 적재하여 준법 리스크를 상시 점검 (구조적 노무 리스크 여부 확장 점검)",
        ],
        "core_solution": "HR Acuity + olivER AI Companion + Hitachi AI HR Companion 'Skye'",
        "ai_technology": [
            "텍스트 자동 분류", "키워드 감지·식별", "유사도 분석",
            "LLM + RAG 기반 규정 검색", "사건 자동 문서화 (LLM)",
            "통합 DB · API/웹 수집/DB 연동",
        ],
        "source": (
            "HR Acuity – Waymo Customer Story; "
            "HR Acuity – AI & Compliance Guide for ER Teams; "
            "olivER AI Companion; "
            "HR Executive – Hitachi AI HR Companion 'Skye' Case (2025)"
        ),
    },
]


# ═══════════════════════════════════════════════════════════════════
# 3) 통합 시사점
# ═══════════════════════════════════════════════════════════════════

INTEGRATED_INSIGHTS: dict[str, str] = {
    "headline": (
        "ER 은 섬세한 판단과 관계 관리가 중요한 영역으로, AI 를 통해 ER 업무의 전 단계를 "
        "유기적으로 연결하되 핵심 판단과 협의는 사람이 수행하도록 설계되어야 함"
    ),
    "summary": (
        "AI 가 데이터와 프로세스 흐름을 연결하되, 협상·대응·의사결정 등 핵심 Action 은 "
        "사람이 수행 (AI Agent 의 전 단계 유기적 연계와 통합 DB 기반 데이터 순환을 통해 "
        "ER 이슈 대응의 일관성과 정합성 확보)"
    ),
    "ai_process_principle": (
        "이슈 식별부터 후속 관리까지 전 단계가 끊김 없이 연결되는 업무 흐름 설계 필요. "
        "사전 예방 → 사후 대응 → 후속 관리로 이어지는 단계별 AI 개입 시나리오 정의. "
        "각 단계의 처리 결과가 다음 단계의 입력값으로 자연스럽게 연결되는 유기적 프로세스 구조 설계."
    ),
    "ai_application_principle": (
        "단계별 데이터가 분절되지 않고 하나의 흐름으로 축적·연계되는 통합 아키텍처 설계 필요. "
        "고충·노사·준법 사건 이력, 법령, 사규 등의 원천 데이터를 프로세스 전반에서 재활용 "
        "가능한 구조 형태로 누적. 인사·근태·급여 등 연관 시스템과의 연동으로 이슈 발생 시 "
        "관련 데이터가 자동 취합되는 체계 확보."
    ),
    "value_chain": (
        "ER value chain: 이슈 식별 및 접수 → 사실관계 확인 및 기준 검토 → 대응 및 협의 실행 → 후속 조치 및 리스크 관리"
    ),
}


# ═══════════════════════════════════════════════════════════════════
# 4) 벤치마킹 테이블 row 데이터
# ═══════════════════════════════════════════════════════════════════

_COMPANY_META: dict[str, dict[str, str]] = {
    "PSE": {
        "company_type": "非Tech 실제 구현",
        "industry": "에너지·유틸리티 (Puget Sound Energy)",
        "infrastructure": "Sodales Solutions (AI for Employee & Labor Relations)",
    },
    "Spire": {
        "company_type": "非Tech 실제 구현",
        "industry": "에너지·유틸리티 (Spire Energy)",
        "infrastructure": "Sodales Solutions (AI for Employee & Labor Relations)",
    },
    "City of Saskatoon": {
        "company_type": "非Tech 실제 구현",
        "industry": "공공기관·도시정부",
        "infrastructure": "Sodales Solutions (AI for Employee & Labor Relations)",
    },
    "Waymo": {
        "company_type": "Tech 선도",
        "industry": "자율주행·AI",
        "infrastructure": "HR Acuity (ER Case Management)",
    },
    "Yelp": {
        "company_type": "Tech 선도",
        "industry": "IT 서비스",
        "infrastructure": "HR Acuity (ER Case Management)",
    },
    "Hitachi": {
        "company_type": "非Tech 실제 구현",
        "industry": "산업기술 제조 (Hitachi)",
        "infrastructure": "Hitachi AI HR Companion 'Skye'",
    },
    "Pilot": {
        "company_type": "非Tech 실제 구현",
        "industry": "운송·물류 (Pilot)",
        "infrastructure": "olivER AI Companion + Compliance Tools",
    },
    "Anonymous Company": {
        "company_type": "非Tech 실제 구현",
        "industry": "익명 (Resolution Note 자동화 사례)",
        "infrastructure": "사건 자동 문서화 시스템 (Resolution Note 자동 생성)",
    },
}


_CASE_ROW_DETAILS: dict[tuple[int, str], dict[str, str]] = {
    # ── Case 1: 노사 이슈 상시 모니터링 및 잠재 이슈 탐지 (PSE, Spire) ──
    (1, "PSE"): {
        "ai_adoption_goal": "노사 이슈 조기 탐지 및 잠재 리스크 사전 식별",
        "ai_technology": "Sodales Solutions · ML 기반 이상 패턴 감지 · 신호 통합 분석",
        "key_data": "고충·불만 / 징계 이력 / 안전 사고 / 감사 결과 / 교육 이수현황",
        "adoption_method": "Sodales 기반 ER 유관 데이터 자동 모니터링",
        "use_case": (
            "신호 통합 분석 (ER 유관 다중 데이터) → 이상 징후 식별 (학습 반영: 과거 이슈 내역, "
            "타사 사례 기반 머신러닝 이상 패턴 감지) → 잠재 이슈 탐지 및 경고 Alert 발송 "
            "(불만 접수 누적, 집단 행동 발생 가능성 높음 등 자동 감지)"
        ),
        "outcome": "사전 예방 구간 확보 + 잠재 리스크 조기 식별 + ER 담당자 의사결정 지원",
        "implication": "**ER 유관 다중 데이터 통합 + ML 기반 이상 패턴 감지** 가 잠재 이슈 탐지 정확도의 핵심",
    },
    (1, "Spire"): {
        "ai_adoption_goal": "노사 이슈 조기 탐지 (Spire Energy 사례)",
        "ai_technology": "Sodales Solutions · ML 기반 이상 패턴 감지",
        "key_data": "고충·불만 / 징계 이력 / 안전 사고 / 감사 결과",
        "adoption_method": "Sodales 기반 ER 운영 데이터 상시 모니터링",
        "use_case": (
            "Spire Energy 가 Sodales 기반으로 노사 이슈 상시 모니터링 체계 운영 — 사전 예방 "
            "구간에 AI 모니터링을 도입하여 잠재 이슈를 조기에 탐지·대응"
        ),
        "outcome": "에너지·유틸리티 산업의 노사 안정성 확보 + 사전 대응력 향상",
        "implication": "**전통 산업군 (유틸리티) 의 AI 기반 노사 모니터링** 도 도입 가능성 입증",
    },
    # ── Case 2: 분쟁 대응을 위한 사실관계 정리 및 조사 지원 (PSE, Spire) ──
    (2, "PSE"): {
        "ai_adoption_goal": "노사 이슈 발생 시 사건 구조화·분석으로 담당자 신속 대처 지원",
        "ai_technology": "Sodales · 문서 Parsing · NLP 기반 다양한 문서 내 Text 인식·분석",
        "key_data": "교섭 요구 원문 · 사내 규정 · 유관 법령 · 관련 기사",
        "adoption_method": "Sodales 기반 사실관계 자동 정리 + 후속 Action 추천",
        "use_case": (
            "사실 관계 정리 (교섭 요구 원문·사내 규정·유관 법령·관련 기사 수집 → 문서 Parsing, "
            "텍스트 추출 → 다양한 문서 내 Text 인식 및 분석) / 조사 지원 (사건 정보 요약, 적용 "
            "규정 정리, 조사 체크리스트 → 조사자를 위한 후속 Action 추천)"
        ),
        "outcome": "사후 대응 신속화 + 조사 정합성 강화 + 담당자 부담 감소",
        "implication": "**다양한 형태 문서 (원문/규정/법령/기사) 통합 처리** 가 조사 효율의 결정 요인",
    },
    (2, "Spire"): {
        "ai_adoption_goal": "Spire Energy 의 노사 이슈 사실관계 정리 및 조사 지원",
        "ai_technology": "Sodales · NLP 기반 문서 분석",
        "key_data": "사내 규정 · 유관 법령 · 사건 관련 정보",
        "adoption_method": "Sodales 기반 사실관계 자동 취합",
        "use_case": (
            "Spire Energy 가 Sodales 솔루션으로 노사 이슈 발생 시 사건 관련 정보 자동 취합, "
            "단계별 시행 전략 구조화 — 담당자가 신속 대처할 수 있도록 사건 정보 요약·적용 규정 "
            "정리 자동화"
        ),
        "outcome": "사건 처리 리드타임 단축 + 후속 Action 명확화",
        "implication": "**Sodales 기반 자동 취합·구조화** 로 노사 이슈 처리의 표준화 가능",
    },
    # ── Case 3: 분쟁 대응 전략 수립 지원 (PSE, City of Saskatoon) ──
    (3, "PSE"): {
        "ai_adoption_goal": "교섭 전략 수립 아이디어 제시 + 교섭/협의 데이터 체계화",
        "ai_technology": "Sodales · 유사 선례 검색 · 옵션 분석",
        "key_data": "조사 결과 · 유사 선례 · 옵션별 참고자료",
        "adoption_method": "교섭 전략 수립 지원 (조사 결과 요약 + 유사 선례 + 옵션별 참고자료)",
        "use_case": (
            "조사 결과 요약, 유사 선례 제시, 옵션별 참고자료 → 교섭 전략 수립 아이디어 제시. "
            "협상 진행은 Human 수행 (AI 는 준비 단계까지만 지원)"
        ),
        "outcome": "협상 준비도 향상 + 일관된 교섭 전략 수립",
        "implication": "**유사 선례 DB 구축** 이 협상 일관성의 기반 (교섭/협의 데이터 체계화)",
    },
    (3, "City of Saskatoon"): {
        "ai_adoption_goal": "공공기관의 노사 협상 전략 수립 지원",
        "ai_technology": "Sodales · 선례 분석",
        "key_data": "공공기관 노사 교섭 이력 · 선례 데이터",
        "adoption_method": "Sodales 기반 협상 준비 지원",
        "use_case": (
            "City of Saskatoon (캐나다 공공기관) 이 Sodales 솔루션으로 노사 협상 시 유사 선례 "
            "분석과 옵션별 참고자료 자동 정리 — 공공 부문 노사 협상의 일관성 확보"
        ),
        "outcome": "공공 부문 노사 협상의 정합성·일관성 확보",
        "implication": "**공공 부문 노사 AI 도입** 으로 정책 일관성과 시민 신뢰 확보 가능",
    },
    # ── Case 4: 사내 고충 접수 내용 자동 분류 (Waymo, Yelp) ──
    (4, "Waymo"): {
        "ai_adoption_goal": "과거 고충/신고/조사 이력 데이터 기반 신규 이슈 자동 분류 및 일관된 대응 전략 수립 지원",
        "ai_technology": "HR Acuity · 텍스트 자동 분류 · 키워드 감지/식별 · 유사도 분석",
        "key_data": "과거 고충/신고/조사 이력 · 신고 내용 원문",
        "adoption_method": "HR Acuity 기반 자동 분류 + 사건 단위 정보 구조 전환",
        "use_case": (
            "신고 내용 구조화 (장소·주체·대상·행위 → 사건 단위 정보 텍스트 구조 전환) → "
            "핵심 내용 분석 (직접 지휘·명령, 근태 개입, 휴가 승인 개입 등 → 키워드 감지/식별, "
            "주요 쟁점 도출) → 이슈 유형 분류 (위장 도급, 불법 파견, 사용자성 이슈 등 → 유사도 "
            "분석 적용, 이슈 그룹 매핑)"
        ),
        "outcome": "초기 triage 자동화 + 일관된 분류 기준 + 담당자 부담 감소",
        "implication": "**과거 사건 이력 DB** 가 신규 이슈 자동 분류 정확도의 핵심",
    },
    (4, "Yelp"): {
        "ai_adoption_goal": "Yelp 의 ER Case Management 자동화",
        "ai_technology": "HR Acuity · 텍스트 자동 분류",
        "key_data": "사내 고충·신고 데이터 · 과거 처리 이력",
        "adoption_method": "HR Acuity 기반 ER Case Management 솔루션",
        "use_case": (
            "Yelp 가 HR Acuity 솔루션을 도입하여 사내 고충 접수 내용 자동 분류 — 신고 사건의 "
            "초기 triage 와 일관된 처리 기준 확보"
        ),
        "outcome": "ER Case 처리의 일관성 + 담당자 효율성 향상",
        "implication": "**Tech 기업 (Yelp) 도 HR Acuity 같은 ER 전문 솔루션 도입** — Best Practice 입증",
    },
    # ── Case 5: AI Compliance Assistant 챗봇 (Hitachi, Pilot) ──
    (5, "Hitachi"): {
        "ai_adoption_goal": "사내 정책 및 규정 문서 기반 정보 검색 및 요약 + 규정 관련 사용자 문의 자동 응대",
        "ai_technology": "Hitachi AI HR Companion 'Skye' · LLM · RAG 기반 규정 검색",
        "key_data": "사내 정책 · 규정 문서 · 법률 쟁점 매핑 데이터",
        "adoption_method": "Compliance Assistant 챗봇 ('Skye')",
        "use_case": (
            "예시: '현장에서 위장 도급 리스크가 확인된 경우, 어떤 규정 검토 및 조사 항목이 "
            "필요할까?' → 질문 의도 해석 + 법률 쟁점 매핑 + 관련 규정 검색 + 조사 항목 생성. "
            "AI 가 우선 검토 필요 문서 (협력업체 운영 가이드, 도급/파견 관리 기준, 현장 관리자 "
            "운영 유의 사항) 자동 제시"
        ),
        "outcome": "최신 법령·사규 적용의 정확성 향상 + ER 담당자 규정 검토 시간 단축",
        "implication": "**LLM + RAG 기반 규정 검색** 이 준법 일관성의 핵심 도구",
    },
    (5, "Pilot"): {
        "ai_adoption_goal": "olivER AI Companion 기반 Compliance 지원",
        "ai_technology": "olivER AI Companion · LLM",
        "key_data": "사내 규정 · 법령 · 컴플라이언스 매뉴얼",
        "adoption_method": "olivER AI Companion 도입",
        "use_case": (
            "Pilot 이 olivER AI Companion 도입으로 ER 담당자에게 사내 규정·법령 즉시 검색 및 "
            "조사 가이드 자동 제시 — Compliance 일관성 확보"
        ),
        "outcome": "Compliance 검토 시간 단축 + 처리 기준 일관성 향상",
        "implication": "**산업별 특화 컴플라이언스 챗봇** 이 ER 표준화의 빠른 진입로",
    },
    # ── Case 6: 사건 처리 내역 자동 문서화 (Anonymous Company) ──
    (6, "Anonymous Company"): {
        "ai_adoption_goal": "ER 담당자의 현장 조사 데이터 기반 AI 가 결과 보고서 자동 생성",
        "ai_technology": "데이터 자동 취합 · 통합 리포트 생성 · LLM 기반 문서 자동화",
        "key_data": "사건 조사 보고서 · 노무자문 결과 · 회의록 · 징계 내역",
        "adoption_method": "처리 내역 자동 문서화 + 사건 유관 자료 취합 및 DB 화",
        "use_case": (
            "현장 조사 → 구두 면담 → 조치안 확정 → 규정 집행 후속업무 → 처리 내역 자동 문서화 "
            "(데이터 자동 취합 + 통합 리포트 생성). 사건 조사 보고서·노무자문 결과·회의록·"
            "징계내역 → 사건개요·처리이력·최종 집행내역 수록 → 건별 Resolution Note 자동 생성"
        ),
        "outcome": "처리 결과·조치 이력의 체계적 축적 + 후속 분석/감사 활용 가능",
        "implication": "**사건 단위 자동 문서화 + DB 적재** 가 후속 활용 (분석/감사) 의 기반",
    },
    # ── Case 7: 시스템 기반 후속 운영 자동화 (PSE) ──
    (7, "PSE"): {
        "ai_adoption_goal": "타결된 협약 및 규칙을 시스템 Rule 로 입력 + 내부 연동 시스템 일괄 자동 반영",
        "ai_technology": "Sodales · 시스템 Rule Engine · API 연동",
        "key_data": "단체협약 / 노조규칙 · 인사정보 시스템 · 근태/급여 시스템",
        "adoption_method": "단체협약·노조규칙 기반 후속 운영 자동화 (Rule 변환 + 시스템 일괄 반영)",
        "use_case": (
            "타결된 협약 및 규칙을 시스템 Rule 로 입력 → 인사정보 시스템, 근태/급여 시스템 등 "
            "내부 연동 시스템에 일괄 자동 반영. 단협 결과를 시스템 rule 로 변환 후 후속 절차 자동 적용"
        ),
        "outcome": "협약 변경의 운영 반영 리드타임 단축 + 운영 정합성 자동 보장",
        "implication": "**Rule Engine + 시스템 연동 자동화** 가 협약 운영 정합성의 결정 요인",
    },
}


# ═══════════════════════════════════════════════════════════════════
# 5) Helpers — 다른 도메인과 동일 시그니처
# ═══════════════════════════════════════════════════════════════════

def build_background_benchmark_rows(filter_l2: list[str] | None = None) -> list[dict]:
    filter_set = {str(n).strip() for n in filter_l2} if filter_l2 else None
    rows: list[dict] = []
    for case in ER_CASES:
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
                "benchmark_domain": "er",
            })
    return rows


def get_background_cases_for_tasks(tasks) -> list[ERCase]:
    if not tasks:
        return []
    l2_names = {getattr(t, "l2", "") or "" for t in tasks}
    l2_set = {n for n in l2_names if n}
    if not l2_set:
        return []
    return [c for c in ER_CASES if any(l2 in l2_set for l2 in c["applicable_l2"])]


def get_background_cases_by_l2(l2_names: list[str]) -> list[ERCase]:
    if not l2_names:
        return []
    l2_set = {str(n).strip() for n in l2_names if n}
    return [c for c in ER_CASES if any(l2 in l2_set for l2 in c["applicable_l2"])]


def match_benchmark_for_task(task_name: str) -> ERCase | None:
    if not task_name:
        return None
    tn = task_name.lower()
    for case in ER_CASES:
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
    lines = ["## 🏛 Background BM — Player 개요 (Doosan HR 큐레이션 · ER 도메인)"]
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
        "## 💡 Background BM — 통합 시사점 (ER 도메인)\n"
        f"**Headline**: {ii['headline']}\n\n"
        f"**핵심 Summary**: {ii['summary']}\n\n"
        f"**AI 기반 프로세스 원칙**: {ii['ai_process_principle']}\n\n"
        f"**AI 적용 방식 원칙**: {ii['ai_application_principle']}\n\n"
        f"**Value Chain**: {ii['value_chain']}\n"
    )


def get_applicable_players_for_tasks(tasks) -> list[PlayerProfile]:
    """ER 도메인 L2 가 매칭되면 2 개 영역 (집단노사·준법지원) 프로필 전체 반환."""
    applicable_cases = get_background_cases_for_tasks(tasks)
    if not applicable_cases:
        return []
    return list(ER_PLAYERS)
