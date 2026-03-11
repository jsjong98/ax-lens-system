"""
classifier.py — 분류기 추상 인터페이스 + StubClassifier

provider 파라미터로 OpenAI / Anthropic 분류기를 선택합니다.
  - "openai"     → LLMClassifier (gpt-5.4)
  - "anthropic"  → AnthropicClassifier (claude-sonnet-4-6)
"""
from __future__ import annotations
import os
from abc import ABC, abstractmethod
from typing import AsyncIterator

from models import ClassificationResult, ClassifierSettings, Task


# ── 추상 기반 클래스 ──────────────────────────────────────────────────────────

class BaseClassifier(ABC):
    """모든 분류기가 구현해야 하는 인터페이스."""

    @abstractmethod
    async def classify_stream(
        self,
        tasks: list[Task],
        settings: ClassifierSettings,
    ) -> AsyncIterator[ClassificationResult]:
        ...  # pragma: no cover


# ── StubClassifier — API Key 미설정 시 사용 ───────────────────────────────────

class StubClassifier(BaseClassifier):
    """API Key 미설정 또는 패키지 누락 시 사용하는 더미 분류기."""

    def __init__(self, provider: str = "openai", reason: str = "api_key"):
        self._provider = provider
        self._reason = reason  # "api_key" | "import_error"

    async def classify_stream(
        self,
        tasks: list[Task],
        settings: ClassifierSettings,
    ) -> AsyncIterator[ClassificationResult]:
        import asyncio
        label_map = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}
        pkg_map = {"openai": "openai", "anthropic": "anthropic"}
        key_name = label_map.get(self._provider, "API_KEY")
        pkg_name = pkg_map.get(self._provider, "패키지")

        if self._reason == "import_error":
            msg = (
                f"'{pkg_name}' 패키지가 설치되지 않았습니다. "
                f"pip install {pkg_name} 를 실행해 주세요."
            )
        else:
            msg = (
                f"{key_name}가 설정되지 않았습니다. "
                "설정 페이지에서 API Key를 입력해 주세요."
            )

        for task in tasks:
            yield ClassificationResult(
                task_id=task.id,
                label="미분류",
                reason=msg,
                confidence=0.0,
                provider=self._provider,
            )
            await asyncio.sleep(0)


# ── 팩토리 ────────────────────────────────────────────────────────────────────

def get_classifier(settings: ClassifierSettings, provider: str = "openai") -> BaseClassifier:
    """
    provider와 설정에 따라 적절한 분류기 인스턴스를 반환합니다.

    - provider="openai"     : OpenAI API Key 확인 → LLMClassifier
    - provider="anthropic"  : Anthropic API Key 확인 → AnthropicClassifier
    - API Key 없으면 → StubClassifier
    """
    if provider == "anthropic":
        api_key = (settings.anthropic_api_key or "").strip()
        env_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        has_key = bool(api_key) or bool(env_key)
        if not has_key:
            return StubClassifier("anthropic")
        try:
            from anthropic_classifier import AnthropicClassifier
            return AnthropicClassifier()
        except ImportError:
            return StubClassifier("anthropic", reason="import_error")

    else:  # openai (default)
        api_key = (settings.api_key or "").strip()
        env_key = os.environ.get("OPENAI_API_KEY", "").strip()
        has_key = bool(api_key) or bool(env_key)
        if not has_key:
            return StubClassifier("openai")
        try:
            from llm_classifier import LLMClassifier
            return LLMClassifier()
        except ImportError:
            return StubClassifier("openai", reason="import_error")
