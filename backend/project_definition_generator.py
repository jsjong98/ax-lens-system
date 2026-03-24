"""
project_definition_generator.py — 과제 정의서 자동 생성기

분류 결과 + To-Be Workflow 결과를 기반으로
과제 정의서를 LLM(Claude)으로 생성합니다.

과제 정의서 구조:
  헤더: 과제번호/이름, 작성일, 작성자
  1. 과제 개요 (주요 과제 내용) — bullet 리스트
  2. 매핑 프로세스 (To-Be 기준) — No./프로세스 + Task ID 범위 설명
  3. 이해관계자
  4. 현황 및 문제점 vs. 개선 방향
  5. 기대 효과 — 정량적(계산식 포함) + 정성적
  6. 과제 추진 시 고려사항
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any


# ── 데이터 모델 ───────────────────────────────────────────────────────────────

@dataclass
class MappingProcess:
    """매핑 프로세스 항목."""
    no: str               # 프로세스 번호 (예: "1.2.3")
    process_name: str      # 프로세스명
    task_range: str = ""   # Task ID 범위 설명 (예: "1.1.1.4 ~ 1.1.1.7 '사내강사 제도 > 외부 벤치마킹' 영역")


@dataclass
class Stakeholder:
    """이해관계자."""
    project_owner: str = ""         # 과제 오너 (이름 + 직급)
    owner_department: str = ""      # 주관 부서
    collaborating_departments: list[str] = field(default_factory=list)
    external_partners: list[str] = field(default_factory=list)


@dataclass
class CurrentVsImprovement:
    """현황 및 문제점 vs. 개선 방향."""
    current_issues: list[str] = field(default_factory=list)
    improvement_directions: list[str] = field(default_factory=list)


@dataclass
class ExpectedEffect:
    """기대 효과."""
    quantitative: list[str] = field(default_factory=list)   # 계산식 포함 (예: "연간 약 336시간 절감 = ...")
    qualitative: list[str] = field(default_factory=list)


@dataclass
class ProjectDefinition:
    """과제 정의서 전체."""
    project_number: str = ""        # 과제 번호 (예: "5")
    project_title: str = ""         # 과제명
    created_date: str = ""          # 작성일
    author: str = ""                # 작성자
    overview: list[str] = field(default_factory=list)   # 과제 개요 (bullet 리스트)
    mapping_processes: list[MappingProcess] = field(default_factory=list)
    stakeholder: Stakeholder = field(default_factory=Stakeholder)
    current_vs_improvement: CurrentVsImprovement = field(default_factory=CurrentVsImprovement)
    expected_effects: ExpectedEffect = field(default_factory=ExpectedEffect)
    considerations: list[str] = field(default_factory=list)


def project_definition_to_dict(pd: ProjectDefinition) -> dict:
    """ProjectDefinition → JSON-serializable dict."""
    return {
        "project_number": pd.project_number,
        "project_title": pd.project_title,
        "created_date": pd.created_date,
        "author": pd.author,
        "overview": pd.overview,
        "mapping_processes": [
            {"no": mp.no, "process_name": mp.process_name, "task_range": mp.task_range}
            for mp in pd.mapping_processes
        ],
        "stakeholder": {
            "project_owner": pd.stakeholder.project_owner,
            "owner_department": pd.stakeholder.owner_department,
            "collaborating_departments": pd.stakeholder.collaborating_departments,
            "external_partners": pd.stakeholder.external_partners,
        },
        "current_vs_improvement": {
            "current_issues": pd.current_vs_improvement.current_issues,
            "improvement_directions": pd.current_vs_improvement.improvement_directions,
        },
        "expected_effects": {
            "quantitative": pd.expected_effects.quantitative,
            "qualitative": pd.expected_effects.qualitative,
        },
        "considerations": pd.considerations,
    }


# ── LLM 프롬프트 ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """당신은 PwC의 HR 디지털 전환 컨설턴트입니다.
AI 업무 자동화 분류 결과와 To-Be Workflow 설계 결과를 바탕으로
과제 정의서를 작성합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【사고 과정】 — 반드시 아래 순서로 단계별로 사고한 뒤 결론을 내리세요
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step A. 데이터 분석
  — 분류 결과(AI, AI+Human, Human)의 분포를 파악합니다.
  — To-Be Workflow의 Agent 구성을 파악합니다.
  — 어떤 L3/L4 프로세스에 AI 자동화가 가장 크게 적용되는지 확인합니다.

Step B. 과제 정의서 작성
  — 과제 개요는 bullet 리스트로, 핵심 내용을 2~3개로 요약합니다.
  — 현황 및 문제점은 실제 Pain Point를 구체적으로 기술하되 가능하면 As-Is 소요 시간을 추정합니다.
  — 개선 방향은 AI가 구체적으로 어떻게 해결하는지 작성합니다.
  — 기대 효과의 정량적 효과는 반드시 계산식을 포함합니다.
    예: "연간 약 336시간 절감 = (16시간(as-is) - 2시간(to-be)) × 24건"
  — 과제 추진 시 고려사항은 실질적 실행 이슈를 포함합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【출력 형식】 — 반드시 아래 JSON 형식만 출력하세요 (마크다운 코드블록 허용)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```json
{
  "project_number": "과제 번호 (예: 1, 2, 3...)",
  "project_title": "과제명 (예: 외부 HRD 트렌드 모니터링 및 벤치마킹 자동화)",
  "overview": [
    "핵심 내용 1 — AI가 무엇을 자동화하는지",
    "핵심 내용 2 — 어떤 업무 사이클이 개선되는지"
  ],
  "mapping_processes": [
    {
      "no": "1.2.3",
      "process_name": "프로세스명",
      "task_range": "1.1.1.4 ~ 1.1.1.7 '해당 영역' 설명"
    }
  ],
  "stakeholder": {
    "project_owner": "(추론한 역할명 + 직급)",
    "owner_department": "주관 부서",
    "collaborating_departments": ["협업 부서1"],
    "external_partners": ["외부 파트너1 또는 없음"]
  },
  "current_vs_improvement": {
    "current_issues": [
      "구체적 현황 및 문제점 — 가능하면 소요 시간/빈도 포함",
      "예: 외부 HRD 트렌드를 담당자가 비정기적으로 수동 검색·수집 (월 4~8시간)"
    ],
    "improvement_directions": [
      "AI가 구체적으로 어떻게 개선하는지",
      "예: AI가 주요 외부자료를 크롤링·요약하여 주간 트렌드 브리핑 자동 생성"
    ]
  },
  "expected_effects": {
    "quantitative": [
      "계산식 포함 (예: 연간 약 336시간 절감 = (16시간(as-is) - 2시간(to-be)) × 24건)"
    ],
    "qualitative": [
      "정성적 효과 (예: 트렌드 모니터링 상시화 → 시장 변화 대응 속도 향상)"
    ]
  },
  "considerations": [
    "실질적 고려사항 (예: 크롤링 대상 매체·소스 리스트의 초기 큐레이션 및 정기 업데이트 체계)"
  ]
}
```

【주의사항】
- mapping_processes의 no는 실제 L3/L4 ID를 사용하세요.
- task_range에는 해당 프로세스에 속하는 L5 Task ID 범위와 영역 설명을 작성하세요.
- 이해관계자 정보는 업무 특성에서 추론하세요. 없으면 "없음"으로 기재합니다.
- 현황 문제점은 3~5개, 개선 방향도 3~5개 이상 작성하세요.
- 기대 효과 정량적은 반드시 계산식(As-Is 시간 - To-Be 시간 × 횟수) 포함하세요.
- 기대 효과는 정량 2~4개, 정성 2~4개 이상 작성하세요.
- 고려사항은 3~5개 이상 작성하세요.
- 전체 Task 대비 AI 자동화 비율 등 수치를 적극 활용하세요.
"""


def _build_user_prompt(
    tasks: list[dict],
    classification_results: dict[str, dict],
    tobe_data: dict | None,
    process_name: str,
) -> str:
    """LLM에 전달할 사용자 프롬프트를 구성합니다."""
    lines: list[str] = []
    lines.append(f"# 프로세스: {process_name}\n")

    # 분류 통계
    total = len(classification_results)
    ai_count = sum(1 for r in classification_results.values() if r.get("label") == "AI")
    hybrid_count = sum(1 for r in classification_results.values() if r.get("label") == "AI + Human")
    human_count = sum(1 for r in classification_results.values() if r.get("label") == "Human")

    lines.append("## 분류 결과 통계")
    lines.append(f"- 전체 Task: {total}개")
    if total:
        lines.append(f"- AI: {ai_count}개 ({ai_count/total*100:.1f}%)")
        lines.append(f"- AI + Human: {hybrid_count}개 ({hybrid_count/total*100:.1f}%)")
        lines.append(f"- Human: {human_count}개 ({human_count/total*100:.1f}%)")
    lines.append("")

    # L3/L4 구조 파악
    l3_groups: dict[str, list[str]] = {}
    for t in tasks:
        l3_key = f"{t.get('l3_id', '')} {t.get('l3', '')}"
        l4_key = f"{t.get('l4_id', '')} {t.get('l4', '')}"
        if l3_key not in l3_groups:
            l3_groups[l3_key] = []
        if l4_key not in l3_groups[l3_key]:
            l3_groups[l3_key].append(l4_key)

    lines.append("## 프로세스 계층 구조")
    for l3, l4s in l3_groups.items():
        lines.append(f"- L3: {l3}")
        for l4 in l4s:
            lines.append(f"  - L4: {l4}")
    lines.append("")

    # Task 목록 + 분류 결과
    lines.append("## L5 Task 목록 및 분류 결과")
    for t in tasks:
        tid = t.get("id", "")
        cr = classification_results.get(tid, {})
        label = cr.get("label", "미분류")
        reason = cr.get("reason", "")
        l3 = t.get("l3", "")
        l4 = t.get("l4", "")
        name = t.get("name", "")
        description = t.get("description", "")
        performer = t.get("performer", "")

        pain_points = []
        for key in ["pain_time", "pain_accuracy", "pain_repetition", "pain_data",
                     "pain_system", "pain_communication", "pain_other"]:
            val = t.get(key, "")
            if val and val.strip():
                pain_points.append(val.strip())

        lines.append(f"- [{tid}] L3={l3} | L4={l4} | {name}")
        if description:
            lines.append(f"  설명: {description}")
        if performer:
            lines.append(f"  수행주체: {performer}")
        lines.append(f"  분류: {label} | 사유: {reason}")
        if pain_points:
            lines.append(f"  Pain Points: {', '.join(pain_points)}")
        ai_prereq = cr.get("ai_prerequisites", "")
        if ai_prereq:
            lines.append(f"  AI 수행 여건: {ai_prereq}")
    lines.append("")

    # To-Be Workflow 정보 (있으면)
    if tobe_data:
        lines.append("## To-Be Workflow 설계 결과")
        summary = tobe_data.get("summary", {})
        if isinstance(summary, dict) and summary:
            lines.append(f"- 요약: {json.dumps(summary, ensure_ascii=False)}")
        elif isinstance(summary, str) and summary:
            lines.append(f"- 요약: {summary}")

        # New Workflow 형식: agents
        agents = tobe_data.get("agents", [])
        if agents:
            lines.append(f"- AI Agent 수: {len(agents)}개")
            for agent in agents:
                agent_name = agent.get("agent_name", "")
                technique = agent.get("ai_technique", agent.get("technique", ""))
                desc = agent.get("description", "")
                task_count = agent.get("task_count", len(agent.get("assigned_tasks", agent.get("tasks", []))))
                lines.append(f"  · {agent_name} (기법: {technique}, Task {task_count}개): {desc}")

        # execution_steps or execution_flow
        exec_steps = tobe_data.get("execution_steps", tobe_data.get("execution_flow", []))
        if exec_steps:
            lines.append("- 실행 단계:")
            for step in exec_steps:
                step_label = step.get("label", step.get("step_name", ""))
                step_type = step.get("type", step.get("step_type", ""))
                desc = step.get("description", "")
                lines.append(f"  · {step_label} ({step_type}): {desc}")

        blueprint = tobe_data.get("blueprint_summary", "")
        if blueprint:
            lines.append(f"- 블루프린트: {blueprint}")

        lines.append("")

    return "\n".join(lines)


def _parse_llm_response(text: str) -> dict:
    """LLM 응답에서 JSON을 추출합니다."""
    # 마크다운 코드블록 제거
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()

    # JSON 객체 추출
    brace_start = text.find("{")
    if brace_start == -1:
        raise ValueError("JSON 응답을 찾을 수 없습니다.")

    depth = 0
    for i in range(brace_start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[brace_start:i + 1])

    return json.loads(text[brace_start:])


def _dict_to_project_definition(data: dict, author: str = "", created_date: str = "") -> ProjectDefinition:
    """JSON dict → ProjectDefinition 변환."""
    stakeholder_data = data.get("stakeholder", {})
    cvi_data = data.get("current_vs_improvement", {})
    effects_data = data.get("expected_effects", {})

    # overview가 문자열이면 리스트로 변환
    overview_raw = data.get("overview", [])
    if isinstance(overview_raw, str):
        overview_raw = [line.strip() for line in overview_raw.split("\n") if line.strip()]

    return ProjectDefinition(
        project_number=str(data.get("project_number", "")),
        project_title=data.get("project_title", ""),
        created_date=created_date or data.get("created_date", date.today().strftime("%Y.%m.%d")),
        author=author or data.get("author", ""),
        overview=overview_raw,
        mapping_processes=[
            MappingProcess(
                no=mp.get("no", ""),
                process_name=mp.get("process_name", ""),
                task_range=mp.get("task_range", ""),
            )
            for mp in data.get("mapping_processes", [])
        ],
        stakeholder=Stakeholder(
            project_owner=stakeholder_data.get("project_owner", ""),
            owner_department=stakeholder_data.get("owner_department", ""),
            collaborating_departments=stakeholder_data.get("collaborating_departments", []),
            external_partners=stakeholder_data.get("external_partners", []),
        ),
        current_vs_improvement=CurrentVsImprovement(
            current_issues=cvi_data.get("current_issues", []),
            improvement_directions=cvi_data.get("improvement_directions", []),
        ),
        expected_effects=ExpectedEffect(
            quantitative=effects_data.get("quantitative", []),
            qualitative=effects_data.get("qualitative", []),
        ),
        considerations=data.get("considerations", []),
    )


# ── LLM 호출 ─────────────────────────────────────────────────────────────────

async def generate_project_definition_with_llm(
    tasks: list[dict],
    classification_results: dict[str, dict],
    tobe_data: dict | None = None,
    process_name: str = "HR 프로세스",
    api_key: str = "",
    model: str = "claude-sonnet-4-6",
    author: str = "",
) -> ProjectDefinition:
    """Claude LLM을 사용하여 과제 정의서를 생성합니다."""
    import anthropic

    api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("Anthropic API 키가 설정되지 않았습니다.")

    user_prompt = _build_user_prompt(tasks, classification_results, tobe_data, process_name)

    client = anthropic.AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.3,
    )

    text = response.content[0].text
    parsed = _parse_llm_response(text)
    return _dict_to_project_definition(parsed, author=author)


# ── Fallback: 규칙 기반 생성 ──────────────────────────────────────────────────

def generate_project_definition_fallback(
    tasks: list[dict],
    classification_results: dict[str, dict],
    tobe_data: dict | None = None,
    process_name: str = "HR 프로세스",
    author: str = "",
) -> ProjectDefinition:
    """LLM 없이 규칙 기반으로 과제 정의서를 생성합니다."""
    total = len(classification_results)
    ai_count = sum(1 for r in classification_results.values() if r.get("label") == "AI")
    hybrid_count = sum(1 for r in classification_results.values() if r.get("label") == "AI + Human")
    human_count = sum(1 for r in classification_results.values() if r.get("label") == "Human")
    auto_rate = (ai_count + hybrid_count) / total * 100 if total else 0

    # 매핑 프로세스: L4 기준, Task ID 범위 포함
    l4_tasks: dict[str, list[str]] = {}
    l4_names: dict[str, str] = {}
    for t in tasks:
        l4_id = t.get("l4_id", "")
        l4_name = t.get("l4", "")
        tid = t.get("id", "")
        if l4_id:
            if l4_id not in l4_tasks:
                l4_tasks[l4_id] = []
                l4_names[l4_id] = l4_name
            l4_tasks[l4_id].append(tid)

    mapping = []
    for l4_id, tids in l4_tasks.items():
        tids_sorted = sorted(tids)
        if len(tids_sorted) > 1:
            task_range = f"{tids_sorted[0]} ~ {tids_sorted[-1]} '{l4_names[l4_id]}' 영역"
        else:
            task_range = f"{tids_sorted[0]} '{l4_names[l4_id]}' 영역"
        mapping.append(MappingProcess(no=l4_id, process_name=l4_names[l4_id], task_range=task_range))

    return ProjectDefinition(
        project_number="1",
        project_title=f"{process_name} AI 자동화 과제",
        created_date=date.today().strftime("%Y.%m.%d"),
        author=author or "PwC",
        overview=[
            f"{process_name} 프로세스의 L5 Task {total}개 중 AI {ai_count}개, AI+Human {hybrid_count}개를 자동화 (Human {human_count}개)",
            f"전체 자동화 가능 비율 {auto_rate:.1f}% 달성을 위한 AI 기반 워크플로우 구축",
        ],
        mapping_processes=mapping,
        stakeholder=Stakeholder(
            project_owner="(지정 필요)",
            owner_department="인사팀",
            collaborating_departments=["IT팀", "디지털혁신팀"],
            external_partners=["AI 솔루션 벤더"],
        ),
        current_vs_improvement=CurrentVsImprovement(
            current_issues=[
                "수작업 기반의 반복적 데이터 처리로 인한 비효율",
                "담당자별 업무 처리 편차로 인한 품질 불균일",
                "대량 데이터 처리 시 소요 시간 과다",
            ],
            improvement_directions=[
                f"AI 자동화를 통한 {ai_count}개 Task 완전 자동 처리",
                f"AI+Human 협업 체계로 {hybrid_count}개 Task 효율화",
                "AI Agent 아키텍처 기반 지능형 워크플로우 구축",
            ],
        ),
        expected_effects=ExpectedEffect(
            quantitative=[
                f"업무 자동화율 {auto_rate:.1f}% 달성",
                "반복 업무 처리 시간 단축 (구체적 수치는 프로세스별 산정 필요)",
            ],
            qualitative=[
                "업무 품질 균일성 확보",
                "담당자 고부가가치 업무 집중 가능",
            ],
        ),
        considerations=[
            "기존 시스템과의 데이터 연동 방안 수립 필요",
            "AI 모델 학습을 위한 데이터 품질 확보",
            "임직원 변화관리 및 교육 계획 수립",
        ],
    )
