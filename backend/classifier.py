"""
classifier.py — 분류기 추상 인터페이스 + StubClassifier

나중에 LLM 기준이 확정되면 llm_classifier.py 의 LLMClassifier 를 사용합니다.
분류기 선택 로직은 get_classifier() 팩토리 함수를 통해 관리합니다.
"""
from __future__ import annotations
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
        """
        Task 목록을 분류하고 결과를 비동기 스트림으로 반환합니다.
        진행 상황을 실시간으로 SSE로 전달하기 위해 스트림 방식을 사용합니다.
        """
        ...  # pragma: no cover


# ── StubClassifier — 분류 기준 미설정 시 사용 ─────────────────────────────────

class StubClassifier(BaseClassifier):
    """
    API Key가 없을 때 사용하는 더미 분류기.
    모든 Task를 "미분류"로 반환합니다.
    """

    async def classify_stream(
        self,
        tasks: list[Task],
        settings: ClassifierSettings,
    ) -> AsyncIterator[ClassificationResult]:
        import asyncio
        for task in tasks:
            yield ClassificationResult(
                task_id=task.id,
                label="미분류",
                reason="OpenAI API Key가 설정되지 않았습니다. 설정 페이지에서 API Key를 입력하거나 환경변수 OPENAI_API_KEY를 설정해 주세요.",
                confidence=0.0,
            )
            await asyncio.sleep(0)


# ── 팩토리 ────────────────────────────────────────────────────────────────────

def get_classifier(settings: ClassifierSettings) -> BaseClassifier:
    """
    설정에 따라 적절한 분류기 인스턴스를 반환합니다.

    - API Key(settings 또는 환경변수 OPENAI_API_KEY)가 있으면 → LLMClassifier
    - API Key가 없으면 → StubClassifier (더미)

    criteria_prompt는 선택 사항입니다.
    내장 Knock-out 기준은 LLMClassifier의 시스템 프롬프트에 항상 포함됩니다.
    """
    import os
    api_key = (settings.api_key or "").strip()
    env_key = os.environ.get("OPENAI_API_KEY", "").strip()
    has_key = bool(api_key) or bool(env_key)

    if not has_key:
        return StubClassifier()

    try:
        from llm_classifier import LLMClassifier
        return LLMClassifier()
    except ImportError:
        return StubClassifier()
