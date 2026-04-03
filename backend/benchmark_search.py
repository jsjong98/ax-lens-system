"""
benchmark_search.py — 웹 벤치마킹 검색 + LLM 기반 Workflow 개선

Perplexity Deep Research 방식:
1. Round 1: 8개 쿼리 병렬 검색 (전문 읽기)
2. LLM이 부족한 부분 분석 → 후속 쿼리 4개 자동 생성
3. Round 2: 후속 쿼리 병렬 검색
4. 전체 결과를 LLM에 전달하여 벤치마킹 테이블 생성
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import urllib.parse
import urllib.request
from typing import Any


# ── Tavily API 검색 ──────────────────────────────────────────────────────────

def _search_tavily(query: str, max_results: int = 5) -> list[dict]:
    """Tavily API로 AI 특화 검색을 수행합니다. 전문(raw_content) 포함."""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return []

    payload = json.dumps({
        "query": query,
        "max_results": max_results,
        "search_depth": "advanced",       # 심층 검색
        "include_answer": True,            # AI 요약 답변 포함
        "include_raw_content": True,       # 전문 포함 (핵심: snippet이 아닌 실제 기사 본문)
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
        with urllib.request.urlopen(req, timeout=20) as resp:
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

        # 개별 검색 결과 — raw_content 우선, 없으면 content
        for r in data.get("results", []):
            raw = r.get("raw_content", "") or ""
            content = r.get("content", "") or ""
            # raw_content가 있으면 더 긴 버전(최대 2500자)을 사용
            full_content = (raw[:2500] if raw else content[:2500])
            results.append({
                "title": r.get("title", ""),
                "snippet": content[:300],
                "url": r.get("url", ""),
                "content": full_content,
                "score": r.get("score", 0),
            })

    except Exception as e:
        print(f"[benchmark] Tavily 검색 실패 ({query[:40]}): {e}")

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
                results.append({"title": title, "snippet": snippet, "url": link, "content": snippet})
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


# ── Round 1: 초기 검색 쿼리 생성 ────────────────────────────────────────────

def _generate_search_queries(workflow_cache: dict) -> list[str]:
    """Round 1 검색 쿼리 생성. L4(구체적) → L3 → L2 순으로 fallback."""
    process_name = workflow_cache.get("process_name", "")
    l2_names: list[str] = workflow_cache.get("l2_names", [])
    l3_names: list[str] = workflow_cache.get("l3_names", [])
    l4_names: list[str] = workflow_cache.get("l4_names", [])
    l4_details: list[dict] = workflow_cache.get("l4_details", [])
    l3_details: list[dict] = workflow_cache.get("l3_details", [])

    queries = []

    focus_kr = l4_names[0] if l4_names else (l3_names[0] if l3_names else (l2_names[0] if l2_names else process_name))
    focus_en = _translate_to_en(focus_kr)
    l3_focus_en = _translate_to_en(l3_names[0] if l3_names else focus_kr)
    l2_focus_en = _translate_to_en(l2_names[0] if l2_names else focus_kr)

    # ── 1. 글로벌 기업 AI 도입 사례 (수치 성과 포함) ──────────────────────────
    queries.append(
        f"{focus_en} AI automation enterprise case study measurable outcomes "
        f"efficiency ROI 2023 2024 2025"
    )
    queries.append(
        f"Workday SAP SuccessFactors Oracle HCM {focus_en} generative AI "
        f"automation workflow real implementation results"
    )

    # ── 2. 시장 조사 리포트 (Gartner/Forrester/McKinsey 리포트 내 기업 사례) ──
    queries.append(
        f"Gartner Forrester {focus_en} AI adoption enterprise benchmark "
        f"2024 2025 company case study"
    )
    queries.append(
        f"McKinsey Deloitte {l2_focus_en} AI transformation "
        f"company implementation results measurable"
    )

    # ── 3. L4 세부 활동 기업 사례 ────────────────────────────────────────────
    for detail in l4_details[:2]:
        en_kw = _translate_to_en(detail["name"])
        if en_kw != detail["name"]:
            queries.append(
                f'"{en_kw}" AI automation enterprise Fortune 500 '
                f"implementation case study 2024"
            )

    # ── 4. 글로벌 선도 기업 직접 사례 ────────────────────────────────────────
    queries.append(
        f"Google Microsoft Amazon Meta IBM {focus_en} internal HR "
        f"AI automation workforce management"
    )
    queries.append(
        f"Siemens GE Unilever JPMorgan {focus_en} HR AI automation "
        f"digital transformation results"
    )

    # ── 5. 한국 대기업 ────────────────────────────────────────────────────────
    kr_pain_kw = " ".join(
        l4_details[0].get("pain_points", [])[:2]
    ) if l4_details else "AI 자동화"
    queries.append(
        f"삼성 현대 SK LG '{focus_kr}' AI 도입 사례 성과 2023 2024 2025"
    )

    # 중복 제거
    seen: set[str] = set()
    deduped = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            deduped.append(q)

    return deduped[:8]  # Round 1은 8개로 집중


# ── Round 2: LLM이 부족한 부분 파악 → 후속 쿼리 자동 생성 ──────────────────

async def _generate_followup_queries(
    workflow_cache: dict,
    round1_results: list[dict],
) -> list[str]:
    """Perplexity Deep Research 핵심 — Round 1 결과를 보고 아직 부족한 부분을
    LLM이 직접 파악하여 후속 검색 쿼리를 생성합니다."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return []

    process_name = workflow_cache.get("process_name", "")
    l4_names = workflow_cache.get("l4_names", [])

    # Round 1에서 찾은 내용 요약 (제목 + URL 유무)
    found_summary_lines = []
    for r in round1_results[:20]:
        has_url = "✓ URL있음" if r.get("url") else "✗ URL없음"
        found_summary_lines.append(f"- {has_url} | {r.get('title', '')[:80]}")

    found_summary = "\n".join(found_summary_lines)

    prompt = f"""당신은 딥 리서치 전문가입니다.

## 조사 대상 프로세스
- 프로세스명: {process_name}
- 핵심 활동(L4): {', '.join(l4_names[:6])}

## Round 1 검색에서 찾은 결과 ({len(round1_results)}건)
{found_summary}

## 지시
Round 1 결과를 보고 아직 찾지 못한 것을 파악하세요:
- 구체적 기업명 + 수치 성과가 없는 경우
- 비Tech 대기업(제조·금융·유통) HR AI 사례가 부족한 경우
- 특정 L4 활동에 대한 사례가 없는 경우

이를 보완할 후속 검색 쿼리 4개를 생성하세요.
가급적 구체적 회사명, 수치 성과, 실제 구현 사례를 찾을 수 있는 쿼리로 만드세요.

JSON만 출력: {{"queries": ["query1", "query2", "query3", "query4"], "gap_analysis": "부족한 부분 한 줄 요약"}}"""

    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",  # 빠른 모델로 쿼리만 생성
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        # JSON 추출
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            data = json.loads(m.group())
            queries = data.get("queries", [])[:4]
            gap = data.get("gap_analysis", "")
            if gap:
                print(f"[benchmark] Round 2 gap: {gap}")
            return queries
    except Exception as e:
        print(f"[benchmark] follow-up 쿼리 생성 실패: {e}")

    return []


# ── 통합 검색 (Perplexity Deep Research 방식) ────────────────────────────────

async def search_benchmarks(workflow_cache: dict) -> list[dict]:
    """
    Perplexity Deep Research 방식 벤치마킹 검색.

    Round 1: 초기 쿼리 8개 → 병렬 검색 (전문 포함)
    Round 2: LLM이 부족한 부분 분석 → 후속 쿼리 4개 자동 생성 → 병렬 검색
    """
    use_tavily = bool(os.getenv("TAVILY_API_KEY", ""))
    search_fn = _search_tavily if use_tavily else _search_duckduckgo

    # ── Round 1: 병렬 검색 ────────────────────────────────────────────────────
    queries_r1 = _generate_search_queries(workflow_cache)
    print(f"[benchmark] Round 1 시작 — {len(queries_r1)}개 쿼리 병렬 검색")

    tasks_r1 = [asyncio.to_thread(search_fn, q, 5) for q in queries_r1]
    raw_batches_r1 = await asyncio.gather(*tasks_r1, return_exceptions=True)

    all_results: list[dict] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    for query, batch in zip(queries_r1, raw_batches_r1):
        if isinstance(batch, Exception):
            print(f"[benchmark] Round 1 오류: {batch}")
            continue
        for r in batch:
            key = r.get("url") or r.get("title", "")
            if key and key not in seen_urls and r.get("title") not in seen_titles:
                seen_urls.add(key)
                seen_titles.add(r.get("title", ""))
                r["query"] = query
                r["round"] = 1
                all_results.append(r)

    print(f"[benchmark] Round 1 완료 — {len(all_results)}건 수집")

    # ── Round 2: LLM이 부족한 부분 파악 → 후속 쿼리 생성 → 병렬 검색 ─────────
    if use_tavily:  # Tavily가 있을 때만 Round 2 수행 (DuckDuckGo는 round 2 생략)
        queries_r2 = await _generate_followup_queries(workflow_cache, all_results)

        if queries_r2:
            print(f"[benchmark] Round 2 시작 — {len(queries_r2)}개 후속 쿼리 병렬 검색")
            tasks_r2 = [asyncio.to_thread(_search_tavily, q, 5) for q in queries_r2]
            raw_batches_r2 = await asyncio.gather(*tasks_r2, return_exceptions=True)

            r2_added = 0
            for query, batch in zip(queries_r2, raw_batches_r2):
                if isinstance(batch, Exception):
                    continue
                for r in batch:
                    key = r.get("url") or r.get("title", "")
                    if key and key not in seen_urls and r.get("title") not in seen_titles:
                        seen_urls.add(key)
                        seen_titles.add(r.get("title", ""))
                        r["query"] = query
                        r["round"] = 2
                        all_results.append(r)
                        r2_added += 1

            print(f"[benchmark] Round 2 완료 — 신규 {r2_added}건 추가")

    engine = "Tavily (전문 + 2라운드)" if use_tavily else "DuckDuckGo (기본)"
    print(f"[benchmark] {engine} — 총 {len(all_results)}건 ({len(queries_r1 + (queries_r2 if use_tavily else []))}개 쿼리)")

    # URL 있는 결과를 앞으로 정렬 (LLM에게 더 유용한 것 먼저)
    all_results.sort(key=lambda r: (0 if r.get("url") else 1, r.get("round", 1)))

    return all_results[:40]


# ── LLM 벤치마킹 기반 Workflow 개선 ─────────────────────────────────────────

_BENCHMARK_SYSTEM_PROMPT = """
당신은 글로벌 AI 업무 혁신 벤치마킹 전문가입니다.
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

**source 필드 핵심 규칙**
`source`는 반드시 **AI를 실제로 도입하여 운영한 기업**이어야 합니다.
- ✅ 허용: Google, Amazon, Meta, Microsoft, Siemens, DHL, 삼성전자, Unilever, JPMorgan 등
- ❌ 절대 금지: McKinsey, BCG, Bain, Deloitte, PwC, EY, KPMG, Accenture, Gartner, Forrester
  → 이들은 보고서 **작성자**일 뿐, AI를 직접 도입한 기업이 아님
  → 보고서에 구체적 기업 사례가 있으면 그 기업명을 source로, 없으면 해당 인사이트 제외
- ❌ 금지: "Fortune 500 기업", "글로벌 대기업", "한 제조사", "Workday", "SAP", "한 기업"

## 분석 프로세스

**Step 1: 검색 결과 원문 확인 → 실제 언급 여부 검증**
검색 결과에 기업명이 명시되어 있는지 확인합니다.

**Step 2: 영어+한국어 사례 번역·해석**
영어 사례를 한국어로 번역·설명합니다.

**Step 3: L4~L5 단위로 AI 적용 방안 도출**
각 L4 Activity별 AI 기법을 적용합니다.

**Step 4: 사례가 없을 때 솔직하게 명시**
관련 사례가 없으면: `"no_cases_note": "검색 결과에서 해당 프로세스 관련 구체적 기업 사례를 확인할 수 없었습니다. [이유]"`

## 출력 형식 (JSON만 출력, 마크다운 코드블록 없음)
{
  "benchmark_insights": [
    {
      "source": "AI를 실제 도입·운영한 기업명 (컨설팅펌·리서치펌 절대 금지)",
      "insight": "구체적으로 무엇을 AI로 했고 어떤 성과가 있었는지 (영어 사례면 한국어로 설명)",
      "application": "현재 프로세스 L4/L5 어느 부분에 어떻게 적용할지",
      "url": "검색 결과에 실제 존재하는 URL (필수 — URL 없는 항목은 아예 제외)"
    }
  ],
  "no_cases_note": "관련 사례가 없을 때만 이유 기재 (사례가 있으면 빈 문자열)",
  "improvement_summary": "전체 개선 방향 2~3문장 (한국어)",
  "blueprint_summary": "벤치마킹 기반 To-Be 기본 설계 요약 2~3문장 (한국어)",
  "process_name": "프로세스명",
  "redesigned_process": [
    {
      "l3_id": "L3 ID",
      "l3_name": "L3 프로세스명",
      "change_type": "유지|통합|세분화|추가|삭제",
      "change_reason": "변경 이유 (벤치마킹 사례 기반)",
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

    # 현재 redesigned_process 구조
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
        lines.append("**현재 AI 에이전트 및 Task 상세:**\n")
        for agent in workflow_cache.get("agents", []):
            lines.append(f"### {agent['agent_name']} ({agent.get('ai_technique', '')})")
            lines.append(f"  automation_level: {agent['automation_level']}")
            for t in agent.get("assigned_tasks", []):
                lines.append(f"  - [{t.get('task_id','')}] {t.get('task_name','')} | ai_role: {t.get('ai_role','')} | level: {t.get('automation_level','')}")
            lines.append("")

    # 벤치마킹 결과 (Round 표시 + 쿼리 출처 포함)
    lines.append(f"\n## 웹 벤치마킹 검색 결과 (총 {len(benchmark_results)}건)\n")
    for i, r in enumerate(benchmark_results, 1):
        round_label = f" [R{r.get('round', 1)}]" if r.get("round") else ""
        lines.append(f"### [{i}]{round_label} {r['title']}")
        if r.get("url"):
            lines.append(f"- 출처 URL: {r['url']}")
        content = r.get("content", r.get("snippet", ""))
        lines.append(f"- 내용: {content[:1200]}")  # 기존 800자 → 1200자
        lines.append("")

    lines.append("\n## 요청")
    lines.append("위 벤치마킹 사례를 분석하여 현재 To-Be Workflow를 개선해주세요.")
    lines.append("각 benchmark_insight의 url 필드에는 위 검색 결과에 실제로 나온 URL만 기재하세요.")
    lines.append("관련 사례가 없으면 솔직하게 no_cases_note에 이유를 명시하고 benchmark_insights는 빈 배열로 반환하세요.")

    return "\n".join(lines)


async def refine_workflow_with_benchmarks(
    workflow_cache: dict,
    benchmark_results: list[dict],
    api_key: str = "",
    model: str = "claude-sonnet-4-6",
    openai_api_key: str = "",
    openai_model: str = "gpt-4o",
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
