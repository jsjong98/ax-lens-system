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


# ── 검색 쿼리 생성 ───────────────────────────────────────────────────────────

def _generate_search_queries(workflow_cache: dict) -> list[str]:
    """선도 기업의 AI 적용 사례를 찾기 위한 검색 쿼리 생성."""
    process_name = workflow_cache.get("process_name", "")
    agents = workflow_cache.get("agents", [])

    queries = []

    # 선도 기업 AI 적용 사례 (Best Practice)
    queries.append(f"'{process_name}' AI automation best practice company case study 2024 2025")
    queries.append(f"leading company '{process_name}' AI implementation success story enterprise")

    # 글로벌 기업 HR AI 적용 사례
    queries.append(f"Google Amazon Microsoft '{process_name}' AI HR automation case study")

    # 에이전트 기술 기반 사례
    techniques = set()
    for agent in agents[:3]:
        tech = agent.get("ai_technique", "")
        if tech:
            techniques.add(tech.split(",")[0].strip())
    if techniques:
        tech_str = " ".join(list(techniques)[:2])
        queries.append(f"enterprise {tech_str} '{process_name}' real world deployment results")

    # 컨설팅 펌 리서치
    queries.append(f"McKinsey Deloitte PwC '{process_name}' AI transformation benchmark report")

    return queries[:5]


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
            results = _search_tavily(query, max_results=5)
        else:
            results = _search_duckduckgo(query, max_results=5)

        for r in results:
            if r["title"] not in seen_titles:
                seen_titles.add(r["title"])
                r["query"] = query
                all_results.append(r)

    search_engine = "Tavily (심층 검색)" if use_tavily else "DuckDuckGo (기본)"
    print(f"[benchmark] {search_engine} — {len(all_results)}개 결과 수집 ({len(queries)}개 쿼리)")

    return all_results[:20]


# ── LLM 벤치마킹 기반 Workflow 개선 ─────────────────────────────────────────

_BENCHMARK_SYSTEM_PROMPT = """
당신은 AI 업무 혁신 컨설턴트이자 벤치마킹 전문가입니다.

## 벤치마킹이란
선도 기업(Best Practice)의 AI 적용 사례를 분석하여, 현재 Workflow를 개선하는 것입니다.
단순히 문서에서 정보를 떼오는 것이 아니라, **실제 기업이 해당 분야에서 AI를 어떻게 적용했는지** 사례를 분석합니다.

## 분석 과정

**Step 1: 선도 기업 AI 적용 사례 분석**
- 검색 결과에서 **실제 기업명과 구체적 AI 적용 방법**을 추출
- 예: "Google은 채용에서 AI 기반 이력서 스크리닝으로 처리 시간 75% 단축"
- 예: "Unilever는 HireVue AI 면접으로 초기 스크리닝 자동화, 연간 100만 달러 절감"
- 사례가 없는 일반 문서는 무시하세요

**Step 2: 현재 Workflow에 적용**
- 선도 기업 사례에서 발견한 구체적 방법론을 현재 Workflow에 반영
- AI 자율 수행(Human-on-the-Loop) Task를 늘리는 방향으로 개선
- **Human Task를 늘리지 마세요** — 벤치마킹의 목적은 AI 자율화 강화

**Step 3: 개선 근거**
- 각 개선에 대해 "어떤 기업의 어떤 사례"를 참고했는지 명시

## benchmark_insights 작성 규칙
- source: **실제 기업명** (예: "Google", "Unilever", "삼성SDS")
- insight: 그 기업이 **구체적으로 무엇을 했는지** 한 줄
- application: 우리 Workflow에 **어떻게 적용**할지 한 줄

## Task 작성 규칙 (반드시 지키세요)
- task_name: 짧게 (예: "이력서 AI 스크리닝")
- ai_role: task_name과 다른 구체적 처리 방법
- human_role: task_name과 같은 내용 금지. 구체적 행동만 (예: "최종 합격자 확정")
- **벤치마킹으로 Human Task를 추가하지 마세요. AI Task를 강화하세요.**

## automation_level
- Human-on-the-Loop: AI 자율 수행, 사람 모니터링만
- Human-in-the-Loop: AI 수행 + 사람 확인/승인
- Human-Supervised: 사람 주도, AI 보조

## 출력 형식 (JSON)
{
  "benchmark_insights": [
    {"source": "실제 기업명", "insight": "구체적 AI 적용 사례 한 줄", "application": "우리 적용 방안 한 줄"}
  ],
  "improvement_summary": "2~3문장. 어떤 기업 사례를 참고하여 어떻게 개선했는지.",
  "blueprint_summary": "2~3문장 간결 요약",
  "process_name": "프로세스명",
  "agents": [...],
  "execution_flow": [...]
}

(agents와 execution_flow는 기존 Workflow와 동일한 구조)

## 규칙
- JSON만 출력
- 기존 Workflow의 좋은 점은 유지
- **Human Task를 늘리지 말고 AI Task를 강화**
- 한국어로 작성
"""


def _build_benchmark_prompt(
    workflow_cache: dict,
    benchmark_results: list[dict],
) -> str:
    """벤치마킹 개선용 사용자 프롬프트 생성."""
    lines = ["## 현재 To-Be Workflow\n"]
    lines.append(f"**프로세스명**: {workflow_cache.get('process_name', '')}\n")
    lines.append(f"**설계 요약**: {workflow_cache.get('blueprint_summary', '')}\n")

    # 현재 에이전트/Task 요약
    lines.append("**현재 AI 에이전트:**\n")
    for agent in workflow_cache.get("agents", []):
        lines.append(f"- {agent['agent_name']} ({agent['agent_type']}, {agent['automation_level']})")
        lines.append(f"  기법: {agent['ai_technique']}")
        lines.append(f"  Task: {', '.join(t['task_name'] for t in agent.get('assigned_tasks', []))}")
        lines.append("")

    # 벤치마킹 결과
    lines.append("\n## 웹 벤치마킹 검색 결과\n")
    for i, r in enumerate(benchmark_results, 1):
        lines.append(f"### [{i}] {r['title']}")
        if r.get("url"):
            lines.append(f"- 출처: {r['url']}")
        # Tavily는 content에 풍부한 본문 요약 제공
        content = r.get("content", r.get("snippet", ""))
        lines.append(f"- 내용: {content[:800]}")
        lines.append("")

    lines.append("\n## 요청")
    lines.append("위 벤치마킹 사례를 깊이 분석하여 현재 To-Be Workflow를 개선해주세요.")
    lines.append("각 개선 사항에 대해 어떤 벤치마킹에서 영감을 받았는지 구체적으로 명시해주세요.")
    lines.append("벤치마킹 사례에서 발견한 혁신적 패턴을 적극적으로 반영하세요.")

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
