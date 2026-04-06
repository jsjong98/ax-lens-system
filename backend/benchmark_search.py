"""
benchmark_search.py — Perplexity Search + Embedding API 기반 벤치마킹

파이프라인:
  Phase 1. Claude Haiku가 가설 기반 검색 쿼리 10개 직접 생성
  Phase 2. Perplexity Search API로 병렬 검색 (최대 5개씩 배치)
  Phase 3. Perplexity Embedding API로 의미 기반 재랭킹
  Phase 4. Claude Haiku가 Gap 분석 → Round 2 후속 쿼리 4개 생성
  Phase 5. Round 2 병렬 검색 + Embedding 재랭킹
  Phase 6. 전체 결과를 LLM에 전달 → 벤치마킹 테이블 생성

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


# ── Perplexity Search API ────────────────────────────────────────────────────

def _search_perplexity_batch(queries: list[str], max_results: int = 8) -> list[dict]:
    """
    Perplexity Search API — 최대 5개 쿼리를 한 번에 전송.
    POST https://api.perplexity.ai/search
    """
    api_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not api_key or not queries:
        return []

    all_results: list[dict] = []
    seen_urls: set[str] = set()

    # 5개씩 배치
    for i in range(0, len(queries), 5):
        batch = queries[i : i + 5]
        query_val = batch if len(batch) > 1 else batch[0]

        payload = json.dumps({
            "query": query_val,
            "max_results": max_results,
            "max_tokens_per_page": 2500,
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.perplexity.ai/search",
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

            for r in data.get("results", []):
                url = r.get("url", "")
                title = r.get("title", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append({
                        "title": title,
                        "url": url,
                        "content": r.get("snippet", ""),
                        "snippet": r.get("snippet", ""),
                        "source": "perplexity",
                    })
        except Exception as e:
            print(f"[benchmark] Perplexity Search 실패 ({batch[0][:40]}): {e}")

    return all_results


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
    api_key = os.getenv("PERPLEXITY_API_KEY", "")
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

    api_key = os.getenv("PERPLEXITY_API_KEY", "")
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


# ── Phase 1: 가설 기반 쿼리 생성 ─────────────────────────────────────────────

async def _plan_search_queries(
    workflow_cache: dict,
    search_log: list[dict],
) -> list[str]:
    """
    Claude Haiku가 학습 지식을 활용해 가설 기반 검색 쿼리를 생성합니다.
    Perplexity처럼 "GM + Paradox + 2M savings" 같은 구체적 쿼리를 만듭니다.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return _fallback_queries(workflow_cache)

    process_name = workflow_cache.get("process_name", "")
    _, _, l4_names, l4_details = _extract_names_from_cache(workflow_cache)
    pain_points = []
    for d in l4_details[:3]:
        pain_points.extend(d.get("pain_points", [])[:2])

    focus_kr = l4_names[0] if l4_names else process_name

    prompt = f"""당신은 글로벌 HR AI 벤치마킹 리서치 전문가입니다.
당신의 학습 지식을 사용하여 **글로벌 선도 대기업**을 타겟하는 가설 기반 쿼리를 생성하세요.

## 조사 대상
- 프로세스: {process_name}
- L4 활동: {', '.join(l4_names[:6])}
- Pain Point: {', '.join(pain_points[:4]) if pain_points else '없음'}

## 타겟 기업 — 반드시 아래 리스트에서만 선택
아래 카테고리에서 해당 프로세스와 가장 관련성 높은 기업을 골라 쿼리를 만드세요:
- **제조·산업**: Siemens, GE, Honeywell, 3M, DuPont, Caterpillar, Bosch, ABB
- **소비재·유통**: Unilever, P&G, Nestlé, Walmart, Target, Coca-Cola, PepsiCo, L'Oréal
- **에너지·화학**: ExxonMobil, Shell, BP, Chevron, BASF, Dow Chemical
- **금융**: JPMorgan, Goldman Sachs, Citi, HSBC, Mastercard, Visa
- **물류·항공**: DHL, FedEx, UPS, Maersk, Delta Airlines
- **Big Tech (도입처로서)**: Google, Amazon, Microsoft, Meta, IBM, Oracle
- **한국 대기업**: 삼성전자, 현대자동차, SK하이닉스, LG전자, 포스코, 두산

## 가설 기반 검색 전략
이미 알고 있는 사실을 검증하는 쿼리를 만드세요:
- ✅ "Unilever HireVue AI video interview screening 50000 candidates automation results"
- ✅ "Siemens SAP SuccessFactors AI workforce planning time reduction ROI"
- ✅ "Walmart AI HR workforce scheduling automation savings case study"
- ❌ "AI HR automation enterprise 2024" (너무 일반적)
- ❌ 중소기업, 스타트업, 국내 중소IT업체 절대 사용 금지

## 쿼리 10개 생성 (아래 구성으로)
- **글로벌 대기업+도구 가설 쿼리** 5개: 위 리스트 기업 + HR AI 도구 조합 (구체적 수치 포함)
- **벤더 공식 케이스 스터디** 3개: Paradox, Eightfold, HireVue, SAP, Workday 공식 사이트
- **한국 대기업 사례** 2개: 삼성·현대·SK·LG + '{focus_kr}' AI 도입 공식 사례

JSON만 출력:
{{"queries": ["q1",...,"q10"], "hypotheses": ["가설1","가설2","가설3"]}}"""

    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
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


# ── Phase 4: Gap 분석 → Round 2 쿼리 생성 ────────────────────────────────────

async def _generate_followup_queries(
    workflow_cache: dict,
    round1_results: list[dict],
    search_log: list[dict],
) -> list[str]:
    """Round 1 결과를 보고 부족한 부분을 파악, 후속 쿼리 생성."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return []

    process_name = workflow_cache.get("process_name", "")
    _, _, l4_names, _ = _extract_names_from_cache(workflow_cache)

    found_lines = "\n".join(
        f"- {'✓' if r.get('url') else '✗'} | score={r.get('embed_score', 0):.2f} | {r.get('title', '')[:70]}"
        for r in round1_results[:20]
    )

    prompt = f"""리서치 전문가. Round 1 결과를 보고 아직 부족한 것을 파악하여 후속 쿼리 4개를 생성하세요.

프로세스: {process_name} | L4: {', '.join(l4_names[:5])}

Round 1 결과 ({len(round1_results)}건):
{found_lines}

부족한 점을 파악하고 후속 쿼리 4개 생성. 반드시 아래 글로벌 선도 대기업만 사용:
- 제조·산업: Siemens, GE, Honeywell, 3M, DuPont, Caterpillar, Bosch
- 소비재·유통: Unilever, P&G, Nestlé, Walmart, Coca-Cola, PepsiCo
- 에너지: ExxonMobil, Shell, Chevron
- 금융: JPMorgan, Goldman Sachs, HSBC
- 물류: DHL, FedEx, Maersk
- Big Tech: Google, Amazon, Microsoft, IBM
- 한국: 삼성전자, 현대자동차, SK, LG, 포스코

JSON만: {{"queries": ["q1","q2","q3","q4"], "gap": "부족한 점 한 줄"}}"""

    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            data = json.loads(m.group())
            queries = data.get("queries", [])[:4]
            gap = data.get("gap", "")
            search_log.append({"type": "gap", "text": gap, "queries": queries})
            print(f"[benchmark] Gap: {gap}")
            return queries
    except Exception as e:
        print(f"[benchmark] follow-up 쿼리 실패: {e}")
    return []


# ── 통합 검색 파이프라인 ──────────────────────────────────────────────────────

async def search_benchmarks(workflow_cache: dict) -> dict:
    """
    Perplexity Search + Embedding 기반 벤치마킹 파이프라인.
    반환: {"results": [...], "search_log": [...]}
    """
    search_log: list[dict] = []
    use_pplx = bool(os.getenv("PERPLEXITY_API_KEY", ""))
    use_tavily = bool(os.getenv("TAVILY_API_KEY", ""))

    engine = "Perplexity" if use_pplx else ("Tavily" if use_tavily else "DuckDuckGo")
    search_log.append({"type": "engine", "text": f"검색 엔진: {engine}"})

    # ── Phase 1: 가설 기반 쿼리 플래닝 ───────────────────────────────────────
    queries_r1 = await _plan_search_queries(workflow_cache, search_log)

    # ── Phase 2: Round 1 병렬 검색 ───────────────────────────────────────────
    search_log.append({"type": "round_start", "round": 1, "query_count": len(queries_r1)})

    all_results: list[dict] = []
    seen_keys: set[str] = set()

    if use_pplx:
        # Perplexity: 5개씩 배치 (동기 함수를 스레드에서 실행)
        batches = [queries_r1[i:i+5] for i in range(0, len(queries_r1), 5)]
        batch_tasks = [asyncio.to_thread(_search_perplexity_batch, batch, 8) for batch in batches]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        for _, batch_r in zip(batches, batch_results):
            if isinstance(batch_r, Exception):
                continue
            for r in batch_r:
                key = r.get("url") or r.get("title", "")
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    r["round"] = 1
                    all_results.append(r)

        # 쿼리별 로그
        for q in queries_r1:
            search_log.append({"type": "query", "round": 1, "q": q, "found": "?"})

    elif use_tavily:
        tasks = [asyncio.to_thread(_search_tavily, q, 5) for q in queries_r1]
        raw_batches = await asyncio.gather(*tasks, return_exceptions=True)
        for q, batch in zip(queries_r1, raw_batches):
            if isinstance(batch, Exception):
                continue
            cnt = 0
            for r in batch:
                key = r.get("url") or r.get("title", "")
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    r["round"] = 1
                    all_results.append(r)
                    cnt += 1
            search_log.append({"type": "query", "round": 1, "q": q, "found": cnt})
    else:
        tasks = [asyncio.to_thread(_search_duckduckgo, q, 5) for q in queries_r1]
        raw_batches = await asyncio.gather(*tasks, return_exceptions=True)
        for q, batch in zip(queries_r1, raw_batches):
            if isinstance(batch, Exception):
                continue
            cnt = 0
            for r in batch:
                key = r.get("url") or r.get("title", "")
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    r["round"] = 1
                    all_results.append(r)
                    cnt += 1
            search_log.append({"type": "query", "round": 1, "q": q, "found": cnt})

    search_log.append({"type": "round_end", "round": 1, "total": len(all_results)})
    print(f"[benchmark] Round 1 완료 — {len(all_results)}건")

    # ── Phase 3: Embedding 기반 재랭킹 ───────────────────────────────────────
    if use_pplx and all_results:
        process_name = workflow_cache.get("process_name", "")
        _, _, l4_names, _ = _extract_names_from_cache(workflow_cache)
        query_context = f"{process_name} AI 자동화 구현 사례 수치 성과: {', '.join(l4_names[:5])}"
        all_results = await _rerank_by_embeddings(all_results, query_context, search_log)

    # ── Phase 4: Gap 분석 → Round 2 ──────────────────────────────────────────
    queries_r2 = await _generate_followup_queries(workflow_cache, all_results, search_log)

    if queries_r2:
        search_log.append({"type": "round_start", "round": 2, "query_count": len(queries_r2)})

        if use_pplx:
            r2_batch = await asyncio.to_thread(_search_perplexity_batch, queries_r2, 8)
            r2_added = 0
            for r in r2_batch:
                key = r.get("url") or r.get("title", "")
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    r["round"] = 2
                    all_results.append(r)
                    r2_added += 1
            for q in queries_r2:
                search_log.append({"type": "query", "round": 2, "q": q, "found": "?"})
        elif use_tavily:
            tasks2 = [asyncio.to_thread(_search_tavily, q, 5) for q in queries_r2]
            raw2 = await asyncio.gather(*tasks2, return_exceptions=True)
            r2_added = 0
            for q, batch in zip(queries_r2, raw2):
                if isinstance(batch, Exception):
                    continue
                cnt = 0
                for r in batch:
                    key = r.get("url") or r.get("title", "")
                    if key and key not in seen_keys:
                        seen_keys.add(key)
                        r["round"] = 2
                        all_results.append(r)
                        r2_added += 1
                        cnt += 1
                search_log.append({"type": "query", "round": 2, "q": q, "found": cnt})
            r2_added = 0  # already counted above

        search_log.append({"type": "round_end", "round": 2, "total": len(all_results)})
        print(f"[benchmark] Round 2 완료 — 총 {len(all_results)}건")

    # ── 최종 정렬 ────────────────────────────────────────────────────────────
    # embed_score 있으면 우선, 없으면 URL 유무 기준
    all_results.sort(
        key=lambda r: r.get("embed_score", 0.5 if r.get("url") else 0),
        reverse=True,
    )

    final_count = min(len(all_results), 40)
    search_log.append({
        "type": "done",
        "total": len(all_results),
        "final": final_count,
        "engine": engine,
    })

    return {"results": all_results[:40], "search_log": search_log}


# ── LLM 벤치마킹 기반 Workflow 개선 ─────────────────────────────────────────

_BENCHMARK_SYSTEM_PROMPT = """
당신은 글로벌 AI 업무 혁신 벤치마킹 전문가입니다.
영어·한국어 검색 결과를 모두 엄격하게 분석하여, 실제 근거가 있는 AI 적용 선도 사례만 추출합니다.

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
    for i, r in enumerate(benchmark_results, 1):
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
            return json.loads(response.choices[0].message.content or "{}")
        except Exception as e:
            print(f"[benchmark] OpenAI 실패: {e}")

    return {"error": "API 키가 설정되지 않았습니다."}
