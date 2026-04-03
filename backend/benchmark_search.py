"""
benchmark_search.py — 웹 벤치마킹 검색 + LLM 기반 Workflow 개선

Perplexity Deep Research 방식 구현:
  Phase 1. LLM이 프로세스를 분석 → 다각도 초기 쿼리 직접 생성 (템플릿 탈피)
  Phase 2. 8개 쿼리 병렬 검색 (Tavily 전문 읽기)
  Phase 3. 상위 결과 URL에서 실제 페이지 전문 추가 수집
  Phase 4. LLM이 "아직 부족한 것" 파악 → 후속 쿼리 4개 자동 생성
  Phase 5. 후속 쿼리 병렬 검색 (Round 2)
  Phase 6. 전체 결과를 LLM에 전달 → 벤치마킹 테이블 생성
"""
from __future__ import annotations

import asyncio
import html as html_module
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
        "search_depth": "advanced",
        "include_answer": True,
        "include_raw_content": True,   # 실제 페이지 본문 수집
        # 뉴스 사이트 제외 — case study / white paper / 공식 블로그 우선
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

        answer = data.get("answer", "")
        if answer:
            results.append({
                "title": f"[AI 요약] {query}",
                "snippet": answer,
                "url": "",
                "content": answer,
            })

        for r in data.get("results", []):
            raw = r.get("raw_content", "") or ""
            content = r.get("content", "") or ""
            full_content = raw[:2500] if raw else content[:2500]
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
            raw_html = resp.read().decode("utf-8", errors="replace")
        snippet_pattern = re.compile(
            r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
            r'class="result__snippet"[^>]*>(.*?)</(?:td|div)',
            re.DOTALL,
        )
        for match in snippet_pattern.finditer(raw_html):
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


# ── 한국어 HR 용어 → 영어 키워드 매핑 (main.py에서도 import해서 사용) ──────────

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
    """한국어 용어를 영어 키워드로 변환. 매핑에 없으면 원문 반환."""
    for kr, en in _KR_TO_EN.items():
        if kr in korean_term:
            return en
    return korean_term


# ── Phase 1: LLM이 초기 쿼리를 직접 생성 ────────────────────────────────────
# Perplexity 핵심 기술 #1 — 하드코딩 템플릿이 아닌 LLM이 컨텍스트를 이해하고 쿼리 생성

def _extract_names_from_cache(workflow_cache: dict) -> tuple[list, list, list, list]:
    """workflow_cache에서 l2/l3/l4 이름과 l4_details를 추출합니다.
    Workflow 캐시(l4_names 직접 보유)와 New Workflow 캐시(redesigned_process 구조) 모두 지원."""
    l2_names = workflow_cache.get("l2_names", [])
    l3_names = workflow_cache.get("l3_names", [])
    l4_names = workflow_cache.get("l4_names", [])
    l4_details = workflow_cache.get("l4_details", [])

    # New Workflow 캐시: redesigned_process에서 L3/L4 이름 추출
    if not l4_names:
        redesigned = workflow_cache.get("redesigned_process", [])
        for l3 in redesigned:
            l3_name = l3.get("l3_name", "")
            if l3_name and l3_name not in l3_names:
                l3_names.append(l3_name)
            for l4 in l3.get("l4_list", []):
                l4_name = l4.get("l4_name", "")
                if l4_name and l4_name not in l4_names:
                    l4_names.append(l4_name)
                    l4_details.append({"name": l4_name, "pain_points": []})

    # agents 구조 fallback (구형 New Workflow)
    if not l4_names:
        for agent in workflow_cache.get("agents", []):
            for t in agent.get("assigned_tasks", []):
                name = t.get("task_name", "")
                if name and name not in l4_names:
                    l4_names.append(name)

    return l2_names, l3_names, l4_names, l4_details


async def _plan_search_queries(workflow_cache: dict) -> list[str]:
    """
    LLM이 프로세스 컨텍스트를 분석하여 다각도 검색 쿼리를 직접 생성합니다.

    Perplexity가 하는 것처럼:
    - 같은 개념을 다양한 표현으로 검색 (HR → people ops, workforce mgmt 등)
    - 기술 / 비즈니스 / 업종별 / 지역별로 각도를 다르게
    - 수치 성과가 있는 사례를 타겟
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return _fallback_queries(workflow_cache)

    process_name = workflow_cache.get("process_name", "")
    l2_names, l3_names, l4_names, l4_details = _extract_names_from_cache(workflow_cache)

    pain_points = []
    for d in l4_details[:3]:
        pain_points.extend(d.get("pain_points", [])[:2])

    prompt = f"""당신은 글로벌 HR 벤치마킹 리서치 전문가입니다.

## 조사 대상
- 프로세스: {process_name}
- L2 영역: {', '.join(l2_names[:3])}
- L3 하위: {', '.join(l3_names[:4])}
- L4 활동: {', '.join(l4_names[:6])}
- 주요 Pain Point: {', '.join(pain_points[:4]) if pain_points else '없음'}

## 목표
위 프로세스에서 AI를 실제로 도입해 성과를 낸 글로벌 선도 기업 사례를 찾고 싶습니다.
**구체적 기업명 + 수치 성과 + 실제 구현 방법**이 담긴 페이지를 찾을 수 있는 검색 쿼리 8개를 생성하세요.

## 쿼리 생성 원칙
1. **다양한 각도**: 기술 구현 사례 / 비즈니스 성과 / 업종별 (제조·금융·유통) / 한국어 사례 — 각각 1~2개
2. **한국어 ↔ 영어 혼합**: 영어 쿼리 5개, 한국어 쿼리 3개
3. **수치 성과 타겟**: "ROI", "efficiency gain", "time saved", "성과" 등 포함
4. **구체적 기업 타겟**: "Fortune 500", "Samsung", "Siemens", "Google" 등 실명 포함
5. **마케팅 자료 배제**: site:vendor.com 제외, 실제 사례 중심

JSON만 출력:
{{"queries": ["query1", "query2", "query3", "query4", "query5", "query6", "query7", "query8"]}}"""

    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",  # 쿼리 생성은 빠른 모델로
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            data = json.loads(m.group())
            queries = data.get("queries", [])[:8]
            if queries:
                print(f"[benchmark] LLM 쿼리 플래닝 완료 — {len(queries)}개")
                return queries
    except Exception as e:
        print(f"[benchmark] LLM 쿼리 플래닝 실패, fallback 사용: {e}")

    return _fallback_queries(workflow_cache)


def _fallback_queries(workflow_cache: dict) -> list[str]:
    """LLM 쿼리 플래닝 실패 시 사용하는 기본 쿼리."""
    process_name = workflow_cache.get("process_name", "HR process")
    _, _, l4_names, _ = _extract_names_from_cache(workflow_cache)
    focus = l4_names[0] if l4_names else process_name

    # 한국어 → 영어 기본 매핑
    _KR = {"발령": "job transfer", "채용": "recruitment", "평가": "performance appraisal",
           "급여": "payroll", "교육": "L&D training", "인사": "HR"}
    focus_en = next((v for k, v in _KR.items() if k in focus), focus)

    return [
        f"{focus_en} AI automation enterprise case study measurable outcomes 2024 2025",
        f"Workday SAP SuccessFactors {focus_en} generative AI workflow results",
        f"Google Microsoft Amazon {focus_en} HR AI automation implementation",
        f"Gartner Forrester {focus_en} AI adoption enterprise benchmark 2024",
        f"Fortune 500 {focus_en} AI HR transformation ROI case study",
        f"Siemens GE Unilever {focus_en} HR digitization results",
        f"삼성 현대 LG '{focus}' AI 자동화 도입 성과 사례 2024",
        f"'{focus}' AI 혁신 사례 HR 디지털 전환 성과 지표",
    ]


# ── Phase 3: URL에서 실제 페이지 전문 추가 수집 ──────────────────────────────
# Perplexity 핵심 기술 #2 — Tavily snippet 외에 실제 URL을 직접 읽어 더 풍부한 내용 확보

def _fetch_url_content(url: str, max_chars: int = 3000) -> str:
    """URL에서 실제 페이지 내용을 가져와 HTML 태그를 제거합니다."""
    if not url or not url.startswith("http"):
        return ""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                              "KHTML, like Gecko Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "text" not in content_type:
                return ""
            raw_bytes = resp.read(80_000)  # 최대 80KB만 읽기
            charset = "utf-8"
            m = re.search(r'charset=([^\s;]+)', content_type)
            if m:
                charset = m.group(1).strip('"\'')
            html_text = raw_bytes.decode(charset, errors="replace")

        # HTML → 순수 텍스트
        # script / style 블록 제거
        html_text = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', html_text, flags=re.DOTALL | re.IGNORECASE)
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', ' ', html_text)
        # HTML 엔티티 디코딩
        text = html_module.unescape(text)
        # 연속 공백·빈 줄 정리
        text = re.sub(r'\s+', ' ', text).strip()

        return text[:max_chars]

    except Exception as e:
        return ""


async def _enrich_top_results(results: list[dict], top_n: int = 8) -> list[dict]:
    """
    Tavily raw_content가 짧은 상위 결과들에 대해 실제 URL을 직접 읽어 보강합니다.
    병렬로 처리하여 속도를 유지합니다.
    """
    # URL이 있고 content가 짧은 결과 선택 (이미 충분히 길면 skip)
    to_enrich = [
        r for r in results[:top_n]
        if r.get("url") and len(r.get("content", "")) < 800
    ]

    if not to_enrich:
        return results

    print(f"[benchmark] URL 전문 수집 — {len(to_enrich)}개 페이지 병렬 읽기")
    fetch_tasks = [asyncio.to_thread(_fetch_url_content, r["url"]) for r in to_enrich]
    fetched = await asyncio.gather(*fetch_tasks, return_exceptions=True)

    enrich_map = {}
    for r, fetched_text in zip(to_enrich, fetched):
        if isinstance(fetched_text, str) and len(fetched_text) > 200:
            enrich_map[r["url"]] = fetched_text

    enriched = 0
    for r in results:
        url = r.get("url", "")
        if url in enrich_map:
            r["content"] = enrich_map[url]
            enriched += 1

    if enriched:
        print(f"[benchmark] URL 전문 수집 완료 — {enriched}개 보강됨")

    return results


# ── Phase 4: LLM Gap Analysis → Round 2 쿼리 생성 ───────────────────────────

async def _generate_followup_queries(
    workflow_cache: dict,
    round1_results: list[dict],
) -> list[str]:
    """Round 1 결과를 보고 아직 부족한 부분을 LLM이 파악하여 후속 쿼리를 생성합니다."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return []

    process_name = workflow_cache.get("process_name", "")
    _, _, l4_names, _ = _extract_names_from_cache(workflow_cache)

    found_lines = []
    for r in round1_results[:20]:
        has_url = "✓" if r.get("url") else "✗"
        content_len = len(r.get("content", ""))
        found_lines.append(f"- {has_url}URL | {content_len}자 | {r.get('title', '')[:70]}")

    prompt = f"""리서치 전문가입니다. Round 1 검색 결과를 분석하고 빈틈을 메울 후속 쿼리를 생성하세요.

## 조사 프로세스: {process_name}
## L4 활동: {', '.join(l4_names[:6])}

## Round 1 수집 결과 ({len(round1_results)}건)
{chr(10).join(found_lines)}

## 아직 부족한 것을 파악하여 후속 쿼리 4개 생성
기준:
- 구체적 기업명 + 정량 성과(%, 시간, 비용)가 없으면 → 그걸 찾는 쿼리
- 비Tech 산업(제조·금융·유통) 사례가 부족하면 → 업종 특화 쿼리
- 한국어 사례가 없으면 → 한국어 쿼리 포함
- 특정 L4 활동이 아직 커버 안 됐으면 → 그 활동 타겟

JSON만 출력:
{{"queries": ["q1","q2","q3","q4"], "gap": "한 줄 요약"}}"""

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
            if gap:
                print(f"[benchmark] Round 2 gap 분석: {gap}")
            return queries
    except Exception as e:
        print(f"[benchmark] follow-up 쿼리 생성 실패: {e}")
    return []


# ── 통합 검색 파이프라인 ──────────────────────────────────────────────────────

async def search_benchmarks(workflow_cache: dict) -> list[dict]:
    """
    Perplexity Deep Research 방식 검색 파이프라인.

    Phase 1. LLM → 초기 쿼리 8개 직접 생성 (컨텍스트 기반)
    Phase 2. 8개 병렬 검색 (Tavily 전문 읽기)
    Phase 3. 상위 URL에서 실제 페이지 전문 추가 수집
    Phase 4. LLM → Gap 분석 → 후속 쿼리 4개 생성
    Phase 5. 후속 쿼리 4개 병렬 검색 (Round 2)
    """
    use_tavily = bool(os.getenv("TAVILY_API_KEY", ""))
    search_fn = _search_tavily if use_tavily else _search_duckduckgo

    # ── Phase 1: LLM 쿼리 플래닝 ─────────────────────────────────────────────
    queries_r1 = await _plan_search_queries(workflow_cache)

    # ── Phase 2: Round 1 병렬 검색 ───────────────────────────────────────────
    print(f"[benchmark] Phase 2 — {len(queries_r1)}개 쿼리 병렬 검색 시작")
    tasks_r1 = [asyncio.to_thread(search_fn, q, 5) for q in queries_r1]
    raw_batches_r1 = await asyncio.gather(*tasks_r1, return_exceptions=True)

    all_results: list[dict] = []
    seen_keys: set[str] = set()

    for query, batch in zip(queries_r1, raw_batches_r1):
        if isinstance(batch, Exception):
            continue
        for r in batch:
            key = r.get("url") or r.get("title", "")
            if key and key not in seen_keys:
                seen_keys.add(key)
                r["query"] = query
                r["round"] = 1
                all_results.append(r)

    print(f"[benchmark] Phase 2 완료 — {len(all_results)}건")

    # ── Phase 3: 상위 URL 전문 수집 ──────────────────────────────────────────
    if use_tavily:
        all_results = await _enrich_top_results(all_results, top_n=10)

    # ── Phase 4 & 5: Round 2 (LLM Gap 분석 → 후속 검색) ─────────────────────
    if use_tavily:
        queries_r2 = await _generate_followup_queries(workflow_cache, all_results)

        if queries_r2:
            print(f"[benchmark] Phase 5 — {len(queries_r2)}개 후속 쿼리 병렬 검색")
            tasks_r2 = [asyncio.to_thread(_search_tavily, q, 5) for q in queries_r2]
            raw_batches_r2 = await asyncio.gather(*tasks_r2, return_exceptions=True)

            r2_added = 0
            for query, batch in zip(queries_r2, raw_batches_r2):
                if isinstance(batch, Exception):
                    continue
                for r in batch:
                    key = r.get("url") or r.get("title", "")
                    if key and key not in seen_keys:
                        seen_keys.add(key)
                        r["query"] = query
                        r["round"] = 2
                        all_results.append(r)
                        r2_added += 1

            print(f"[benchmark] Phase 5 완료 — 신규 {r2_added}건 추가")

    engine = "Tavily + URL 전문 + 2라운드" if use_tavily else "DuckDuckGo (기본)"
    total_queries = len(queries_r1) + (len(queries_r2) if use_tavily and queries_r2 else 0)
    print(f"[benchmark] 완료 — {engine} | {total_queries}개 쿼리 | 총 {len(all_results)}건")

    # URL 있는 결과를 앞으로 정렬 (LLM에 유용한 것 우선)
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
            for t in agent.get("assigned_tasks", []):
                lines.append(f"  - [{t.get('task_id','')}] {t.get('task_name','')} | level: {t.get('automation_level','')}")
            lines.append("")

    # 검색 결과 — Round 정보 + 풍부한 내용 포함
    lines.append(f"\n## 웹 벤치마킹 검색 결과 (총 {len(benchmark_results)}건)\n")
    for i, r in enumerate(benchmark_results, 1):
        round_label = f" [R{r.get('round', 1)}]" if r.get("round") else ""
        lines.append(f"### [{i}]{round_label} {r['title']}")
        if r.get("url"):
            lines.append(f"- 출처 URL: {r['url']}")
        content = r.get("content", r.get("snippet", ""))
        lines.append(f"- 내용: {content[:1500]}")  # 기존 800자 → 1500자
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
