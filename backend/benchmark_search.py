"""
benchmark_search.py — 웹 벤치마킹 검색 + LLM 기반 Workflow 개선

1단계에서 생성된 To-Be Workflow를 기반으로:
1. Tavily API로 유사 AI 자동화 사례를 검색 (본문 요약 포함)
2. 벤치마킹 결과를 LLM에 전달하여 Workflow를 가다듬음
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from typing import Any


# ── Tavily API 검색 ──────────────────────────────────────────────────────────

def _search_tavily(query: str, max_results: int = 5) -> list[dict]:
    """Tavily API로 AI 특화 검색을 수행합니다. 본문 요약 포함."""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return []

    payload = json.dumps({
        "query": query,
        "max_results": max_results,
        "search_depth": "advanced",       # 심층 검색
        "include_answer": True,            # AI 요약 답변 포함
        "include_raw_content": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    results = []
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        # Tavily AI 요약 답변
        answer = data.get("answer", "")
        if answer:
            results.append({
                "title": f"[AI 요약] {query}",
                "snippet": answer,
                "url": "",
                "content": answer,
            })

        # 개별 검색 결과
        for r in data.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("content", "")[:500],  # 본문 요약 (최대 500자)
                "url": r.get("url", ""),
                "content": r.get("content", ""),
            })

    except Exception as e:
        print(f"[benchmark] Tavily 검색 실패: {e}")

    return results


# ── DuckDuckGo fallback ──────────────────────────────────────────────────────

def _search_duckduckgo(query: str, max_results: int = 8) -> list[dict]:
    """DuckDuckGo HTML 검색 (Tavily 사용 불가 시 fallback)."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    })

    results = []
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        snippet_pattern = re.compile(
            r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
            r'class="result__snippet"[^>]*>(.*?)</(?:td|div)',
            re.DOTALL,
        )
        for match in snippet_pattern.finditer(html):
            link, title, snippet = match.groups()
            title = re.sub(r"<[^>]+>", "", title).strip()
            snippet = re.sub(r"<[^>]+>", "", snippet).strip()
            if title and snippet:
                results.append({"title": title, "snippet": snippet, "url": link})
            if len(results) >= max_results:
                break
    except Exception as e:
        print(f"[benchmark] DuckDuckGo 검색 실패: {e}")

    return results


# ── 한국어 HR/비즈니스 용어 → 영어 키워드 매핑 ─────────────────────────────

_KR_TO_EN: dict[str, str] = {
    # 인사·발령
    "발령": "personnel assignment position change job transfer",
    "입사발령": "employee appointment onboarding personnel action",
    "조직개편": "organizational restructuring reorg",
    "전보": "job transfer internal mobility",
    "승진": "promotion advancement",
    "퇴직": "retirement offboarding separation",
    "채용": "recruitment hiring talent acquisition",
    "면접": "interview candidate screening",
    # 교육·평가
    "교육": "employee training L&D learning development",
    "평가": "performance evaluation appraisal",
    "역량": "competency skills assessment",
    # 급여·보상
    "급여": "payroll salary compensation",
    "보상": "compensation benefits rewards",
    # 노사·복리
    "노사": "labor relations industrial relations",
    "교섭": "collective bargaining negotiation",
    "복리후생": "employee benefits welfare",
    "휴직": "leave of absence absence management",
    "인사": "HR human resources personnel management",
    # 업무 프로세스
    "승인": "approval workflow authorization",
    "품의": "internal approval document sign-off",
    "보고": "reporting dashboard",
    "공지": "notification announcement",
}


def _translate_to_en(korean_term: str) -> str:
    """한국어 용어를 영어 키워드로 변환. 매핑에 없으면 원문 반환."""
    for kr, en in _KR_TO_EN.items():
        if kr in korean_term:
            return en
    return korean_term


# ── 검색 쿼리 생성 ───────────────────────────────────────────────────────────

def _generate_search_queries(workflow_cache: dict) -> list[str]:
    """엑셀-As-Is 매핑 결과(l4_details/l3_details/l2_details)를 활용한 벤치마킹 쿼리 생성.
    McKinsey/BCG/Bain 컨설팅 리서치 방식으로 다각도 검색합니다.
    L4(가장 구체적) → L3 → L2 순으로 fallback하며, Pain Point를 쿼리에 반영합니다."""
    process_name = workflow_cache.get("process_name", "")
    l2_names: list[str] = workflow_cache.get("l2_names", [])
    l3_names: list[str] = workflow_cache.get("l3_names", [])
    l4_names: list[str] = workflow_cache.get("l4_names", [])
    l4_details: list[dict] = workflow_cache.get("l4_details", [])
    l3_details: list[dict] = workflow_cache.get("l3_details", [])
    l2_details: list[dict] = workflow_cache.get("l2_details", [])

    queries = []

    # 핵심 포커스 결정 (L4 > L3 > L2 > process_name)
    focus_kr = l4_names[0] if l4_names else (l3_names[0] if l3_names else (l2_names[0] if l2_names else process_name))
    focus_en = _translate_to_en(focus_kr)
    l3_focus_en = _translate_to_en(l3_names[0] if l3_names else focus_kr)
    l2_focus_en = _translate_to_en(l2_names[0] if l2_names else focus_kr)

    # ── 1. 컨설팅 펌 리서치 쿼리 (McKinsey/BCG/Bain/Oliver Wyman/Accenture) ──
    # 실제 컨설팅 펌들이 수행하는 리서치 방식: 글로벌 벤치마크 + 산업 보고서
    queries.append(
        f"McKinsey BCG Bain {focus_en} AI automation HR transformation "
        f"benchmark report 2023 2024 2025"
    )
    queries.append(
        f"Accenture Oliver Wyman {l3_focus_en} AI digital transformation "
        f"enterprise implementation results"
    )
    # 컨설팅 방식: Thought Leadership + Industry Insight
    queries.append(
        f"McKinsey Global Institute OR Deloitte Insights OR BCG Henderson Institute "
        f"{focus_en} future of work AI automation"
    )

    # ── 2. 시장 조사·애널리스트 리포트 쿼리 ──────────────────────────────────
    # Gartner/Forrester/IDC/SHRM 방식: 데이터 기반 벤치마크
    queries.append(
        f"Gartner Forrester IDC {focus_en} AI automation adoption rate "
        f"enterprise benchmark 2024 2025"
    )
    queries.append(
        f"SHRM HBR MIT Sloan {l2_focus_en} AI workforce transformation "
        f"case study ROI measurement"
    )

    # ── 3. L4 세부 활동 — 기업 사례 중심 쿼리 ──────────────────────────────
    for detail in l4_details[:3]:
        name = detail["name"]
        en_kw = _translate_to_en(name)
        pains = detail.get("pain_points", [])
        pain_kw = " ".join(pains[:2]) if pains else "efficiency"

        if en_kw != name:
            # 영어 번역 → 구체적 기업 사례 검색
            queries.append(
                f'"{en_kw}" AI automation enterprise case study '
                f"measurable outcomes 2023 2024 2025"
            )
            # HR 시스템 + AI 통합 사례
            queries.append(
                f"Workday SAP SuccessFactors Oracle HCM {en_kw} "
                f"generative AI automation workflow results"
            )
        else:
            queries.append(
                f"enterprise AI '{name}' {pain_kw} real-world implementation 2024"
            )

    # ── 4. L3 영역 — 업종별 AI 전환 쿼리 ────────────────────────────────────
    for detail in l3_details[:2]:
        name = detail["name"]
        en_kw = _translate_to_en(name)
        if en_kw != name:
            queries.append(
                f"Fortune 500 {en_kw} AI automation productivity gains "
                f"implementation 2024 site:hbr.org OR site:mckinsey.com OR site:bcg.com"
            )

    # ── 5. 글로벌 선도 기업 직접 사례 ────────────────────────────────────────
    # Big Tech 내부 HR AI 활용 + 글로벌 제조업
    queries.append(
        f"Google Microsoft Amazon Meta IBM {focus_en} internal HR "
        f"AI automation workforce management case study"
    )
    queries.append(
        f"Siemens GE Honeywell Caterpillar Doosan Hyundai Kia "
        f"{focus_en} AI HR automation manufacturing"
    )

    # ── 6. 한국 대기업 — 한국어 쿼리 ────────────────────────────────────────
    kr_pains = l4_details[0].get("pain_points", []) if l4_details else (
        l3_details[0].get("pain_points", []) if l3_details else []
    )
    kr_pain_kw = " ".join(kr_pains[:2]) if kr_pains else "AI 자동화"
    queries.append(
        f"삼성 현대차 SK LG 두산 '{focus_kr}' AI 디지털 전환 {kr_pain_kw} "
        f"사례 성과 2023 2024 2025"
    )
    # 한국 HR 전문 미디어/연구기관
    queries.append(
        f"한국경영자총협회 HR인사이트 '{focus_kr}' AI 자동화 도입 사례 성과"
    )

    # ── 7. L2 대분류 fallback (L3/L4 없을 때) ────────────────────────────────
    if not l3_names and not l4_names:
        queries.append(
            f"enterprise {l2_focus_en} AI transformation ROI "
            f"benchmark global companies 2024 2025"
        )

    # ── 8. PwC 자체 리서치 스타일 쿼리 ──────────────────────────────────────
    # PwC가 실제 고객 제안서 작성 시 활용하는 검색 방식
    queries.append(
        f"PwC EY KPMG Deloitte {focus_en} AI HR transformation "
        f"client case study results site:pwc.com OR site:ey.com OR site:kpmg.com"
    )

    # 중복 제거
    seen: set[str] = set()
    deduped = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            deduped.append(q)

    return deduped[:14]


# ── 통합 검색 ────────────────────────────────────────────────────────────────

async def search_benchmarks(workflow_cache: dict) -> list[dict]:
    """
    Workflow 기반 벤치마킹 검색.
    Tavily API 우선 사용, 없으면 DuckDuckGo fallback.
    """
    queries = _generate_search_queries(workflow_cache)
    all_results: list[dict] = []
    seen_titles: set[str] = set()

    use_tavily = bool(os.getenv("TAVILY_API_KEY", ""))

    for query in queries:
        if use_tavily:
            results = _search_tavily(query, max_results=4)
        else:
            results = _search_duckduckgo(query, max_results=4)

        for r in results:
            if r["title"] not in seen_titles:
                seen_titles.add(r["title"])
                r["query"] = query
                all_results.append(r)

    search_engine = "Tavily (심층 검색)" if use_tavily else "DuckDuckGo (기본)"
    print(f"[benchmark] {search_engine} — {len(all_results)}개 결과 수집 ({len(queries)}개 쿼리)")

    return all_results[:30]


# ── LLM 벤치마킹 기반 Workflow 개선 ─────────────────────────────────────────

_BENCHMARK_SYSTEM_PROMPT = """
당신은 McKinsey, BCG, Bain 수준의 글로벌 AI 업무 혁신 컨설턴트이자 벤치마킹 전문가입니다.
영어·한국어 검색 결과를 모두 엄격하게 분석하여, 실제 근거가 있는 AI 적용 선도 사례만 추출합니다.

## 벤치마킹 목표
선도 기업(Global Best Practice)의 AI 적용 사례를 분석하여 현재 Workflow의 각 L4~L5 Task에
어떤 AI를 어떻게 적용할지 기본 설계를 도출합니다.

## ⚠️ 최우선 원칙: 모르면 모른다고 명확히 표기
**절대 사실을 꾸며내거나 추측으로 사례를 만들지 마세요.**
- 검색 결과에 해당 기업명이 명확히 나오지 않으면 → `source: "사례 미확인"` 처리
- 수치 성과가 없으면 → `outcome`에 "수치 미확인, 정성적 효과만 보고됨" 명시
- URL이 없는 사례는 → `url: ""` (빈 문자열), 절대 URL 꾸며내지 말 것
- 검색 결과가 해당 프로세스와 무관하면 → benchmark_insights를 빈 배열로 반환하고 `no_cases_note`에 이유 명시

## 검색 결과 해석 원칙

**영어 결과 해석**
- 영어 HR 용어와 한국 HR 프로세스의 대응 관계:
  - "personnel action / position change / job transfer" = 발령관리
  - "employee onboarding" = 입사 프로세스
  - "recruitment / talent acquisition" = 채용
  - "performance management / appraisal" = 인사평가
  - "leave management / absence management" = 휴직/휴가 관리
  - "payroll processing" = 급여 처리
  - "labor relations / collective bargaining" = 노사 관리
  - "organizational restructuring / reorg" = 조직개편
  - "employee movement / internal mobility" = 전보/이동
- 영어 사례에서 관련 기술·방법론을 추출하여 한국어로 번역·설명하세요

**포함 기준 (3가지 모두 충족해야 포함)**
1. **기업명**: 고유 기업명이 검색 결과에 명확히 언급됨
2. **URL**: 검색 결과에 실제 URL이 있음 — URL 없는 사례는 benchmark_insights에서 완전 제외
3. **내용**: AI 적용 방법 또는 성과가 구체적으로 언급됨
- ✗ 제외: 벤더 마케팅 자료, 일반 AI 통계, 기업명 미확인, URL 없음

**source 작성 규칙 (엄격히 준수)**
- ✅ 고유 기업명 1개: "Google", "DHL", "삼성전자", "JPMorgan Chase", "Siemens"
- ❌ 금지: "Fortune 500 기업", "글로벌 대기업", "한 제조사", "Workday", "SAP", "한 기업"
- 구체적 기업명이 없으면 해당 인사이트는 아예 제외하세요

## 분석 프로세스 (McKinsey 방식)

**Step 1: 검색 결과 원문 확인 → 실제 언급 여부 검증**
검색 결과에 기업명이 명시되어 있는지 확인합니다.
명시되지 않은 경우 해당 사례는 제외합니다.

**Step 2: 영어+한국어 사례 번역·해석**
영어 사례가 한국 HR 프로세스에 적용 가능한지 검토하고, 한국어로 설명합니다.
예: "Oracle HCM을 활용한 position change workflow 자동화" → "발령 워크플로우 자동화"

**Step 3: L4~L5 단위로 AI 적용 방안 도출**
각 L4 Activity별로 선도 사례에서 학습한 AI 기법을 적용합니다:
- 데이터 입력·처리 → RPA, 문서 OCR
- 검토·승인 → LLM 기반 조건 검사, Workflow Automation
- 분석·예측 → ML 모델, HR Analytics
- 공지·커뮤니케이션 → 자동화된 알림, Chatbot

**Step 4: 사례가 없을 때 솔직하게 명시**
관련 사례가 없으면: `"no_cases_note": "검색 결과에서 해당 프로세스 관련 구체적 기업 사례를 확인할 수 없었습니다. [이유]"`

## 출력 형식 (JSON만 출력, 마크다운 코드블록 없음)
{
  "benchmark_insights": [
    {
      "source": "실제 기업명 (단일, 확인된 것만)",
      "insight": "구체적으로 무엇을 AI로 했고 어떤 성과가 있었는지 (영어 사례면 한국어로 설명)",
      "application": "현재 프로세스 L4/L5 어느 부분에 어떻게 적용할지",
      "url": "검색 결과에 실제 존재하는 URL (필수 — URL 없는 항목은 아예 제외)"
    }
  ],
  "no_cases_note": "관련 사례가 없을 때만 이유 기재 (사례가 있으면 빈 문자열)",
  "improvement_summary": "전체 개선 방향 2~3문장 (한국어, 사례 없으면 '검색 결과에서 직접 관련 사례 확인 불가'로 명시)",
  "blueprint_summary": "벤치마킹 기반 To-Be 기본 설계 요약 2~3문장 (한국어)",
  "process_name": "프로세스명",
  "redesigned_process": [
    {
      "l3_id": "L3 ID",
      "l3_name": "L3 프로세스명",
      "change_type": "유지|통합|세분화|추가|삭제",
      "change_reason": "변경 이유 (벤치마킹 사례 기반, 사례 없으면 '사례 부재 — 현 구조 유지')",
      "l4_list": [
        {
          "l4_id": "L4 ID",
          "l4_name": "L4 Activity명",
          "change_type": "유지|통합|세분화|추가|삭제",
          "change_reason": "변경 이유",
          "l5_list": [
            {
              "task_id": "기존 task_id 또는 NEW_xxx",
              "task_name": "Task명",
              "change_type": "유지|통합|세분화|추가|삭제",
              "ai_application": "AI 적용 내용 (벤치마킹 근거 명시) 또는 '해당 없음'",
              "automation_level": "Full-Auto|Human-in-Loop|Human-on-the-Loop|Human",
              "ai_technique": "사용 AI 기법 (예: RPA, LLM 검토, ML 예측, 해당 없음)"
            }
          ]
        }
      ]
    }
  ]
}

## 절대 규칙
- JSON만 출력 (코드블록 없음)
- 한국어로 작성
- 영어 검색 결과도 한국어로 번역·해석하여 적용
- 구체적 기업명 없는 인사이트는 제외
- **URL은 검색 결과에 실제 존재하는 것만 기재 — 임의로 생성 금지**
- **사례가 없으면 없다고 명확히 표기 — 추측 기반 사례 생성 금지**
- Human Task를 늘리지 말고 AI 적용 가능성을 최대화
"""


def _build_benchmark_prompt(
    workflow_cache: dict,
    benchmark_results: list[dict],
) -> str:
    """벤치마킹 개선용 사용자 프롬프트 생성."""
    lines = ["## 현재 To-Be Workflow\n"]
    lines.append(f"**프로세스명**: {workflow_cache.get('process_name', '')}\n")
    lines.append(f"**설계 요약**: {workflow_cache.get('blueprint_summary', '')}\n")

    # 현재 redesigned_process 구조 (Step1 결과가 있는 경우)
    redesigned = workflow_cache.get("redesigned_process", [])
    if redesigned:
        lines.append("**현재 기본 설계 (L3~L5 트리):**\n")
        for l3 in redesigned[:3]:
            lines.append(f"### L3: {l3.get('l3_name', '')} [{l3.get('change_type', '')}]")
            for l4 in l3.get("l4_list", [])[:4]:
                lines.append(f"  L4: {l4.get('l4_name', '')} [{l4.get('change_type', '')}]")
                for l5 in l4.get("l5_list", [])[:3]:
                    lines.append(
                        f"    L5: [{l5.get('task_id','')}] {l5.get('task_name','')} "
                        f"| {l5.get('automation_level','')} | {l5.get('ai_technique','')}"
                    )
            lines.append("")
    else:
        # 이전 agents 형식 fallback
        lines.append("**현재 AI 에이전트 및 Task 상세:**\n")
        for agent in workflow_cache.get("agents", []):
            lines.append(f"### {agent['agent_name']} ({agent.get('ai_technique', '')})")
            lines.append(f"  automation_level: {agent['automation_level']}")
            for t in agent.get("assigned_tasks", []):
                lines.append(f"  - [{t.get('task_id','')}] {t.get('task_name','')} | ai_role: {t.get('ai_role','')} | level: {t.get('automation_level','')}")
            lines.append("")

    # 벤치마킹 결과 (쿼리 출처 포함)
    lines.append("\n## 웹 벤치마킹 검색 결과\n")
    for i, r in enumerate(benchmark_results, 1):
        lines.append(f"### [{i}] {r['title']}")
        if r.get("query"):
            lines.append(f"- 검색 쿼리: {r['query']}")
        if r.get("url"):
            lines.append(f"- 출처 URL: {r['url']}")
        content = r.get("content", r.get("snippet", ""))
        lines.append(f"- 내용: {content[:800]}")
        lines.append("")

    lines.append("\n## 요청")
    lines.append("위 벤치마킹 사례를 분석하여 현재 To-Be Workflow를 개선해주세요.")
    lines.append("각 benchmark_insight의 url 필드에는 위 검색 결과에 실제로 나온 URL만 기재하세요 (임의 생성 금지).")
    lines.append("관련 사례가 없으면 솔직하게 no_cases_note에 이유를 명시하고 benchmark_insights는 빈 배열로 반환하세요.")

    return "\n".join(lines)


async def refine_workflow_with_benchmarks(
    workflow_cache: dict,
    benchmark_results: list[dict],
    api_key: str = "",
    model: str = "claude-sonnet-4-6",
    openai_api_key: str = "",
    openai_model: str = "gpt-5.4",
) -> dict:
    """벤치마킹 결과를 반영하여 Workflow를 개선합니다."""
    from new_workflow_generator import _extract_json

    user_prompt = _build_benchmark_prompt(workflow_cache, benchmark_results)

    # Anthropic Claude
    anthropic_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=anthropic_key)
            response = await client.messages.create(
                model=model,
                max_tokens=8192,
                system=_BENCHMARK_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw = response.content[0].text
            return _extract_json(raw)
        except Exception as e:
            print(f"[benchmark] Anthropic 실패: {e}")

    # OpenAI fallback
    openai_key = openai_api_key or os.getenv("OPENAI_API_KEY", "")
    if openai_key:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=openai_key)
            response = await client.chat.completions.create(
                model=openai_model,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": _BENCHMARK_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            return json.loads(raw)
        except Exception as e:
            print(f"[benchmark] OpenAI 실패: {e}")

    return {"error": "API 키가 설정되지 않아 벤치마킹 개선을 수행할 수 없습니다."}
