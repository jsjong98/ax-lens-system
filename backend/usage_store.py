"""
usage_store.py — API 토큰 사용량 누적 저장소

각 분류 API 호출 후 토큰 수를 누적 기록합니다.
저장 위치: backend/usage.json

참고 단가 (2026년 기준 추정 — 실제 청구는 각 제공사 대시보드 확인 필요)
  OpenAI    (O 모델):   입력 $2.50 / 출력 $10.00  (per 1M tokens)
  Anthropic (A 모델):   입력 $3.00 / 출력 $15.00  (per 1M tokens)
  Perplexity (Sonar Pro): 입력 $3.00 / 출력 $15.00 + 요청당 $0.014~$0.022 (per 1M tokens)
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

_PERSIST_ROOT = Path("/app/persist") if Path("/app/persist").exists() else Path(__file__).parent
_USAGE_FILE = _PERSIST_ROOT / "usage.json"

# 참고 단가 (per 1,000,000 tokens, USD)
_PRICE: dict[str, dict[str, float]] = {
    "openai":      {"input": 2.50,  "output": 10.00},
    "anthropic":   {"input": 3.00,  "output": 15.00},
    "perplexity":  {"input": 3.00,  "output": 15.00},
}

_DEFAULT_ENTRY = {
    "total_calls":     0,
    "input_tokens":    0,
    "output_tokens":   0,
    "estimated_cost_usd": 0.0,
    "last_used":       None,
}


def _load() -> dict:
    if _USAGE_FILE.exists():
        try:
            return json.loads(_USAGE_FILE.read_text("utf-8"))
        except Exception:
            pass
    return {"openai": dict(_DEFAULT_ENTRY), "anthropic": dict(_DEFAULT_ENTRY)}


def _save(data: dict) -> None:
    _USAGE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def add_usage(provider: str, input_tokens: int, output_tokens: int) -> None:
    """분류 1건의 토큰 사용량을 누적 기록합니다."""
    data = _load()
    if provider not in data:
        data[provider] = dict(_DEFAULT_ENTRY)

    entry = data[provider]
    price = _PRICE.get(provider, {"input": 0.0, "output": 0.0})

    entry["total_calls"]     += 1
    entry["input_tokens"]    += input_tokens
    entry["output_tokens"]   += output_tokens
    entry["estimated_cost_usd"] = round(
        (entry["input_tokens"]  / 1_000_000 * price["input"]) +
        (entry["output_tokens"] / 1_000_000 * price["output"]),
        6,
    )
    entry["last_used"] = datetime.now(timezone.utc).isoformat()

    _save(data)


def get_usage() -> dict:
    """전체 사용량 요약을 반환합니다."""
    data = _load()
    result = {}
    for provider in ("openai", "anthropic", "perplexity"):
        entry = data.get(provider, dict(_DEFAULT_ENTRY))
        price = _PRICE.get(provider, {"input": 0.0, "output": 0.0})
        result[provider] = {
            **entry,
            "price_per_1m_input":  price["input"],
            "price_per_1m_output": price["output"],
        }
    return result


def reset_usage(provider: str = "all") -> None:
    """사용량을 초기화합니다. provider='all'이면 전체 초기화."""
    data = _load()
    targets = ("openai", "anthropic", "perplexity") if provider == "all" else (provider,)
    for p in targets:
        data[p] = dict(_DEFAULT_ENTRY)
    _save(data)
