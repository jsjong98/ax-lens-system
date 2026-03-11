"""
anthropic_classifier.py — Anthropic Claude API 기반 HR Task 분류기

사용 모델: claude-sonnet-4-6
  - Anthropic Messages API 사용 (system + user 메시지 구조)
  - llm_classifier.py의 동일한 시스템 프롬프트 재사용
  - 응답에서 JSON 파싱 (마크다운 코드 블록 포함 처리)
"""
from __future__ import annotations
import json
import os
import re
from typing import AsyncIterator

from anthropic import AsyncAnthropic

from classifier import BaseClassifier
from llm_classifier import build_system_prompt, build_user_prompt, _LABELS
from models import ClassificationResult, ClassifierSettings, Task


def _extract_json(text: str) -> dict:
    """Claude 응답 텍스트에서 JSON 객체를 추출합니다."""
    text = text.strip()
    # ```json ... ``` 또는 ``` ... ``` 블록 처리
    match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


class AnthropicClassifier(BaseClassifier):
    """Claude API를 사용하는 3단계 Knock-out + AI+Human 하이브리드 판정 분류기."""

    async def classify_stream(
        self,
        tasks: list[Task],
        settings: ClassifierSettings,
    ) -> AsyncIterator[ClassificationResult]:
        api_key = os.getenv("ANTHROPIC_API_KEY", "") or settings.anthropic_api_key
        if not api_key:
            raise ValueError(
                "Anthropic API 키가 없습니다. backend/.env 파일에 "
                "ANTHROPIC_API_KEY=sk-ant-... 를 설정해 주세요."
            )

        client = AsyncAnthropic(api_key=api_key)
        system_prompt = build_system_prompt(settings.criteria_prompt)

        for task in tasks:
            result = await self._call_single(
                client, task, system_prompt, settings.anthropic_model
            )
            yield result

    async def _call_single(
        self,
        client: AsyncAnthropic,
        task: Task,
        system_prompt: str,
        model: str = "claude-sonnet-4-6",
    ) -> ClassificationResult:
        from models import StageAnalysis
        user_prompt = build_user_prompt([task])

        try:
            response = await client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw = response.content[0].text
            data = _extract_json(raw)
            classified = data.get("tasks", [data])
            r = classified[0] if classified else {}

        except Exception as e:
            return ClassificationResult(
                task_id=task.id,
                label="미분류",
                reason=f"API 오류: {e}",
                confidence=0.0,
                provider="anthropic",
            )

        raw_label = r.get("label", "미분류")
        label = raw_label if raw_label in _LABELS else "미분류"

        input_types  = r.get("input_types", "")  if label == "AI 수행 가능" else ""
        output_types = r.get("output_types", "") if label == "AI 수행 가능" else ""

        return ClassificationResult(
            task_id=task.id,
            label=label,
            criterion=r.get("criterion", ""),
            stage1=StageAnalysis(
                passed=bool(r.get("stage1_pass", True)),
                note=str(r.get("stage1_note", "")),
            ),
            stage2=StageAnalysis(
                passed=bool(r.get("stage2_pass", True)),
                note=str(r.get("stage2_note", "")),
            ),
            stage3=StageAnalysis(
                passed=bool(r.get("stage3_pass", True)),
                note=str(r.get("stage3_note", "")),
            ),
            hybrid_check=bool(r.get("hybrid_check", False)),
            hybrid_note=str(r.get("hybrid_note", "")),
            input_types=input_types,
            output_types=output_types,
            reason=r.get("reason", ""),
            confidence=float(r.get("confidence", 0.5)),
            provider="anthropic",
        )
