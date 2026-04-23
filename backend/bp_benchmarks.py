"""
BP (HR Business Partner · 운영지원) 선도사 AI 적용 사례 — Background BM (PwC 큐레이션).

Doosan HR L2 'BP' · '복리후생' 프로세스에 자동 주입되는 기본 벤치마킹 데이터.

**동작 원칙** (다른 도메인 모듈과 동일 패턴):
- 엑셀 L2 매칭 시 _wf_benchmark_table['__background__'] 에 자동 주입 (is_background=True)
- Step 1 기본 설계 프롬프트에 모두 포함됨 → Perplexity 검색 없이도 Step 1 정상 실행
- UI 에서 파란색으로 하이라이트
- Task 이름 attribution 에도 동일 매칭 키워드 사용

**데이터 소스** (PwC Analysis 슬라이드 원문 기반):
- IBM – AskHR, AI Agents for HR
- IBM – Multi-Agent Orchestration in watsonx Orchestrate
- IBM – Agentic Workflows and Domain Agents (2025)
- Microsoft – Using Copilot in Human Resources (Copilot Scenario Library)
- Microsoft – Employee Self-Service Agent in Microsoft 365 Copilot
- Microsoft – Orchestrate Agent Behavior with Generative AI (Microsoft Copilot Studio)

**BP Value Chain** (PwC 정의):
문의대응 → HR Transaction → 인사정보 유지·관리 → 급여·복리후생 정산

**핵심 컨셉**:
- Microsoft = 'Self-Service 에 제한된 HR 운영 지원' — Teams·Portal 내 AI 내재화로 접근성·편의성 향상
- IBM = 'HR 운영 전반의 자동화·고도화' — AskHR 중심 E2E 실행형 구조
- 공통 방향: 기능별 분절 업무 → Orchestration 기반 Case 관리형 E2E 구조
"""
from __future__ import annotations

from typing import TypedDict


# ═══════════════════════════════════════════════════════════════════
# 1) 사례별 핵심 정보
# ═══════════════════════════════════════════════════════════════════

class BPCase(TypedDict):
    case_no: int
    title: str
    match_keywords: list[str]
    applicable_l2: list[str]
    companies: list[str]


# BP/복리후생 L2 매칭 — 두산 L2 'BP', '복리후생' + 가능 후보
_L2_BP = ["BP", "복리후생", "운영지원", "HR Operations"]


BP_CASES: list[BPCase] = [
    {
        "case_no": 1,
        "title": "BP AI Orchestration 기반 E2E Case 관리",
        "match_keywords": [
            "Orchestration", "orchestration", "오케스트레이션",
            "BP Orchestration", "Case 관리", "case 관리", "E2E 운영", "E2E Case",
            "적응적 조정", "Agent 조율", "Routing Engine", "routing engine",
            "Workflow 선정", "처리 유형 판단",
        ],
        "applicable_l2": _L2_BP,
        "companies": ["Microsoft", "IBM"],
    },
    {
        "case_no": 2,
        "title": "문의응대 AI Agent",
        "match_keywords": [
            "문의 응대", "문의응대", "HR 문의", "HR 챗봇",
            "Self-Service", "Self Service", "self-service", "self service",
            "AskHR", "askhr", "자동 응대", "정책 안내", "정책 응답",
            "FAQ", "담당자 연계", "문의 접수", "문의 분류",
            "Copilot Agent", "copilot agent",
        ],
        "applicable_l2": _L2_BP,
        "companies": ["Microsoft", "IBM"],
    },
    {
        "case_no": 3,
        "title": "HR Transaction 처리 AI Agent",
        "match_keywords": [
            "HR Transaction", "HR 트랜잭션", "HR 신청", "HR 변경",
            "증명서 발급", "증명서발급", "휴가 신청", "휴가 프로세스", "휴가프로세스",
            "휴직 신청", "휴직신청", "휴직 생성", "육아휴직",
            "온보딩 프로세스", "온보딩프로세스", "Leave of Absence", "leave of absence",
            "Onboarding Agent", "onboarding agent",
            "승인 라우팅", "요청 접수", "요건 검토", "ERP 연계", "그룹웨어 연계",
            "Workflow 실행",
        ],
        "applicable_l2": _L2_BP,
        "companies": ["Microsoft", "IBM"],
    },
    {
        "case_no": 4,
        "title": "인사정보 유지·관리 AI Agent",
        "match_keywords": [
            "인사정보", "인사 정보", "인사 데이터", "인사데이터",
            "조직 정보", "조직정보", "기준정보", "기준 정보",
            "정합성 점검", "정합성점검", "이력 관리", "프로파일 관리",
            "인사 분석", "현황 모니터링", "다중 시스템 입력", "인사카드",
            "인사마스터", "조직/직무",
        ],
        "applicable_l2": _L2_BP,
        "companies": ["Microsoft", "IBM"],
    },
    {
        "case_no": 5,
        "title": "급근복 정산연계 AI Agent",
        "match_keywords": [
            "급여 정산", "급여정산", "복리후생 정산", "복리후생정산",
            "휴가 정산", "보상 정산", "보상정산", "정산 연계", "정산연계",
            "급여 영향", "급여·정산", "급여정산 영향",
            "오류 감지", "자동 보정", "정산 마감",
            "급근복", "후속처리", "후속 처리",
            "급여·휴가·보상", "월급여 마감",
        ],
        "applicable_l2": _L2_BP,
        "companies": ["IBM"],
    },
]


# ═══════════════════════════════════════════════════════════════════
# 2) Player 프로파일 — Microsoft / IBM
# ═══════════════════════════════════════════════════════════════════

class PlayerProfile(TypedDict):
    name: str
    theme: str
    focus: str
    key_points: list[str]
    core_solution: str
    ai_technology: list[str]
    source: str


BP_PLAYERS: list[PlayerProfile] = [
    {
        "name": "Microsoft",
        "theme": "Self-Service 에 제한된 HR 운영 지원",
        "focus": (
            "구성원 Self-Service 중심으로 문의·신청·안내 등 HR 업무 처리 경험 개선. "
            "기존 협업 채널 (Teams, SharePoint, Portal) 내에서 AI 를 내재화해 구성원 접점의 "
            "편의성·접근성을 높임"
        ),
        "key_points": [
            "HR Copilot Agent 탐색 & 선정: Teams·SharePoint·Portal 기반 + Leave of Absence Agent / Onboarding Agent / Self Service Agent 중에서 업무에 맞는 Agent 자동 선택",
            "5 단계 Orchestration: ① 요청 이해·도메인 매핑 → ② Action Flow 선정·계획 수립 (3 Case 분류) → ③ Flow 실행·상태 모니터링 → ④ 적응적 조정 → ⑤ 이해관계자 커뮤니케이션",
            "3 Case 분류: Case 1 조회/등록 단일 Flow, Case 2 승인 필요 다단계 Flow, Case 3 사람 개입 필수 예외·고위험 Flow",
            "적응적 조정: 성공→조정, 대기→알람 전송, 실패→재시도·예외처리·사람에게 티켓 전환",
            "이해관계자 커뮤니케이션: 주요 승인자에게 상황 전달, 고위험 Case 전문가 호출, 요청자에게 결과 정리 후 전달",
            "표준화된 요청을 신속 처리하는 Orchestration 기반 운영 효율화",
        ],
        "core_solution": "HR Copilot Agent (Teams, SharePoint, Portal) + Microsoft 365 Copilot Studio",
        "ai_technology": [
            "Copilot Scenario Library", "Employee Self-Service Agent",
            "Orchestrate Agent Behavior", "Action Flow Engine", "Adaptive Orchestration",
        ],
        "source": (
            "Microsoft – Using Copilot in Human Resources (Copilot Scenario Library); "
            "Microsoft – Employee Self-Service Agent in Microsoft 365 Copilot; "
            "Microsoft – Orchestrate Agent Behavior with Generative AI (Microsoft Copilot Studio)"
        ),
    },
    {
        "name": "IBM",
        "theme": "HR 운영 전반의 자동화·고도화",
        "focus": (
            "통합된 AI 창구인 AskHR 에서 구성원의 Self-service 를 너머 전반적인 HR 업무 수행이 "
            "가능토록 Orchestration, AI, Automation 등 Multi-Layer 기반 AI 구현. 구성원·매니저·HR "
            "전반을 대상으로 인사운영 업무의 E2E 수행 지원"
        ),
        "key_points": [
            "AskHR 통합 AI 창구: HR, 관리자, 현업 (HR 문의 발령요청, 데이터수정·증명서발급, 급여 사전작업·복리후생 정산) 단일 인터페이스",
            "질문 의미 파악 & 핵심 정보 추출 (LLM) + HR 도메인 & 처리방식 분류 (Benefit / Payroll / Policy / Career / Support)",
            "지식형 Q&A (RAG) + Orchestrate 호출 2-track (단순 Q&A vs 업무 실행)",
            "Watsonx Orchestrate 의 Routing Engine 처리방식: Single Task (휴가생성, 인사카드조회 등), Workflow (잔여 연차 조회→휴가생성→승인자할당→알림발송 등), Agent (HR규정/근무형태 조회→육아휴직 가능여부→휴직생성→승인자할당 등 복잡 판단)",
            "자동 일정 업무: 트리거 (예: 월급여 마감 5일 전) → Workflow (인사 변경·휴직·승진·전배 이벤트 리스트 조회 → 각 이벤트별 후속업무 진행)",
            "커넥터·API·RPA 호출로 Backend 업무수행 (교육, HRIS, O365, IBM RPA, Payroll 등)",
            "LLM 기반 결과 집계 & 요약 작성 + 결과 검토 후 미달성 시 반복",
        ],
        "core_solution": "AskHR + Watsonx Orchestrate + IBM RPA + 지식형 Q&A (RAG)",
        "ai_technology": [
            "LLM 기반 의미 파악", "RAG (Retrieval-Augmented Generation)",
            "Multi-agent Orchestration", "Agentic Workflows",
            "Routing Engine", "커넥터·API·RPA 자동화",
        ],
        "source": (
            "IBM – AskHR; IBM – AI Agents for HR; "
            "IBM – Multi-Agent Orchestration in watsonx Orchestrate; "
            "IBM – Agentic Workflows and Domain Agents (2025)"
        ),
    },
]


# ═══════════════════════════════════════════════════════════════════
# 3) 통합 시사점
# ═══════════════════════════════════════════════════════════════════

INTEGRATED_INSIGHTS: dict[str, str] = {
    "headline": (
        "운영지원의 AX 는 기능별 분절 업무를 넘어, 요청 접수부터 처리·정보반영·정산까지 "
        "연결되는 E2E 운영체계를 Orchestration 기반으로 구현하는 방향으로 고도화되고 있음"
    ),
    "summary": (
        "요청에서 종결까지 전체 업무를 E2E 로 연결하고, 이를 Orchestration 기반의 "
        "Case 관리형 구조로 설계"
    ),
    "ai_process_principle": (
        "BP 프로세스는 기능별 업무 묶음이 아니라, 문의응대 / 요청·처리 / 정보반영 / 정산으로 "
        "이어지는 Value Chain 흐름 기준으로 구성되어야 한다. 하나의 요청이 실제 종결될 때까지 "
        "단계 간 연계와 후속 반영을 포함해 end-to-end 로 설계되어야 한다."
    ),
    "ai_application_principle": (
        "BP AI 는 하나의 Orchestration 이 적정 모듈 Agent 를 배정·조율하는 구조로 구현되어야 한다. "
        "요청의 진행상태나 예외처리를 끝까지 추적·조율하는 Case 관리형 구조로 설계 — "
        "문의응대 Agent / Transaction 처리 Agent / 인사정보 유지·관리 Agent / 급근복 정산연계 Agent "
        "같이 도메인별 모듈 Agent 를 상위 Orchestration 이 조율."
    ),
    "value_chain": (
        "BP value chain: 문의대응 → HR Transaction → 인사정보 유지·관리 → 급여·복리후생 정산"
    ),
}


# ═══════════════════════════════════════════════════════════════════
# 4) 벤치마킹 테이블 row 데이터
# ═══════════════════════════════════════════════════════════════════

_COMPANY_META: dict[str, dict[str, str]] = {
    "Microsoft": {
        "company_type": "Tech 선도",
        "industry": "IT 솔루션",
        "infrastructure": "HR Copilot Agent (Teams/SharePoint/Portal) + Microsoft 365 Copilot Studio",
    },
    "IBM": {
        "company_type": "Tech 선도",
        "industry": "IT 솔루션",
        "infrastructure": "AskHR + Watsonx Orchestrate + IBM RPA + RAG",
    },
}


_CASE_ROW_DETAILS: dict[tuple[int, str], dict[str, str]] = {
    (1, "Microsoft"): {
        "ai_adoption_goal": "Orchestration 기반으로 HR 요청을 E2E 처리 (Case 관리형 구조)",
        "ai_technology": "Action Flow Engine · Adaptive Orchestration · Agent Routing",
        "key_data": "요청·문의 원문 · 조직/사용자 컨텍스트 · HR 지식·정책 · HRIS 데이터",
        "adoption_method": "Microsoft 365 Copilot Studio 기반 Orchestrate Agent Behavior 구현",
        "use_case": (
            "5 단계 Orchestration: 요청 이해·도메인 매핑 (문의 접수 → 조직·사용자 컨텍스트 + "
            "HR 지식 반영 → 의도·핵심 정보 추출 → 도메인 매핑 → 후보 Flow/Action 탐색) → "
            "Action Flow 선정·계획 수립 (3 Case 분류: 단일 Flow / 다단계 Flow / 예외·고위험) → "
            "Flow 실행·상태 모니터링 → 적응적 조정 (성공·대기·실패 분기) → 이해관계자 커뮤니케이션"
        ),
        "outcome": "표준화된 요청을 신속 처리 + 예외·고위험 Case 도 체계적으로 관리",
        "implication": "**Case 분류 체계 (단일/다단계/예외) + 적응적 조정 룰** 이 운영 안정성의 핵심",
    },
    (1, "IBM"): {
        "ai_adoption_goal": "Multi-Layer (Orchestration + AI + Automation) 기반 HR 운영 전반 자동화",
        "ai_technology": "Watsonx Orchestrate · Multi-agent Orchestration · Agentic Workflows",
        "key_data": "요청 원문 · HR 규정·정책 DB · HRIS · Payroll · 그룹웨어 연동 데이터",
        "adoption_method": "AskHR 통합 AI 창구 + Watsonx Orchestrate Routing Engine",
        "use_case": (
            "Routing Engine 이 요청을 분석해 적절한 처리 방식 결정 — Single Task (휴가생성, "
            "인사카드조회 등 한 가지 기능), Workflow (잔여 연차 조회→휴가생성→승인자할당→"
            "알림발송 등 절차), Agent (HR규정/근무형태 조회→육아휴직 가능여부→휴직생성 등 복잡 "
            "판단·조율). 자동 일정 업무는 트리거 (월급여 마감 5일 전 등) → Workflow 자동 실행"
        ),
        "outcome": "구성원·매니저·HR 전반을 대상으로 E2E 수행 지원 + 운영 효율화 + 업무 일관성 제고",
        "implication": "**Routing Engine 의 처리방식 분류 (Single/Workflow/Agent)** 가 orchestration 복잡도 관리의 핵심",
    },
    (2, "Microsoft"): {
        "ai_adoption_goal": "Self-Service 중심 HR 문의 응대 (Teams·Portal 내 AI 내재화)",
        "ai_technology": "Copilot Scenario Library · Employee Self-Service Agent · NLP",
        "key_data": "직원 문의 원문 · HR 정책·제도 문서 · FAQ DB",
        "adoption_method": "HR Copilot Agent (Leave of Absence Agent / Onboarding Agent / Self Service Agent)",
        "use_case": (
            "Teams, SharePoint, Portal 등 기존 협업 채널 내 AI 내재화. 직원의 즉시 응답 경험 "
            "제고 + 문의 채널 분산 완화. 직원이 '업무를 수행하기 위해 어떤 Agent 를 선택해야 "
            "하는가' 를 AI 가 자동 판단"
        ),
        "outcome": "HR 문의 Self-Service 지원 + 문의 채널 분산 완화 + 구성원 접점의 편의성·접근성 향상",
        "implication": "**기존 협업 Tool (Teams/Portal) 에 AI 내재화** 가 Self-Service 채택률의 핵심 요인",
    },
    (2, "IBM"): {
        "ai_adoption_goal": "AI 챗봇을 활용한 구성원 문의 응대 (반복 문의 대규모 자동 처리 + HR 상담 부담 경감)",
        "ai_technology": "LLM 기반 의미 파악 · RAG (Retrieval-Augmented Generation) · HR 도메인 분류",
        "key_data": "문의 원문 · HR 규정·정책·매뉴얼 · 도메인 분류 기준 (Benefit/Payroll/Policy/Career/Support)",
        "adoption_method": "AskHR 통합 AI 창구 + 지식형 Q&A (RAG)",
        "use_case": (
            "AskHR 에서 LLM 이 질문 의미 파악 & 핵심 정보 추출, HR 도메인 (Benefit / Payroll / "
            "Policy / Career / Support) & 처리방식 분류. 단순 질문은 지식형 Q&A (RAG) 로 답변, "
            "복잡 요청은 Orchestrate 호출"
        ),
        "outcome": "반복 문의의 대규모 자동 처리 + HR 상담 부담 경감 + HR 도메인별 일관된 응답",
        "implication": "**RAG 기반 지식 검색 + 도메인 분류** 로 응답 정확도와 커버리지 동시 확보",
    },
    (3, "Microsoft"): {
        "ai_adoption_goal": "Self-service 휴가프로세스·온보딩 프로세스 등 표준 HR Transaction 지원",
        "ai_technology": "Leave of Absence Agent · Onboarding Agent · Action Flow Engine",
        "key_data": "휴가 규정·이력 · 온보딩 체크리스트 · HRIS 직원 정보 · 정책·법규",
        "adoption_method": "Microsoft 365 Copilot Studio 기반 전용 Agent",
        "use_case": (
            "예시: '둘째 출산 때문에 내년 1월부터 1년 동안 육아휴직을 쓰고 싶어요' → 직원 성별/"
            "재직상태/휴직 이력/휴직 규정 조회 → 휴직 도메인 매핑 → 정책·법규 검증 (경계/위반"
            "가능성 여부에 따라 HR 검토 추가) → 휴직 신청 및 승인 → HRIS 정보 조회 + 정책 "
            "테이블과 매핑하여 검증 → 단계별 상태 모니터링. 경계/고위험 케이스의 경우 HRBP 에게 "
            "전달 후 지연 시 리마인더 발송 및 기한초과로 자동 취소·보류"
        ),
        "outcome": "Self Service 중심의 업무 지원 + 표준 Transaction 신속 처리",
        "implication": "**도메인 특화 Agent 설계 (휴가/온보딩 등)** 가 Transaction 자동화의 기본 단위",
    },
    (3, "IBM"): {
        "ai_adoption_goal": "Self-service 및 HR 신청·변경·증명서·휴가 업무 실행 (HR 업무 E2E 자동화, 처리 리드타임 단축)",
        "ai_technology": "Watsonx Orchestrate Workflow · Multi-agent Orchestration · 커넥터·API·RPA 호출",
        "key_data": "HR 신청·변경·증명서·휴가 요청 원문 · HRIS · Payroll · ERP · 그룹웨어 데이터",
        "adoption_method": "Watsonx Orchestrate Workflow + 커넥터·API·RPA 호출",
        "use_case": (
            "HR Transaction 요청 이해 → Routing Engine 이 Single / Workflow / Agent 결정 → "
            "Backend 업무수행 (교육, HRIS, O365, IBM RPA, Payroll 연동) → 결과 집계 & 요약 "
            "작성 (LLM) → 결과 검토 후 미달성 시 반복"
        ),
        "outcome": "HR 업무의 end-to-end 자동화 + 처리 리드타임 단축 + 처리 정확성 강화",
        "implication": "**커넥터·API·RPA 통합** 이 Backend 시스템 연동 자동화의 필수 인프라",
    },
    (4, "Microsoft"): {
        "ai_adoption_goal": "Self-service 정보 조회·분석 지원 (화면 전환 최소화, HR 정보 활용 편의 향상)",
        "ai_technology": "Self Service Agent · HR 데이터 분석",
        "key_data": "직원 HR 정보 · 조직/직무 정보 · 이력·프로파일",
        "adoption_method": "HR Copilot Agent 내 Self Service Agent",
        "use_case": (
            "Self-service 정보 조회·분석 지원. 직원이 Teams / Portal 에서 바로 자기 HR 정보 조회 "
            "+ AI 가 분석 지원. 화면 전환 최소화"
        ),
        "outcome": "HR 정보 활용 편의 향상 + 화면 전환 마찰 제거",
        "implication": "**Self-service 분석 기능** 은 HR 담당자 부담 감소 및 직원 참여율 제고",
    },
    (4, "IBM"): {
        "ai_adoption_goal": "인사·조직 정보 조회 및 변경 반영 (다중 시스템 입력 축소, 기준정보 정합성 제고)",
        "ai_technology": "LLM · 다중 시스템 커넥터 · 정합성 점검",
        "key_data": "인사 마스터 · 조직·직무 · 이력·프로파일 · HR 시스템 간 데이터",
        "adoption_method": "AskHR + Watsonx Orchestrate + 다중 시스템 커넥터",
        "use_case": (
            "인사·조직 정보 조회 요청을 AskHR 에서 처리. 인사 데이터 변경 시 다중 시스템 입력을 "
            "단일 Orchestration 이 처리 → 기준정보 정합성 자동 점검"
        ),
        "outcome": "다중 시스템 입력 축소 + 기준정보 정합성 제고 + HR 마스터 데이터 관리 효율화",
        "implication": "**단일 Orchestration 으로 다중 시스템 통합 입력** 이 기준정보 정합성의 핵심",
    },
    (5, "IBM"): {
        "ai_adoption_goal": "AI 기반 급여·휴가·보상 후속처리 (후행 업무 자동화, 처리 정확성 강화)",
        "ai_technology": "Watsonx Orchestrate · 자동 일정 Workflow · 오류 감지·자동 보정",
        "key_data": "급여 데이터 · 휴가·근태 이력 · 보상 정책 · 복리후생 사용 이력",
        "adoption_method": "자동 일정 업무 Workflow (트리거: 월급여 마감 5일 전 등)",
        "use_case": (
            "트리거 (예: 월급여 마감 5일 전) → Workflow 실행 (이번달 인사 변경·휴직·승진·전배 "
            "이벤트 리스트 조회 → 각 이벤트별 후속업무 진행). 급여·정산 영향 식별 / 오류 자동 "
            "감지·보정 / 정산 마감 처리"
        ),
        "outcome": "후행 업무 자동화 + 처리 정확성 강화 + 정산 마감 리드타임 단축",
        "implication": "**트리거 기반 자동 일정 Workflow** + **오류 자동 감지·보정** 이 정산 운영 안정성의 핵심",
    },
}


# ═══════════════════════════════════════════════════════════════════
# 5) Helpers — 다른 도메인과 동일 시그니처
# ═══════════════════════════════════════════════════════════════════

def build_background_benchmark_rows(filter_l2: list[str] | None = None) -> list[dict]:
    filter_set = {str(n).strip() for n in filter_l2} if filter_l2 else None
    rows: list[dict] = []
    for case in BP_CASES:
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
                "benchmark_domain": "bp",
            })
    return rows


def get_background_cases_for_tasks(tasks) -> list[BPCase]:
    if not tasks:
        return []
    l2_names = {getattr(t, "l2", "") or "" for t in tasks}
    l2_set = {n for n in l2_names if n}
    if not l2_set:
        return []
    return [c for c in BP_CASES if any(l2 in l2_set for l2 in c["applicable_l2"])]


def get_background_cases_by_l2(l2_names: list[str]) -> list[BPCase]:
    if not l2_names:
        return []
    l2_set = {str(n).strip() for n in l2_names if n}
    return [c for c in BP_CASES if any(l2 in l2_set for l2 in c["applicable_l2"])]


def match_benchmark_for_task(task_name: str) -> BPCase | None:
    if not task_name:
        return None
    tn = task_name.lower()
    for case in BP_CASES:
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
    lines = ["## 🏛 Background BM — Player 개요 (Doosan HR 큐레이션 · BP 도메인)"]
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
        "## 💡 Background BM — 통합 시사점 (BP 도메인)\n"
        f"**Headline**: {ii['headline']}\n\n"
        f"**핵심 Summary**: {ii['summary']}\n\n"
        f"**AI 기반 프로세스 원칙**: {ii['ai_process_principle']}\n\n"
        f"**AI 적용 방식 원칙**: {ii['ai_application_principle']}\n\n"
        f"**Value Chain**: {ii['value_chain']}\n"
    )


def get_applicable_players_for_tasks(tasks) -> list[PlayerProfile]:
    """BP 도메인 L2 가 매칭되면 2 사 프로필 전체 반환, 아니면 빈 리스트."""
    applicable_cases = get_background_cases_for_tasks(tasks)
    if not applicable_cases:
        return []
    return list(BP_PLAYERS)
