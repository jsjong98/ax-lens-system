"""
benchmark_search.py — Perplexity Sonar Pro 기반 벤치마킹

파이프라인:
  Phase 1. Claude Sonnet이 L2→L3→L4→L5 전 계층 맥락을 이해하여 가설 기반 쿼리 생성
  Phase 2. Sonar Pro (streaming) 병렬 검색
           - model: sonar-pro
           - search_type: auto → 복잡한 쿼리는 Pro Search (multi-step + fetch_url_content)
           - search_context_size: high
           - search_domain_filter: 뉴스 도메인 제외
  Phase 3. Perplexity Embedding API로 의미 기반 재랭킹
  Phase 4. Gap 분석 → Round 2 후속 쿼리 생성
  Phase 5. Round 2 병렬 검색

* search_log: 검색 과정 전체를 기록 → 프론트에 "생각 과정" 표시용
* Fallback: Perplexity API 없으면 Tavily → DuckDuckGo 순으로 대체
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import struct
import urllib.parse
import urllib.request
from typing import Any


# ── API 키 헬퍼 ──────────────────────────────────────────────────────────────

def _get_perplexity_key() -> str:
    """환경변수에서 Perplexity API 키를 조회합니다."""
    return os.getenv("PERPLEXITY_API_KEY", "")


# ── Perplexity Search API ────────────────────────────────────────────────────

# 뉴스 도메인 denylist — Perplexity search_domain_filter에 적용 (denylist: "-domain")
# 한국 저품질 뉴스만 차단 — 글로벌 IT/비즈니스 미디어(techcrunch, reuters 등)는 허용
_SONAR_DOMAIN_DENYLIST = [
    "-chosun.com", "-mk.co.kr", "-hankyung.com", "-hani.co.kr",
    "-joins.com", "-joongang.co.kr", "-yonhapnews.co.kr", "-yna.co.kr",
    "-news.naver.com", "-news.daum.net", "-etnews.com", "-zdnet.co.kr",
    "-bloter.net", "-ddaily.co.kr", "-aitimes.com", "-newsis.com",
]


def _search_perplexity_sonar(query: str) -> list[dict]:
    """
    Perplexity Sonar Pro + Pro Search (streaming SSE).
    - model: sonar-pro (sonar 대비 complex query 지원 강화)
    - stream: True (Pro Search 활성화 필수 조건)
    - search_type: auto (복잡한 쿼리 → multi-step + fetch_url_content 자동 적용)
    - search_context_size: high (더 넓은 웹 컨텍스트 수집)
    - search_domain_filter: 뉴스 도메인 제외
    SSE 스트림을 파싱해 전체 content + citations 추출.
    """
    api_key = _get_perplexity_key()
    if not api_key or not query:
        return []

    payload = json.dumps({
        "model": "sonar-pro",
        "messages": [{"role": "user", "content": query}],
        "max_tokens": 2000,
        "stream": True,                        # Pro Search 필수 조건
        "search_domain_filter": _SONAR_DOMAIN_DENYLIST,
        "search_recency_filter": "year",       # 최근 1년 결과 우선
        "search_language_filter": ["en", "ko"],# 영어 + 한국어
        "web_search_options": {
            "search_type": "auto",             # 공식 문서 기준 위치 (classifier가 pro/fast 자동 선택)
            "search_context_size": "high",
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.perplexity.ai/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        content_parts: list[str] = []
        # 2025 API: search_results 필드로 변경 (citations 필드 deprecated)
        search_results: list[dict] = []
        usage_input = 0
        usage_output = 0

        with urllib.request.urlopen(req, timeout=90) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").rstrip("\n\r")
                if not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                # content delta 수집
                for choice in chunk.get("choices", []):
                    delta = choice.get("delta", {})
                    if delta.get("content"):
                        content_parts.append(delta["content"])

                # search_results (신규) 또는 citations (구버전 호환) 수집
                if chunk.get("search_results"):
                    search_results = chunk["search_results"]
                elif chunk.get("citations"):
                    # 구버전 citations 필드 호환 (URL 문자열 배열)
                    search_results = [{"url": u, "title": ""} for u in chunk["citations"]]

                # usage
                if chunk.get("usage"):
                    usage_input = chunk["usage"].get("prompt_tokens", 0)
                    usage_output = chunk["usage"].get("completion_tokens", 0)

        content = "".join(content_parts)

        # 토큰 사용량 누적 기록
        if usage_input or usage_output:
            try:
                from usage_store import add_usage
                add_usage("perplexity", input_tokens=usage_input, output_tokens=usage_output)
            except Exception:
                pass

        results = []
        if search_results:
            for sr in search_results:
                url = sr.get("url", "")
                title = sr.get("title", "") or query[:80]
                results.append({
                    "title": title,
                    "url": url,
                    "content": content,
                    "snippet": content[:500],
                    "source": "perplexity-sonar-pro",
                    "query": query,
                })
        else:
            # citation 없는 경우 — content는 있으므로 URL 없이 추가
            results.append({
                "title": query[:80],
                "url": "",
                "content": content,
                "snippet": content[:500],
                "source": "perplexity-sonar-pro",
                "query": query,
            })

        print(f"[benchmark] Sonar Pro '{query[:50]}' → {len(search_results)}개 출처, {len(content)}자 (in:{usage_input}/out:{usage_output})")
        return results

    except Exception as e:
        print(f"[benchmark] Sonar Pro 실패 ({query[:40]}): {e}")
        return []


# ── Perplexity Embedding API ─────────────────────────────────────────────────

def _decode_int8_b64(b64_str: str) -> list[float]:
    """Base64 INT8 임베딩 디코딩 → [-1, 1] float 배열로 정규화."""
    raw = base64.b64decode(b64_str)
    values = struct.unpack(f"{len(raw)}b", raw)  # signed int8
    return [v / 127.0 for v in values]


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """코사인 유사도 (numpy 미사용)."""
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb + 1e-9) if na and nb else 0.0


def _get_embeddings(texts: list[str], model: str = "pplx-embed-v1-0.6b") -> list[list[float]]:
    """
    Perplexity Embeddings API.
    POST https://api.perplexity.ai/v1/embeddings
    최대 512개 텍스트, 120K 토큰 제한.
    """
    api_key = _get_perplexity_key()
    if not api_key or not texts:
        return []

    payload = json.dumps({
        "input": texts[:128],  # 안전하게 128개 제한
        "model": model,
        "encoding_format": "base64_int8",
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.perplexity.ai/v1/embeddings",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
        return [_decode_int8_b64(item["embedding"]) for item in items]

    except Exception as e:
        print(f"[benchmark] Perplexity Embedding 실패: {e}")
        return []


async def _rerank_by_embeddings(
    results: list[dict],
    query_context: str,
    search_log: list[dict],
) -> list[dict]:
    """
    Embedding 기반 의미 재랭킹.
    query_context(프로세스 설명)와 각 결과의 코사인 유사도로 정렬.
    """
    if not results:
        return results

    api_key = _get_perplexity_key()
    if not api_key:
        return results

    # 임베딩할 텍스트 준비
    result_texts = [
        f"{r.get('title', '')} {r.get('content', r.get('snippet', ''))[:300]}"
        for r in results
    ]
    all_texts = [query_context] + result_texts

    # 배치 임베딩 (동기 함수를 스레드에서 실행)
    embeddings = await asyncio.to_thread(_get_embeddings, all_texts)

    if len(embeddings) < 2:
        search_log.append({"type": "embed_rank", "status": "실패 — fallback 사용"})
        return results

    query_emb = embeddings[0]
    result_embs = embeddings[1:]

    # 코사인 유사도 계산 및 점수 부여
    for r, emb in zip(results, result_embs):
        r["embed_score"] = _cosine_sim(query_emb, emb)

    results.sort(key=lambda r: r.get("embed_score", 0), reverse=True)
    top_score = results[0].get("embed_score", 0) if results else 0

    search_log.append({
        "type": "embed_rank",
        "total": len(results),
        "top_score": round(top_score, 3),
        "status": f"{len(results)}개 의미 재랭킹 완료 (최고 유사도: {top_score:.3f})",
    })

    return results


# ── Tavily 폴백 ──────────────────────────────────────────────────────────────

def _search_tavily(query: str, max_results: int = 5) -> list[dict]:
    """Tavily API 폴백 (Perplexity 없을 때)."""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return []

    payload = json.dumps({
        "query": query,
        "max_results": max_results,
        "search_depth": "advanced",
        "include_answer": True,
        "include_raw_content": True,
        "exclude_domains": [
            "news.naver.com", "n.news.naver.com", "news.daum.net",
            "chosun.com", "joins.com", "joongang.co.kr", "hani.co.kr",
            "mk.co.kr", "hankyung.com", "etnews.com", "zdnet.co.kr",
            "itworld.co.kr", "dt.co.kr", "bloter.net", "ddaily.co.kr",
            "aitimes.com", "aitimes.kr", "newsis.com", "yonhapnews.co.kr",
            "techcrunch.com", "reuters.com", "bloomberg.com", "cnbc.com",
            "businessinsider.com", "venturebeat.com",
        ],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    results = []
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for r in data.get("results", []):
            raw = r.get("raw_content", "") or ""
            content = r.get("content", "") or ""
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": raw[:2500] if raw else content[:2500],
                "snippet": content[:300],
                "source": "tavily",
            })
    except Exception as e:
        print(f"[benchmark] Tavily 폴백 실패 ({query[:40]}): {e}")
    return results


def _search_duckduckgo(query: str, max_results: int = 8) -> list[dict]:
    """DuckDuckGo 최종 폴백."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    })
    results = []
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw_html = resp.read().decode("utf-8", errors="replace")
        pat = re.compile(
            r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
            r'class="result__snippet"[^>]*>(.*?)</(?:td|div)', re.DOTALL)
        for m in pat.finditer(raw_html):
            link, title, snippet = m.groups()
            title = re.sub(r"<[^>]+>", "", title).strip()
            snippet = re.sub(r"<[^>]+>", "", snippet).strip()
            if title and snippet:
                results.append({"title": title, "url": link, "content": snippet, "snippet": snippet, "source": "duckduckgo"})
            if len(results) >= max_results:
                break
    except Exception as e:
        print(f"[benchmark] DuckDuckGo 실패: {e}")
    return results


# ── 한국어 HR 용어 → 영어 매핑 ──────────────────────────────────────────────

_KR_TO_EN: dict[str, str] = {
    "발령": "personnel assignment position change job transfer",
    "입사발령": "employee appointment onboarding personnel action",
    "조직개편": "organizational restructuring reorg",
    "전보": "job transfer internal mobility",
    "승진": "promotion advancement",
    "퇴직": "retirement offboarding separation",
    "채용": "recruitment hiring talent acquisition",
    "면접": "interview candidate screening",
    "교육": "employee training L&D learning development",
    "평가": "performance evaluation appraisal",
    "역량": "competency skills assessment",
    "급여": "payroll salary compensation",
    "보상": "compensation benefits rewards",
    "노사": "labor relations industrial relations",
    "교섭": "collective bargaining negotiation",
    "복리후생": "employee benefits welfare",
    "휴직": "leave of absence absence management",
    "인사": "HR human resources personnel management",
    "승인": "approval workflow authorization",
    "품의": "internal approval document sign-off",
    "보고": "reporting dashboard",
    "공지": "notification announcement",
}


def _translate_to_en(korean_term: str) -> str:
    for kr, en in _KR_TO_EN.items():
        if kr in korean_term:
            return en
    return korean_term


# ── 캐시에서 L2/L3/L4 이름 추출 ─────────────────────────────────────────────

def _extract_names_from_cache(workflow_cache: dict) -> tuple[list, list, list, list]:
    """Workflow 캐시(l4_names)와 New Workflow 캐시(redesigned_process) 모두 지원."""
    l2_names = workflow_cache.get("l2_names", [])
    l3_names = workflow_cache.get("l3_names", [])
    l4_names = workflow_cache.get("l4_names", [])
    l4_details = workflow_cache.get("l4_details", [])

    if not l4_names:
        for l3 in workflow_cache.get("redesigned_process", []):
            l3n = l3.get("l3_name", "")
            if l3n and l3n not in l3_names:
                l3_names.append(l3n)
            for l4 in l3.get("l4_list", []):
                l4n = l4.get("l4_name", "")
                if l4n and l4n not in l4_names:
                    l4_names.append(l4n)
                    l4_details.append({"name": l4n, "pain_points": []})

    if not l4_names:
        for agent in workflow_cache.get("agents", []):
            for t in agent.get("assigned_tasks", []):
                n = t.get("task_name", "")
                if n and n not in l4_names:
                    l4_names.append(n)

    return l2_names, l3_names, l4_names, l4_details




# ── Phase 1: 가설 기반 쿼리 생성 (Tavily/DuckDuckGo fallback용) ──────────────

async def _plan_search_queries(
    workflow_cache: dict,
    search_log: list[dict],
) -> list[str]:
    """
    Round 1 — L5 Task 단위 구체 쿼리 (5개).
    Sonnet이 각 L5 Task의 실제 업무 행위를 읽고, 그 업무를 AI로 자동화한 가장 구체적인 사례를 찾는 쿼리를 생성합니다.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return _fallback_queries(workflow_cache)

    process_name = workflow_cache.get("process_name", "")
    l2_names = workflow_cache.get("l2_names", [])
    _, _, _, l4_details = _extract_names_from_cache(workflow_cache)
    l5_tasks = workflow_cache.get("l5_tasks", [])

    pain_points = []
    for d in l4_details[:4]:
        pain_points.extend(d.get("pain_points", [])[:2])

    # L4별로 L5 Task 묶기 — L4 이름만 보고 오해하지 않도록 각 L4의 실제 업무를 L5로 보여줌
    from collections import defaultdict
    l5_by_l4: dict = defaultdict(list)
    for t in l5_tasks:
        l4_key = t.get("l4", "")
        if t.get("name"):
            l5_by_l4[l4_key].append(t)

    l4_grouped_lines = []
    for i, d in enumerate(l4_details[:6]):
        l4_name = d.get("name", "")
        tasks_under = l5_by_l4.get(l4_name, [])
        l4_grouped_lines.append(f"  [{i+1}] L4: {l4_name}")
        if tasks_under:
            for t in tasks_under[:6]:
                desc = t.get("description", "")
                line = f"      └ {t['name']}"
                if desc:
                    line += f": {desc}"
                l4_grouped_lines.append(line)
        else:
            l4_grouped_lines.append("      └ (L5 상세 없음)")
    l4_with_l5 = "\n".join(l4_grouped_lines)

    l2_context = f"기능 단위: {', '.join(l2_names[:2])} (BP = Business Partner, HR 파트너 기능)" if l2_names else ""

    prompt = f"""당신은 AX(AI Transformation) 전략 수립을 위한 글로벌 HR 벤치마킹 리서치 전문가입니다.
이것은 3라운드 탐색의 **Round 1: L5 Task 단위 구체 탐색**입니다.

## 두산 HR 프로세스 계층
{l2_context}
- L3 프로세스: {process_name}
- L4 + L5 상세 (각 L5 Task의 실제 업무 행위를 파악하세요):
{l4_with_l5 if l4_with_l5 else '  (정보 없음)'}
- Pain Point: {', '.join(list(dict.fromkeys(pain_points))[:5]) if pain_points else '없음'}

## 약어 정의
- BP = Business Partner (인사 담당 파트너), ER = Employee Relations

## Round 1 목표: L5 Task 하나씩 들여다보기
각 L5 Task의 구체적 업무 행위(예: "문서 초안 작성", "시스템 데이터 입력", "승인 상신", "공지 발송")를 영어로 추상화하여,
**그 행위를 AI로 자동화한 가장 구체적인 글로벌 대기업 사례**를 찾는 쿼리를 만드세요.

쿼리 규칙:
1. L5 Task 내용을 근거로 — L4 이름만 보고 만들지 말 것 (예: "조직개편"만 보면 의미 오해 가능)
2. AI 키워드 필수: "AI", "GenAI", "LLM", "intelligent automation", "AI agent" 중 하나 이상
3. Forbes Global 500 / Fortune 500 수준만, 스타트업 금지
4. 시스템 기능 소개 아닌 AI 전환 성과·사례 중심

## 쿼리 10개 생성
- L5 Task 행위 기반 AI 자동화 사례 쿼리 10개 (각기 다른 L5 업무 행위 커버)

JSON만 출력:
{{"queries": ["q1","q2","q3","q4","q5","q6","q7","q8","q9","q10"], "hypotheses": ["가설1","가설2","가설3"]}}"""

    try:
        from anthropic import AsyncAnthropic
        from usage_store import add_usage as _add_usage_plan
        client = AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        if resp.usage:
            _add_usage_plan("anthropic",
                            input_tokens=resp.usage.input_tokens,
                            output_tokens=resp.usage.output_tokens)
        raw = resp.content[0].text.strip()
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            data = json.loads(m.group())
            queries = data.get("queries", [])[:10]
            hypotheses = data.get("hypotheses", [])
            if queries:
                search_log.append({
                    "type": "plan",
                    "hypotheses": hypotheses[:3],
                    "query_count": len(queries),
                    "queries": queries,
                })
                print(f"[benchmark] 쿼리 플래닝 — {len(queries)}개 | 가설: {' / '.join(hypotheses[:2])}")
                return queries
    except Exception as e:
        print(f"[benchmark] 쿼리 플래닝 실패: {e}")

    queries = _fallback_queries(workflow_cache)
    search_log.append({"type": "plan", "hypotheses": [], "query_count": len(queries), "queries": queries, "fallback": True})
    return queries


def _fallback_queries(workflow_cache: dict) -> list[str]:
    process_name = workflow_cache.get("process_name", "HR process")
    _, _, l4_names, _ = _extract_names_from_cache(workflow_cache)
    focus_kr = l4_names[0] if l4_names else process_name
    focus_en = _translate_to_en(focus_kr)
    return [
        f"Unilever HireVue AI {focus_en} video interview screening automation results",
        f"Siemens SAP SuccessFactors AI {focus_en} workforce planning time reduction ROI",
        f"Walmart Target AI {focus_en} workforce scheduling automation savings case study",
        f"General Motors Paradox AI {focus_en} recruiting chatbot savings official",
        f"DHL FedEx AI {focus_en} HR automation productivity improvement results",
        f"P&G Nestlé Coca-Cola AI {focus_en} talent acquisition case study",
        f"Paradox Eightfold {focus_en} AI case study Fortune 500 customer official site",
        f"Workday SAP SuccessFactors {focus_en} AI generative features official documentation",
        f"삼성전자 현대자동차 '{focus_kr}' AI 자동화 공식 케이스스터디 성과",
        f"SK하이닉스 LG전자 포스코 '{focus_kr}' AI HR 도입 사례 결과",
    ]


# ── Round 2/3 쿼리 생성 ──────────────────────────────────────────────────────

def _fmt_results_summary(results: list[dict], limit: int = 15) -> str:
    """검색 결과를 Sonnet에게 넘길 간결한 요약 문자열로 변환."""
    lines = []
    for r in results[:limit]:
        status = "✓" if r.get("url") else "✗"
        title = r.get("title", "")[:70]
        lines.append(f"- {status} [R{r.get('round', '?')}] {title}")
    return "\n".join(lines) if lines else "(결과 없음)"


async def _plan_l4_queries(
    workflow_cache: dict,
    r1_results: list[dict],
    search_log: list[dict],
) -> list[str]:
    """
    Round 2 — L4 활동 단위 쿼리 (5개).
    Sonnet이 R1 결과 + L5 맥락을 보고 L4 활동 단위에서 AI 전환 패턴을 찾는 쿼리를 생성합니다.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return []

    process_name = workflow_cache.get("process_name", "")
    _, _, _, l4_details = _extract_names_from_cache(workflow_cache)
    l5_tasks = workflow_cache.get("l5_tasks", [])

    from collections import defaultdict
    l5_by_l4: dict = defaultdict(list)
    for t in l5_tasks:
        l5_by_l4[t.get("l4", "")].append(t)

    l4_grouped_lines = []
    for i, d in enumerate(l4_details[:6]):
        l4_name = d.get("name", "")
        tasks_under = l5_by_l4.get(l4_name, [])
        l4_grouped_lines.append(f"  [{i+1}] L4: {l4_name}")
        for t in tasks_under[:5]:
            desc = t.get("description", "")
            line = f"      └ {t['name']}" + (f": {desc}" if desc else "")
            l4_grouped_lines.append(line)
    l4_with_l5 = "\n".join(l4_grouped_lines) or "  (정보 없음)"

    r1_summary = _fmt_results_summary(r1_results)

    prompt = f"""AX 벤치마킹 리서치 전문가입니다.
이것은 3라운드 탐색의 **Round 2: L4 활동 단위 패턴 탐색**입니다.

## HR 프로세스 계층
- L3: {process_name}
- L4 + L5 상세:
{l4_with_l5}

## Round 1 결과 ({len(r1_results)}건) — L5 Task 단위 구체 탐색 결과
{r1_summary}

## Round 2 목표: L5를 모두 이해한 뒤 L4 활동 단위로 질문
R1에서 개별 L5 Task 수준의 사례를 탐색했습니다.
이제 **L4 활동 하나를 L5 Task들을 모두 읽어 실제 의미를 파악한 뒤**, 그 활동 전체를 AI로 전환한 더 넓은 패턴·사례를 찾는 쿼리를 만드세요.
- L4 이름만 보지 말 것 (예: "조직개편"이라는 L4 이름만 보면 전략 프로세스로 오해 가능 — L5를 읽으면 행정 후처리임을 알 수 있음)
- R1에서 이미 찾은 방향은 겹치지 않도록
- AI 키워드 필수: "AI", "GenAI", "LLM", "intelligent automation", "AI agent" 중 하나 이상
- Forbes Global 500 수준만, 스타트업 금지

## 쿼리 8개 생성
- L4 활동별 AI 전환 사례 쿼리 8개 (L5를 이해하고 L4 단위로 추상화한 쿼리)

JSON만: {{"queries": ["q1","q2","q3","q4","q5","q6","q7","q8"], "l4_focus": "어떤 L4 활동에 집중했는지 한 줄"}}"""

    try:
        from anthropic import AsyncAnthropic
        from usage_store import add_usage as _add_usage_r2
        client = AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        if resp.usage:
            _add_usage_r2("anthropic",
                          input_tokens=resp.usage.input_tokens,
                          output_tokens=resp.usage.output_tokens)
        raw = resp.content[0].text.strip()
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            data = json.loads(m.group())
            queries = data.get("queries", [])[:8]
            focus = data.get("l4_focus", "")
            search_log.append({"type": "plan_r2", "l4_focus": focus, "queries": queries})
            print(f"[benchmark] R2 쿼리 — L4 포커스: {focus}")
            return queries
    except Exception as e:
        print(f"[benchmark] R2 쿼리 생성 실패: {e}")
    return []


async def _plan_l3_queries(
    workflow_cache: dict,
    r1_results: list[dict],
    r2_results: list[dict],
    search_log: list[dict],
) -> list[str]:
    """
    Round 3 — L3 프로세스 전체 전환 + 보완 쿼리 (4개).
    Sonnet이 R1+R2 결과를 보고 L3 전체의 AX 전환 개요 + 아직 못 찾은 부분을 보완합니다.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return []

    process_name = workflow_cache.get("process_name", "")
    _, _, _, l4_details = _extract_names_from_cache(workflow_cache)
    l4_names = [d.get("name", "") for d in l4_details[:6]]

    all_results = r1_results + r2_results
    r1_summary = _fmt_results_summary(r1_results, limit=10)
    r2_summary = _fmt_results_summary(r2_results, limit=10)

    prompt = f"""AX 벤치마킹 리서치 전문가입니다.
이것은 3라운드 탐색의 **Round 3: L3 프로세스 전체 AX 전환 + 보완**입니다.

## HR 프로세스
- L3: {process_name}
- L4 활동: {', '.join(l4_names)}

## Round 1 결과 ({len(r1_results)}건) — L5 단위 구체 탐색
{r1_summary}

## Round 2 결과 ({len(r2_results)}건) — L4 단위 패턴 탐색
{r2_summary}

## Round 3 목표: L3 전체를 조망하는 AX 전환 + 보완
R1(L5 구체)/R2(L4 패턴)에서 찾지 못한 것을 파악하고:
1. L4, L5를 모두 이해한 뒤 이 **L3 프로세스 전체**를 AI로 전환한 종합 사례 쿼리
2. R1/R2에서 커버되지 않은 L4 활동이나 관점의 보완 쿼리

규칙:
- AI 키워드 필수: "AI", "GenAI", "LLM", "intelligent automation" 중 하나 이상
- Forbes Global 500 수준만, 스타트업 금지
- R1/R2에서 이미 찾은 방향 중복 금지

## 쿼리 7개 생성
- L3 전체 AX 전환 종합 사례 쿼리 3개
- R1/R2 보완 쿼리 4개 (아직 못 찾은 L4 활동 또는 관점)

JSON만: {{"queries": ["q1","q2","q3","q4","q5","q6","q7"], "gap": "R1/R2에서 부족했던 점 한 줄"}}"""

    try:
        from anthropic import AsyncAnthropic
        from usage_store import add_usage as _add_usage_r3
        client = AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        if resp.usage:
            _add_usage_r3("anthropic",
                          input_tokens=resp.usage.input_tokens,
                          output_tokens=resp.usage.output_tokens)
        raw = resp.content[0].text.strip()
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            data = json.loads(m.group())
            queries = data.get("queries", [])[:7]
            gap = data.get("gap", "")
            search_log.append({"type": "plan_r3", "gap": gap, "queries": queries})
            print(f"[benchmark] R3 쿼리 — Gap: {gap}")
            return queries
    except Exception as e:
        print(f"[benchmark] R3 쿼리 생성 실패: {e}")
    return []


# ── 통합 검색 파이프라인 ──────────────────────────────────────────────────────

async def _run_search_round(
    queries: list[str],
    round_num: int,
    use_pplx: bool,
    use_tavily: bool,
    seen_keys: set,
    search_log: list[dict],
    progress_cb=None,
) -> list[dict]:
    """단일 라운드 검색 실행 — 엔진별 분기 + 중복 제거 후 결과 반환."""
    results: list[dict] = []
    search_log.append({"type": "round_start", "round": round_num, "query_count": len(queries)})
    if progress_cb:
        progress_cb({"type": "round_start", "round": round_num, "count": len(queries)})

    # 개별 쿼리 태스크 — 완료되는 순서대로 처리
    async def _run_one(q: str, idx: int):
        if use_pplx:
            batch = await asyncio.to_thread(_search_perplexity_sonar, q)
        elif use_tavily:
            batch = await asyncio.to_thread(_search_tavily, q, 5)
        else:
            batch = await asyncio.to_thread(_search_duckduckgo, q, 5)
        return q, batch, idx

    tasks = [asyncio.create_task(_run_one(q, i + 1)) for i, q in enumerate(queries)]

    for coro in asyncio.as_completed(tasks):
        try:
            q, batch, idx = await coro
        except Exception as e:
            search_log.append({"type": "query", "round": round_num, "q": "?", "found": 0})
            continue
        cnt = 0
        for r in batch:
            key = r.get("url") or r.get("query", q) or r.get("title", "")
            if key and key not in seen_keys:
                seen_keys.add(key)
                r["round"] = round_num
                results.append(r)
                cnt += 1
        search_log.append({"type": "query", "round": round_num, "q": q, "found": cnt})
        if progress_cb:
            progress_cb({
                "type": "query_done",
                "round": round_num,
                "idx": idx,
                "total": len(queries),
                "query": q[:80],
                "found": cnt,
            })

    search_log.append({"type": "round_end", "round": round_num, "total": len(results)})
    if progress_cb:
        progress_cb({"type": "round_end", "round": round_num, "collected": len(results)})
    print(f"[benchmark] Round {round_num} 완료 — {len(results)}건 추가")
    return results


async def search_benchmarks(workflow_cache: dict, progress_cb=None) -> dict:
    """
    Sonnet ↔ Sonar 3라운드 벤치마킹 파이프라인.
    - Round 1 (L5): Sonnet이 L5 Task 단위 구체 쿼리 생성 → 검색
    - Round 2 (L4): Sonnet이 R1 결과 보고 L4 활동 단위 쿼리 생성 → 검색
    - Round 3 (L3): Sonnet이 R1+R2 결과 보고 L3 전환 + 보완 쿼리 생성 → 검색
    반환: {"results": [...], "search_log": [...]}
    progress_cb(event_dict): 진행 상황을 실시간으로 전달하는 동기 콜백
    """
    def emit(event: dict):
        if progress_cb:
            try:
                progress_cb(event)
            except Exception:
                pass

    search_log: list[dict] = []
    use_pplx = bool(_get_perplexity_key())
    use_tavily = bool(os.getenv("TAVILY_API_KEY", ""))

    engine = "Perplexity Sonar Pro" if use_pplx else ("Tavily" if use_tavily else "DuckDuckGo")
    search_log.append({"type": "engine", "text": f"검색 엔진: {engine}"})
    emit({"type": "engine", "text": f"검색 엔진: {engine}"})

    seen_keys: set[str] = set()
    all_results: list[dict] = []

    # ── Round 1: L5 Task 단위 구체 탐색 ──────────────────────────────────────
    emit({"type": "plan", "round": 1, "text": "R1 쿼리 생성 중 (L5 Task 단위 구체 탐색)..."})
    queries_r1 = await _plan_search_queries(workflow_cache, search_log)
    emit({"type": "queries", "round": 1, "queries": [q[:80] for q in queries_r1], "count": len(queries_r1)})

    r1_results = await _run_search_round(queries_r1, 1, use_pplx, use_tavily, seen_keys, search_log, emit)
    all_results.extend(r1_results)

    # ── Embedding 재랭킹 (Sonar Pro 결과 품질 향상) ───────────────────────────
    if use_pplx and all_results:
        emit({"type": "embed", "text": f"임베딩 재랭킹 중... ({len(all_results)}건 의미 유사도 정렬)"})
        process_name = workflow_cache.get("process_name", "")
        _, _, l4_names, _ = _extract_names_from_cache(workflow_cache)
        query_context = f"{process_name} AI 자동화 구현 사례 수치 성과: {', '.join(l4_names[:5])}"
        all_results = await _rerank_by_embeddings(all_results, query_context, search_log)
        r1_results = all_results  # 재랭킹된 결과를 R2 플래닝에 사용

    # ── Round 2: L4 활동 단위 패턴 탐색 ─────────────────────────────────────
    emit({"type": "plan", "round": 2, "text": "R2 쿼리 생성 중 (L4 활동 단위 패턴 탐색)..."})
    queries_r2 = await _plan_l4_queries(workflow_cache, r1_results, search_log)
    if queries_r2:
        emit({"type": "queries", "round": 2, "queries": [q[:80] for q in queries_r2], "count": len(queries_r2)})
        r2_results = await _run_search_round(queries_r2, 2, use_pplx, use_tavily, seen_keys, search_log, emit)
        all_results.extend(r2_results)
    else:
        r2_results = []

    # ── Round 3: L3 전체 AX 전환 + 보완 ─────────────────────────────────────
    emit({"type": "plan", "round": 3, "text": "R3 쿼리 생성 중 (L3 종합 + 보완 탐색)..."})
    queries_r3 = await _plan_l3_queries(workflow_cache, r1_results, r2_results, search_log)
    if queries_r3:
        emit({"type": "queries", "round": 3, "queries": [q[:80] for q in queries_r3], "count": len(queries_r3)})
        r3_results = await _run_search_round(queries_r3, 3, use_pplx, use_tavily, seen_keys, search_log, emit)
        all_results.extend(r3_results)

    # ── 최종 정렬 ─────────────────────────────────────────────────────────────
    all_results.sort(
        key=lambda r: r.get("embed_score", 0.5 if r.get("url") else 0),
        reverse=True,
    )

    final_count = min(len(all_results), 200)
    search_log.append({
        "type": "done",
        "total": len(all_results),
        "final": final_count,
        "engine": engine,
    })
    emit({"type": "done_search", "total": len(all_results), "final": final_count})

    return {"results": all_results[:200], "search_log": search_log}


# ── LLM 벤치마킹 기반 Workflow 개선 ─────────────────────────────────────────

_BENCHMARK_SYSTEM_PROMPT = """
당신은 글로벌 AI 업무 혁신 벤치마킹 전문가입니다.
영어·한국어 검색 결과를 모두 엄격하게 분석하여, 실제 근거가 있는 AI 적용 선도 사례만 추출합니다.

## 두산 HR 전문 약어 정의 (반드시 준수)
- **BP** = Business Partner (HR BP, 인사 담당 파트너) — 절대로 'British Petroleum'이 아님
- **ER** = Employee Relations (노사관계/직원관계)
- **발령** = 인사발령 (personnel assignment/job transfer)
- **조직개편** (이 문맥에서) = 조직변경에 따른 인사발령 처리 — '전략적 조직 재설계'가 아님

## ⚠️ 벤치마킹 범위 정의 (필수 이해)
이 프로세스는 조직개편·인사이동이 **이미 결정된 후** 그 내용을 처리하는 후처리 행정 프로세스입니다:
- ✅ 포함: 시스템 데이터 자동 업데이트(SAP SuccessFactors, ERP), 발령 승인 워크플로우 자동화, 인사발령 공지 자동 발송
- ❌ 제외: 조직 재설계 전략, 인력 재배치 의사결정, M&A 조직통합 — 이런 사례는 분석에서 완전히 제외

## ⚠️ 최우선 원칙: 모르면 모른다고 명확히 표기
- 검색 결과에 해당 기업명이 명확히 나오지 않으면 → source: "사례 미확인" 처리
- 수치 성과가 없으면 → outcome에 "수치 미확인, 정성적 효과만 보고됨" 명시
- URL이 없는 사례는 → url: "" (빈 문자열), 절대 URL 꾸며내지 말 것

## 포함 기준 (3가지 모두 충족해야 포함)
1. **기업명**: 고유 기업명이 검색 결과에 명확히 언급됨
2. **URL**: 검색 결과에 실제 URL이 있음
3. **내용**: AI 적용 방법 또는 성과가 구체적으로 언급됨

## source 필드 핵심 규칙
- ✅ 허용: Google, Amazon, GM, Siemens, 삼성전자, Unilever 등 실명 기업
- ❌ 금지: McKinsey, BCG, Deloitte, PwC, Gartner, Forrester (보고서 작성자)
- ❌ 금지: "Fortune 500 기업", "익명", 30자 초과 표현

## 출력 형식 (JSON만 출력, 마크다운 코드블록 없음)
{
  "benchmark_insights": [
    {
      "source": "기업명",
      "insight": "구체적으로 무엇을 AI로 했고 어떤 성과",
      "application": "현재 프로세스 L4/L5 적용 방안",
      "url": "실제 URL (없으면 빈 문자열)"
    }
  ],
  "no_cases_note": "사례 없을 때만 이유",
  "improvement_summary": "전체 개선 방향 2~3문장",
  "blueprint_summary": "벤치마킹 기반 To-Be 설계 요약",
  "process_name": "프로세스명",
  "redesigned_process": [
    {
      "l3_id": "L3 ID",
      "l3_name": "L3 프로세스명",
      "change_type": "유지|통합|세분화|추가|삭제",
      "change_reason": "변경 이유",
      "l4_list": [
        {
          "l4_id": "L4 ID",
          "l4_name": "L4 Activity명",
          "change_type": "유지|통합|세분화|추가|삭제",
          "change_reason": "변경 이유",
          "l5_list": [
            {
              "task_id": "task_id 또는 NEW_xxx",
              "task_name": "Task명",
              "change_type": "유지|통합|세분화|추가|삭제",
              "ai_application": "AI 적용 내용 또는 '해당 없음'",
              "automation_level": "Full-Auto|Human-in-Loop|Human-on-the-Loop|Human",
              "ai_technique": "RPA, LLM, ML 예측 등"
            }
          ]
        }
      ]
    }
  ]
}

## 절대 규칙
- JSON만 출력 (코드블록 없음)
- 한국어로 작성, 영어 사례도 번역
- URL 없는 인사이트 제외
- 추측 금지
"""


def _build_benchmark_prompt(workflow_cache: dict, benchmark_results: list[dict]) -> str:
    lines = ["## 현재 To-Be Workflow\n"]
    lines.append(f"**프로세스명**: {workflow_cache.get('process_name', '')}\n")
    lines.append(f"**설계 요약**: {workflow_cache.get('blueprint_summary', '')}\n")

    redesigned = workflow_cache.get("redesigned_process", [])
    if redesigned:
        lines.append("**현재 기본 설계:**\n")
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

    lines.append(f"\n## 웹 벤치마킹 검색 결과 (총 {len(benchmark_results)}건)\n")
    for i, r in enumerate(benchmark_results[:20], 1):
        score_label = f" [유사도:{r['embed_score']:.2f}]" if r.get("embed_score") else ""
        round_label = f" [R{r.get('round', 1)}]" if r.get("round") else ""
        lines.append(f"### [{i}]{round_label}{score_label} {r['title']}")
        if r.get("url"):
            lines.append(f"- 출처 URL: {r['url']}")
        content = r.get("content", r.get("snippet", ""))
        lines.append(f"- 내용: {content[:1500]}")
        lines.append("")

    lines.append("\n## 요청")
    lines.append("위 벤치마킹 사례를 분석하여 현재 To-Be Workflow를 개선해주세요.")
    lines.append("각 benchmark_insight의 url 필드에는 위 검색 결과에 실제로 나온 URL만 기재하세요.")
    return "\n".join(lines)


async def refine_workflow_with_benchmarks(
    workflow_cache: dict,
    benchmark_results: list[dict],
    api_key: str = "",
    model: str = "claude-sonnet-4-6",
    openai_api_key: str = "",
    openai_model: str = "gpt-4o",
) -> dict:
    from new_workflow_generator import _extract_json
    user_prompt = _build_benchmark_prompt(workflow_cache, benchmark_results)

    from usage_store import add_usage as _add_usage_bm

    anthropic_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=anthropic_key)
            response = await client.messages.create(
                model=model, max_tokens=8192,
                system=_BENCHMARK_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            if response.usage:
                _add_usage_bm("anthropic",
                              input_tokens=response.usage.input_tokens,
                              output_tokens=response.usage.output_tokens)
            return _extract_json(response.content[0].text)
        except Exception as e:
            print(f"[benchmark] Anthropic 실패: {e}")

    openai_key = openai_api_key or os.getenv("OPENAI_API_KEY", "")
    if openai_key:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=openai_key)
            response = await client.chat.completions.create(
                model=openai_model, temperature=0.0,
                messages=[
                    {"role": "system", "content": _BENCHMARK_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            if response.usage:
                _add_usage_bm("openai",
                              input_tokens=response.usage.prompt_tokens,
                              output_tokens=response.usage.completion_tokens)
            return json.loads(response.choices[0].message.content or "{}")
        except Exception as e:
            print(f"[benchmark] OpenAI 실패: {e}")

    return {"error": "API 키가 설정되지 않았습니다."}
