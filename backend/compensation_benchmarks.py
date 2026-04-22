"""
보상 (Compensation & Benefits) 선도사 AI 적용 사례 — Background BM (PwC 큐레이션).

Doosan HR L2 '보상' · 'C&B' · 'Compensation' 등 보상 관련 프로세스에
자동 주입되는 기본 벤치마킹 데이터.

**동작 원칙** (recruit/evaluation_benchmarks.py 와 동일 패턴):
- 엑셀 L2 매칭 시 _wf_benchmark_table['__background__'] 에 자동 주입 (is_background=True)
- Step 1 기본 설계 프롬프트에 모두 포함됨 → Perplexity 검색 없이도 Step 1 정상 실행
- UI 에서 파란색으로 하이라이트, '추가 벤치마킹' 버튼으로 동적 보강 가능
- Task 이름 attribution (attribute_task_name) 에도 동일 매칭 키워드 사용

**데이터 소스** (PwC Analysis 슬라이드 원문 기반):
- IBM – Compensation Advisor with Watson (Equal Pay Blog)
- IBM Research – AI Fairness 360
- IBM – Watson Talent: Business Case for AI in HR
- PayAnalytics – Allianz Equal Pay Case Study (2022)
- beqom – Allianz Customer Success Story / Pay Intelligence Software

**보상 Value Chain** (PwC 정의):
제도 설계·인건비 계획 → 보상 산정 → 지급·운영 → 사후 분석·관리

**핵심 컨셉**:
- IBM = 'AI 추천 + 운영 자동화' 방향
- Allianz = '공정성 검증 중심' 방향
- 두 접근은 '추천 + 검증' 보완재로 결합 가능
"""
from __future__ import annotations

from typing import TypedDict


# ═══════════════════════════════════════════════════════════════════
# 1) 사례별 핵심 정보
# ═══════════════════════════════════════════════════════════════════

class CompensationCase(TypedDict):
    case_no: int
    title: str                     # 벤치마킹 사례 제목 (attribution prefix 원본)
    match_keywords: list[str]      # Task 이름 매칭 키워드 (부분 문자열, 대소문자 무시)
    applicable_l2: list[str]       # 두산 L2 매칭 (UI 표시 조건)
    companies: list[str]           # 해당 사례 적용 Player (실명)


# 보상 도메인 L2 매칭 후보 — 두산 L2 명칭이 확정되지 않아 가능한 후보 모두 포함
_L2_COMP_PLANNING = ["보상 기획", "보상", "C&B", "Compensation", "보상 설계"]
_L2_COMP_OPS      = ["보상 운영", "보상", "C&B", "Compensation", "보상 산정"]


COMPENSATION_CASES: list[CompensationCase] = [
    {
        "case_no": 1,
        "title": "스킬·역할 기반 보상 구조 설계",
        "match_keywords": [
            "보상 구조", "보상구조", "Pay Band 설계", "Pay Band 산정",
            "스킬 기반 pay", "스킬 기반 보상", "Skill-based Pay", "skill-based pay",
            "Talent Frameworks", "보상 기준 설계", "Pay 기준",
        ],
        "applicable_l2": _L2_COMP_PLANNING,
        "companies": ["IBM"],
    },
    {
        "case_no": 2,
        "title": "Pay Band 형평성 사전 검증",
        "match_keywords": [
            "Pay Band 형평성", "Pay Band 검증", "Equal Pay", "equal pay",
            "형평성 검증", "형평성 점검", "성별 편차", "직군별 편차",
            "보상 형평성", "벤치마킹 검증",
        ],
        "applicable_l2": _L2_COMP_PLANNING,
        "companies": ["Allianz"],
    },
    {
        "case_no": 3,
        "title": "인건비 시뮬레이션 및 예산 계획",
        "match_keywords": [
            "인건비 시뮬레이션", "인건비시뮬레이션", "예산 계획", "예산계획",
            "인건비 예산", "보상 예산", "예산 시나리오",
        ],
        "applicable_l2": _L2_COMP_PLANNING,
        "companies": ["IBM"],
    },
    {
        "case_no": 4,
        "title": "AI 개인별 보상 추천 (Salary Recommendation) + 추천 이유 설명 + 편향 점검",
        "match_keywords": [
            "보상 추천", "보상추천", "Salary Recommendation", "salary recommendation",
            "개인별 보상", "연봉 산정", "연봉산정", "Merit", "merit", "성과급 산정",
            "추천 이유", "Explainability", "AI Fairness", "편향 점검",
            "보상 산정", "보상산정",
        ],
        "applicable_l2": _L2_COMP_OPS,
        "companies": ["IBM"],
    },
    {
        "case_no": 5,
        "title": "매 급여 결정 시 공정성 즉시 검증 + ML 적정 보상 예측",
        "match_keywords": [
            "공정성 검증", "공정성검증", "공정성 즉시 검증", "Pay Predictor",
            "pay predictor", "Compensation Assistant", "적정 보상 예측",
            "적정보상 예측", "보상 예측", "GAP 즉시", "사전 검증",
        ],
        "applicable_l2": _L2_COMP_OPS,
        "companies": ["Allianz"],
    },
    {
        "case_no": 6,
        "title": "챗봇 기반 보상 문의 응대 + 보상 워크플로우 자동화",
        "match_keywords": [
            "보상 문의", "보상문의", "보상 챗봇", "보상 응대",
            "AskHR", "askhr", "보상 운영 자동화", "보상 워크플로우",
            "승인 라우팅", "HR transaction", "Zero-touch", "Hybrid Automation",
            "급여 문의", "연봉 문의",
        ],
        "applicable_l2": _L2_COMP_OPS,
        "companies": ["IBM"],
    },
    {
        "case_no": 7,
        "title": "연간 보상 공정성 Review",
        "match_keywords": [
            "보상 공정성 Review", "보상 Review", "보상 리뷰", "보상리뷰",
            "공정성 Review", "연간 Review", "주기적 모니터링", "보상 모니터링",
        ],
        "applicable_l2": _L2_COMP_OPS,
        "companies": ["Allianz"],
    },
    {
        "case_no": 8,
        "title": "AI 기반 보상 투자 효과 · 예산 효율 · 인력 ROI 분석",
        "match_keywords": [
            "보상 투자 효과", "보상투자 효과", "예산 효율", "인력 ROI",
            "보상 ROI", "ROI 분석", "보상 분석", "인건비 실적",
            "보상 사후 분석", "보상사후분석", "보상 결과 분석",
        ],
        "applicable_l2": _L2_COMP_OPS,
        "companies": ["IBM"],
    },
    {
        "case_no": 9,
        "title": "AI 기반 Unexplained Pay Gap 탐지 및 시정 (PayAnalytics)",
        "match_keywords": [
            "Pay Gap", "pay gap", "페이갭", "Pay Equity", "pay equity",
            "Unexplained Gap", "unexplained gap", "PayAnalytics", "payanalytics",
            "Gap 탐지", "Gap 시정", "보상 격차", "보상격차",
            "급여 격차", "임금 격차",
        ],
        "applicable_l2": _L2_COMP_OPS,
        "companies": ["Allianz"],
    },
]


# ═══════════════════════════════════════════════════════════════════
# 2) Player 프로파일 — IBM / Allianz 개요
# ═══════════════════════════════════════════════════════════════════

class PlayerProfile(TypedDict):
    name: str
    theme: str
    focus: str
    key_points: list[str]
    core_solution: str
    ai_technology: list[str]
    source: str


COMPENSATION_PLAYERS: list[PlayerProfile] = [
    {
        "name": "IBM",
        "theme": "Pay Band 설계 및 개별 보상 추천 대상 AI 적용 + 대화 기반 문의·후속 정산 자동화",
        "focus": (
            "스킬·성과·시장 데이터 기반 AI 가 팀장에게 개인별 보상 추천안을 제공하는 등 "
            "산정~지급까지 全 단계를 추천·자동화형으로 고도화"
        ),
        "key_points": [
            "Skill-based Pay 원칙: 직무가 아닌 스킬·역할 기반 pay 기준 (Talent Frameworks 로 직원 보유 스킬·역할 요구·시장가치·내부 수요 통합 관리)",
            "Salary Recommendation AI: AI 가 스킬·성과·시장 데이터 분석 후 추천 근거 (Explainability) 와 편향 점검 (AI Fairness 360) 을 포함한 개인별 보상 추천안 제공, 매니저가 최종 결정 ('AI 는 추천, 사람이 결정')",
            "AskHR 대화형 AI + 워크플로우 자동화: 보상 관련 문의·승인·HR transaction 전 과정 운영 자동화 (Zero-touch support / Hybrid Automation), AI 기반 HR 운영으로 $197M 절감",
        ],
        "core_solution": "Talent Frameworks + Salary Recommendation AI + AskHR + AI Fairness 360",
        "ai_technology": [
            "스킬 추론", "ML 기반 보상 추천", "Explainability (Watson)",
            "AI Fairness 360 (편향 점검)", "대화형 AI (LLM)", "워크플로우 자동화",
        ],
        "source": (
            "IBM – Compensation Advisor with Watson (Equal Pay Blog); "
            "IBM Research – AI Fairness 360; "
            "IBM – Watson Talent: Business Case for AI in HR"
        ),
    },
    {
        "name": "Allianz",
        "theme": "공정성 검증 중심 AI 적용",
        "focus": (
            "PayAnalytics 의 회귀분석·ML 기반 검증으로 매 보상 결정의 공정성을 "
            "실시간 점검하는 AI 가 특화"
        ),
        "key_points": [
            "공정성 중심 보상 정책 구축: 글로벌 벤치마킹 + Equal Pay 내재화, 업무 간 비교 가능 구조, TTDC 관리·시장 포지셔닝",
            "설계 시 형평성 사전 점검: 국가·법인별 Pay Band 설계 + 성별·직군별 편차 사전 검증",
            "실시간 보상 공정성 검토: Compensation Assistant (매 급여 결정 시 공정성 부합 여부 즉시 검증) + Pay Predictor (ML 기반 적정 보상 예측 및 비용 사전 확인)",
            "Pay Equity 분석·모니터링: ML 기반 Unexplained Pay Gap 탐지 + Gap 해소 조정안 자동 계산 + 지속 모니터링",
            "실제 적용 성과: 70개국 10만+ 직원 대상 적용, 2021 글로벌 Equal Pay 달성, 2022 독일 HR Management Prize 수상",
        ],
        "core_solution": "Compensation Assistant (beqom) + Pay Predictor + PayAnalytics",
        "ai_technology": [
            "ML 회귀분석 (Pay Gap)", "ML 기반 적정 보상 예측",
            "실시간 공정성 검증 알고리즘", "자동 Gap 시정안 산출",
        ],
        "source": (
            "PayAnalytics – Allianz Equal Pay Case Study (2022); "
            "beqom – Allianz Customer Success Story; "
            "beqom – Pay Intelligence Software"
        ),
    },
]


# ═══════════════════════════════════════════════════════════════════
# 3) 통합 시사점
# ═══════════════════════════════════════════════════════════════════

INTEGRATED_INSIGHTS: dict[str, str] = {
    "headline": (
        "IBM 은 AI 가 보상을 추천하고 운영을 자동화하는 방향, Allianz 는 매 보상 결정의 "
        "공정성을 AI 로 실시간 검증·시정하는 방향으로, 두 접근은 '추천 + 검증' 의 보완재로 결합 가능"
    ),
    "summary": (
        "스킬 데이터를 기반으로 보상 설계 및 개인 보상 산정까지 AI 가 지원, 반복적 운영 업무는 "
        "대화 기반 문의 대응 및 자동화 구현. 통합 DB 기반 Pay Equity 상시 감지·검증으로 "
        "공정성을 구조적으로 내재화"
    ),
    "ai_process_principle": (
        "제도 설계 (원칙·기준) → 산정 (AI 추천·검증) → 사후 분석 (Gap 탐지) → 제도 설계 피드백으로 "
        "밸류체인 全 단계가 순환·연계되는 구조여야 한다. 사후 분석 결과가 다음 사이클의 제도 설계에 "
        "재반영되어 데이터와 운영이 함께 정교화되는 폐쇄 루프 구성이 핵심."
    ),
    "ai_application_principle": (
        "각 Value Chain 단계에 목적별 전문 AI (보상안 추천 · 공정성 분석 · 설명 가능성 구현) 가 "
        "개별적으로 구현되어 서로 간의 Input·Output 이 연계되는 구조로 설계되어야 한다. "
        "Explainability + Fairness 검증을 보상 AI 도입의 기본 요건으로 내재화."
    ),
    "value_chain": (
        "보상 value chain: 제도 설계·인건비 계획 → 보상 산정 → 지급·운영 → 사후 분석·관리"
    ),
}


# ═══════════════════════════════════════════════════════════════════
# 4) 벤치마킹 테이블 row 데이터 — _wf_benchmark_table 자동 주입용
# ═══════════════════════════════════════════════════════════════════

_COMPANY_META: dict[str, dict[str, str]] = {
    "IBM": {
        "company_type": "Tech 선도",
        "industry": "IT 솔루션",
        "infrastructure": "Talent Frameworks + Salary Recommendation AI + AskHR + AI Fairness 360",
    },
    "Allianz": {
        "company_type": "非Tech 실제 구현",
        "industry": "글로벌 보험·금융",
        "infrastructure": "Compensation Assistant (beqom) + Pay Predictor + PayAnalytics",
    },
}


_CASE_ROW_DETAILS: dict[tuple[int, str], dict[str, str]] = {
    (1, "IBM"): {
        "ai_adoption_goal": "스킬·역할 기반 pay 구조 + 시장 벤치마크 분석으로 보상 구조 설계 자동화",
        "ai_technology": "Talent Frameworks · 스킬 추론 · 시장 벤치마크 분석",
        "key_data": "직원 보유 스킬 · 역할 요구 · 시장가치 · 내부 수요",
        "adoption_method": "Skill-based Pay 원칙 적용 (직무 아닌 스킬·역할 기반 Pay 기준)",
        "use_case": (
            "Talent Frameworks 로 직원 보유 스킬·역할 요구·시장가치·내부 수요를 통합 관리하여 "
            "직무가 아닌 스킬·역할 기반 pay 기준 설계. 시장 벤치마크 + 내부 스킬 분포 분석을 결합한 "
            "데이터 기반 보상 구조 자동화"
        ),
        "outcome": "AI 기반 HR 운영으로 $197M 절감 + Skill-based Pay 체계 확립",
        "implication": "**스킬-역할 기반 보상 체계** 전환에는 직무-스킬 매핑 DB 와 시장 벤치마크 파이프라인이 선행 필요",
    },
    (2, "Allianz"): {
        "ai_adoption_goal": "글로벌 보상 벤치마킹 + Pay Band 설계안의 형평성 사전 점검",
        "ai_technology": "회귀분석 · 편차 검증 · 글로벌 벤치마킹",
        "key_data": "국가·법인별 Pay Band · 성별·직군별 보상 데이터 · 글로벌 시장 데이터",
        "adoption_method": "Equal Pay 내재화 + 형평성 사전 검증 프로세스",
        "use_case": (
            "Equal Pay 를 보상 정책·프로세스에 내재화. 글로벌 벤치마킹 + Pay Band 설계안의 "
            "형평성을 사전에 점검 (국가·법인별 Pay Band 설계, 성별·직군별 편차 사전 검증)"
        ),
        "outcome": "TTDC 관리·시장 포지셔닝 + 형평성 사전 검증 체계 확보 + 사후 Gap 발생 차단",
        "implication": "**Pay Band 설계 단계의 형평성 검증** 의무화로 사후 시정 비용 최소화",
    },
    (3, "IBM"): {
        "ai_adoption_goal": "인건비 시뮬레이션 자동화 + 예산 계획 정밀도 향상",
        "ai_technology": "시뮬레이션 모델 · 시장 벤치마크 · 시나리오 분석",
        "key_data": "직무·스킬 분포 · 시장 보상 벤치마크 · 인건비 정책",
        "adoption_method": "Pay 기준 설계 기반 시뮬레이션",
        "use_case": (
            "직무-스킬 매핑 + Pay 기준 설계를 기반으로 인건비 시뮬레이션·예산 계획 자동화. "
            "시장 벤치마크와 내부 스킬 분포 분석을 결합한 시나리오별 예산 추정"
        ),
        "outcome": "예산 계획 정밀도 향상 + 인건비 변동 시나리오 사전 파악",
        "implication": "**시나리오별 시뮬레이션** 자동화로 의사결정 속도·품질 동시 향상",
    },
    (4, "IBM"): {
        "ai_adoption_goal": "AI 기반 개인별 보상 추천 + 추천 근거 설명 가능성 + 편향 점검 자동화",
        "ai_technology": "Salary Recommendation AI · Explainability · AI Fairness 360",
        "key_data": "스킬·성과·시장 데이터",
        "adoption_method": "Salary Recommendation AI 4 단계 (데이터 → AI 추천 → 이유 설명 → 매니저 결정)",
        "use_case": (
            "스킬·성과·시장 데이터를 기반으로 AI 추천안 생성. 추천마다 이유 설명 (Explainability), "
            "AI Fairness 360 으로 편향 점검 후 매니저가 최종 결정. 'AI 는 추천, 사람이 결정' 원칙. "
            "merit·채용·승진 시 모두 적용 가능"
        ),
        "outcome": "추천 근거 투명화 + 편향 사전 차단 + 매니저 의사결정 일관성 향상",
        "implication": "**Explainability + Fairness 검증** 이 보상 AI 도입의 사회적 신뢰 확보 핵심 요건",
    },
    (5, "Allianz"): {
        "ai_adoption_goal": "매 보상 결정 시점에 공정성 즉시 검증 + ML 기반 적정 보상 예측",
        "ai_technology": "ML 기반 회귀분석 · Pay Predictor (ML) · 실시간 공정성 검증",
        "key_data": "급여 결정 데이터 · 직무·스킬·성과 · 비교 코호트 데이터",
        "adoption_method": "Compensation Assistant (beqom) + Pay Predictor",
        "use_case": (
            "Compensation Assistant 가 매 급여 결정 시점에 공정성 부합 여부를 즉시 검증하여 "
            "부합한 보상안을 제시. Pay Predictor 가 ML 기반으로 적정 보상을 예측하여 비용 사전 확인. "
            "merit·채용·승진 모든 인사 트리거 시 GAP 즉시 확인 + 의사결정 전 검증·예방"
        ),
        "outcome": "보상 결정의 공정성 실시간 보장 + 비용 사전 예측 + 사후 시정 비용 최소화",
        "implication": "**의사결정 전 검증 (Pre-decision validation)** 으로 사후 시정 부담을 구조적으로 제거",
    },
    (6, "IBM"): {
        "ai_adoption_goal": "보상 문의 자동 응대 + HR transaction 후속 과정 자동화",
        "ai_technology": "대화형 AI (AskHR · LLM) · 워크플로우 자동화",
        "key_data": "보상 정책 FAQ · 직원 보상 데이터 · HR transaction 로그",
        "adoption_method": "AskHR 자동화 운영 (Zero-touch support / Hybrid Automation)",
        "use_case": (
            "AskHR 대화형 AI + 워크플로우 자동화로 보상 관련 직원 문의 자동 응대, 승인 라우팅 "
            "자동화, HR transaction 후속 반영. Zero-touch support 구현 + Hybrid Automation 방식"
        ),
        "outcome": "보상 운영 비용 절감 + 응답 속도 단축 + HR 담당자 고부가가치 업무 집중",
        "implication": "**보상 운영 자동화** 는 HR transaction · Payroll 시스템과의 API 연계가 필수",
    },
    (7, "Allianz"): {
        "ai_adoption_goal": "주기적 운영 모니터링 (연간 보상 공정성 Review) 자동화",
        "ai_technology": "회귀분석 · 통계 검증 · 자동 레포팅",
        "key_data": "보상 결정 이력 · 직군·국가별 데이터",
        "adoption_method": "주기적 자동화된 공정성 Review (연간 보상 공정성 Review 수행)",
        "use_case": (
            "모든 보상 결정 결과를 통계적으로 분석하여 공정성 유지 여부를 주기적으로 검증. "
            "Review 결과를 다음 연도 제도 설계의 피드백 인풋으로 순환 연결"
        ),
        "outcome": "공정성 정책의 운영 단계 정합성 확보 + 폐쇄 루프 보상 거버넌스 구축",
        "implication": "**연간 공정성 Review** 결과의 제도 설계 피드백 순환이 보상 거버넌스의 핵심",
    },
    (8, "IBM"): {
        "ai_adoption_goal": "보상 투자 효과 분석 + 예산 효율 추적 + 인력 투자 ROI 분석",
        "ai_technology": "데이터 분석 · 통계 모델링 · 레포팅 자동화",
        "key_data": "보상 결정 결과 · 예산 데이터 · 인력 성과 데이터",
        "adoption_method": "AI 기반 사후 분석 레포팅",
        "use_case": (
            "보상 결정 결과 분석, 예산 사용 효율 추적, 인력 투자 ROI 분석을 자동화된 "
            "레포트로 제공. 보상 사후 평가 결과가 다음 사이클의 보상 의사결정에 환류"
        ),
        "outcome": "보상 투자 의사결정의 데이터 기반 정밀화 + 인건비 효율성 가시화",
        "implication": "**ROI 기반 보상 의사결정** 이 가능하려면 성과-보상 연계 데이터 축적 필요",
    },
    (9, "Allianz"): {
        "ai_adoption_goal": "ML 기반 설명되지 않는 Pay Gap 탐지 + 자동 조정안 계산",
        "ai_technology": "PayAnalytics ML · 회귀분석 · 자동 조정안 산출",
        "key_data": "전체 직원 보상 데이터 · 직군·성별·연령·근속 등 코호트 변수",
        "adoption_method": "PayAnalytics 머신러닝 분석",
        "use_case": (
            "ML 기반 분석으로 설명되지 않는 Pay Gap 을 파악 (Unexplained Gap 탐지). "
            "Gap 발생 대상 식별 후 Gap 을 없애는 조정안 자동 계산 (지속 모니터링 수행). "
            "70개국 10만+ 직원 대상 적용, 2022 독일 HR Management Prize 수상"
        ),
        "outcome": "예산 최적화 + 시정안 자동 산출 + 상시 모니터링 체계 구축 + 글로벌 Equal Pay 달성",
        "implication": "**Unexplained Gap** 탐지 모델은 코호트 변수 정의·검증 단계가 핵심 (변수 누락 시 위양성)",
    },
}


# ═══════════════════════════════════════════════════════════════════
# 5) Helpers — recruit/evaluation_benchmarks 와 동일 시그니처
# ═══════════════════════════════════════════════════════════════════

def build_background_benchmark_rows(filter_l2: list[str] | None = None) -> list[dict]:
    """Background BM row 리스트 (BenchmarkTableRow 형식 + is_background=True)."""
    filter_set = {str(n).strip() for n in filter_l2} if filter_l2 else None
    rows: list[dict] = []
    for case in COMPENSATION_CASES:
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
                "benchmark_domain": "compensation",
            })
    return rows


def get_background_cases_for_tasks(tasks) -> list[CompensationCase]:
    if not tasks:
        return []
    l2_names = {getattr(t, "l2", "") or "" for t in tasks}
    l2_set = {n for n in l2_names if n}
    if not l2_set:
        return []
    return [c for c in COMPENSATION_CASES if any(l2 in l2_set for l2 in c["applicable_l2"])]


def get_background_cases_by_l2(l2_names: list[str]) -> list[CompensationCase]:
    if not l2_names:
        return []
    l2_set = {str(n).strip() for n in l2_names if n}
    return [c for c in COMPENSATION_CASES if any(l2 in l2_set for l2 in c["applicable_l2"])]


def match_benchmark_for_task(task_name: str) -> CompensationCase | None:
    if not task_name:
        return None
    tn = task_name.lower()
    for case in COMPENSATION_CASES:
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
    lines = ["## 🏛 Background BM — Player 개요 (Doosan HR 큐레이션 · 보상 도메인)"]
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
        "## 💡 Background BM — 통합 시사점 (보상 도메인)\n"
        f"**Headline**: {ii['headline']}\n\n"
        f"**핵심 Summary**: {ii['summary']}\n\n"
        f"**AI 기반 프로세스 원칙**: {ii['ai_process_principle']}\n\n"
        f"**AI 적용 방식 원칙**: {ii['ai_application_principle']}\n\n"
        f"**Value Chain**: {ii['value_chain']}\n"
    )


def get_applicable_players_for_tasks(tasks) -> list[PlayerProfile]:
    """보상 도메인 L2 가 매칭되면 2 사 프로필 전체 반환, 아니면 빈 리스트."""
    applicable_cases = get_background_cases_for_tasks(tasks)
    if not applicable_cases:
        return []
    return list(COMPENSATION_PLAYERS)
