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
    """Workflow 결과에서 맥락에 맞는 검색 쿼리를 생성합니다."""
    process_name = workflow_cache.get("process_name", "")
    agents = workflow_cache.get("agents", [])
    summary = workflow_cache.get("blueprint_summary", "")

    queries = []

    # 핵심 프로세스 쿼리
    queries.append(f"{process_name} AI 자동화 도입 사례 best practice")
    queries.append(f"{process_name} AI transformation enterprise case study")

    # 에이전트 유형 기반 심화 쿼리
    for agent in agents[:2]:
        agent_type = agent.get("agent_type", "")
        technique = agent.get("ai_technique", "")
        if agent_type:
            queries.append(f"enterprise {agent_type} {technique} implementation case study")

    # 선제적 AI 쿼리
    queries.append(f"proactive AI assistant HR {process_name} innovation")

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

## 역할
현재 설계된 To-Be Workflow와 웹에서 검색한 벤치마킹 사례를 분석하여,
Workflow를 **더 혁신적이고 실용적으로 개선**합니다.

## 사고 과정

**Step 1: 벤치마킹 사례 분석**
- 검색된 사례들에서 핵심 인사이트를 추출하세요
- 현재 Workflow에 빠져있는 혁신 포인트를 식별하세요
- 업계 트렌드와 best practice를 파악하세요

**Step 2: Workflow 개선**
- 벤치마킹에서 발견한 아이디어를 현재 Workflow에 반영하세요
- 새로운 Task를 추가하거나, 기존 Task의 AI 역할을 강화하세요
- 실현 가능성과 혁신성 사이의 균형을 맞추세요

**Step 3: 개선 근거 제시**
- 각 개선 사항에 대해 어떤 벤치마킹 사례에서 영감을 받았는지 설명하세요

## 출력 형식 (JSON)
{
  "benchmark_insights": [
    {
      "source": "벤치마킹 출처/사례명",
      "insight": "핵심 인사이트",
      "application": "현재 Workflow에 적용할 점"
    }
  ],
  "improvement_summary": "개선 요약 (3~4문장). 어떤 벤치마킹을 참고하여 어떻게 개선했는지.",
  "blueprint_summary": "개선된 전체 Workflow 설계 요약 (3~4문장)",
  "process_name": "프로세스명",
  "agents": [
    {
      "agent_id": "agent_1",
      "agent_name": "에이전트 이름",
      "agent_type": "에이전트 유형",
      "ai_technique": "사용 기법",
      "description": "역할 설명",
      "automation_level": "Full-Auto | Human-in-Loop | Human-Supervised",
      "assigned_tasks": [
        {
          "task_id": "1.1",
          "task_name": "Task명",
          "l4": "상위 카테고리",
          "l3": "프로세스 영역",
          "ai_role": "AI가 하는 일",
          "human_role": "사람이 하는 일",
          "input_data": ["입력"],
          "output_data": ["출력"],
          "automation_level": "Full-Auto | Human-in-Loop | Human-Supervised"
        }
      ]
    }
  ],
  "execution_flow": [
    {
      "step": 1,
      "step_name": "단계명",
      "step_type": "sequential | parallel",
      "description": "설명",
      "agent_ids": ["agent_1"],
      "task_ids": ["1.1"]
    }
  ]
}

## 규칙
- 반드시 JSON만 출력 (마크다운 코드 블록 없음)
- 기존 Workflow의 좋은 점은 유지하면서 개선하세요
- 벤치마킹에서 영감받은 새로운 Task를 추가할 수 있습니다
- 비현실적인 개선은 피하세요 — 실제 구현 가능한 수준으로
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
