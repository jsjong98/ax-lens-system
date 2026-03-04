"""
llm_classifier.py — Knock-out 기반 HR Task 분류기 (AI 수행 가능 / 인간 수행 필요)

[분류 결과 2종]
  인간 수행 필요 — Knock-out 기준(규제·확정승인·상호작용) 중 하나라도 해당
  AI 수행 가능   — 위 기준 모두 해당 없음. Input/Output 유형은 부가 정보로 제공

[분석 구조 (배치 단일 호출)]
  Phase 1: Knock-out 검사 → 인간 수행 필요 여부 확정
  Phase 2: AI 수행 가능 태스크의 Input/Output 유형 분석 (부가 컨텍스트)
"""
from __future__ import annotations
import asyncio
import json
import os
from typing import AsyncIterator

from openai import AsyncOpenAI

from classifier import BaseClassifier
from models import ClassificationResult, ClassifierSettings, Task

# ─────────────────────────────────────────────────────────────────────────────
# 시스템 프롬프트
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """당신은 HR 업무 자동화 전략 전문가입니다.
주어진 HR Task들을 아래 기준에 따라 "AI 수행 가능" 또는 "인간 수행 필요"로 분류합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【Knock-out 평가 기준】 — 해당하면 즉시 "인간 수행 필요"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▌[1단계] 규제 측면 (AI 기본법 · EU AI Act)  ← 가장 먼저 확인
  ① 법적 금지 — AI 활용 자체를 불허하는 영역
     예: 화상면접 감정 분석, CCTV 얼굴 DB 구축
  ② 법적 감독 의무 (고위험 AI) — 채용·승진·성과 등 개인 권리에 영향을 미치는 영역에서
     인간의 최종 감독·확정이 의무화된 업무
     예: 최종 합격자 선정, 성과 등급 확정, 승진 대상자 확정

▌[2단계] 업무 측면 — 확정/승인 업무 (책임귀속성)
  ③ 조직 기준·제도 확정 — 전사/사업장 적용 정책·기준을 확정
     예: 평가 제도 개편안 확정, 보상 정책 확정, 취업규칙 변경
  ④ 고영향·비가역 의사결정 — 법적 분쟁·노사 갈등 등 복구 비용이 현저히 큰 결정
     예: 직장 내 괴롭힘 조치 확정, 차별 이슈 결론, 징계 확정

▌[3단계] 업무 측면 — 상호작용 업무 (관계·맥락·윤리·변화)
  ⑤ 공감·심리안전 — 개인 심리 회복을 위한 공감 기반 대인 상호작용
     예: 복직 면담, 퇴직 면담, 육아휴직 복직자 면담
  ⑥ 협상·중재 — 상충하는 이해관계의 현장 협상 및 중재
     예: 노사 교섭, 처우 협의, 고용조건 협의
  ⑦ 공정성 설득 — 결정의 정당성 설명·감정 조율로 수용 유도
     예: 평가등급 이의제기 대응, 승진 누락 이의제기 대응
  ⑧ 변화/리더십 정착 — 비전 제시로 조직 행동 변화 촉진
     예: 제도 런칭 설명회, 리더 코칭, 문화 내재화 활동
  ⑨ 창의적 설계 — 새 제도·구조를 만드는 집단 창작
     예: 직무/조직/제도 설계 워크숍, 신규 복리후생 기획

→ ①~⑨ 중 하나라도 해당하면 → "인간 수행 필요"
→ 모두 해당 없으면 → "AI 수행 가능"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【AI 수행 가능 태스크 — Input/Output 유형 분석 (부가 정보)】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"AI 수행 가능"으로 분류된 태스크에 한해 아래 유형을 분석해 input_types, output_types 필드에 기재합니다.

Input 유형 (해당하는 것을 쉼표로 나열):
  · 시스템 데이터 — HR시스템·ERP에서 조회/추출하는 데이터
  · 문서/서류     — 신청서·증명서·이력서·계약서 등 문서 형태
  · 외부 정보     — 채용플랫폼·4대보험·벤치마크 등 외부 기관 정보
  · 구두/메일 요청 — 메일·메신저·구두 지시 형태의 요청

Output 유형 (해당하는 것을 쉼표로 나열):
  · 시스템 반영   — HR시스템·ERP 데이터 입력/수정/반영
  · 문서/보고서   — 보고서·명세서·증명서·Excel 등 문서 산출물
  · 커뮤니케이션  — 안내 메일·공지·회신·알림 등 소통 형태 산출물
  · 의사결정      — 승인·확정·판정 등 결정 형태 산출물

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【출력 형식】 JSON만 출력, 다른 텍스트 없이
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

각 Task에 대해 3단계를 순서대로 평가하고 아래 형식으로 출력합니다.
인간 수행 필요 판정 시 해당 단계에서 즉시 확정하고 이후 단계는 건너뜁니다.

{
  "tasks": [
    {
      "id": "L5_ID",
      "stage1_pass": true 또는 false,
      "stage1_note": "1단계 판단 근거 (통과 시 빈 문자열 가능, 탈락 시 어떤 기준 ①②에 해당하는지)",
      "stage2_pass": true 또는 false,
      "stage2_note": "2단계 판단 근거 (통과 시 빈 문자열 가능, 탈락 시 어떤 기준 ③④에 해당하는지)",
      "stage3_pass": true 또는 false,
      "stage3_note": "3단계 판단 근거 (통과 시 빈 문자열 가능, 탈락 시 어떤 기준 ⑤~⑨에 해당하는지)",
      "label": "AI 수행 가능" 또는 "인간 수행 필요",
      "criterion": "1단계: 규제 측면" | "2단계: 확정/승인 업무" | "3단계: 상호작용 업무" | "",
      "input_types": "시스템 데이터, 문서/서류" (AI 수행 가능 시만 기재, 인간 수행 필요 시 ""),
      "output_types": "시스템 반영, 문서/보고서" (AI 수행 가능 시만 기재, 인간 수행 필요 시 ""),
      "reason": "최종 판단 근거 한국어 60자 이내",
      "confidence": 0.0 ~ 1.0
    }
  ]
}
"""

_EXTRA_CRITERIA_HEADER = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【추가 분류 기준】 (사용자 정의)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

_LABELS = {"AI 수행 가능", "인간 수행 필요"}


def build_system_prompt(extra_criteria: str = "") -> str:
    if extra_criteria.strip():
        return _SYSTEM_PROMPT + _EXTRA_CRITERIA_HEADER + extra_criteria.strip()
    return _SYSTEM_PROMPT


def _checked(value: str) -> bool:
    """체크박스 열: 값이 있으면 체크된 것으로 간주."""
    return bool(value and value.strip())


def build_user_prompt(tasks: list[Task]) -> str:
    lines = ["다음 HR Task들을 3개 Phase에 따라 순서대로 분석해 주세요:\n"]
    for t in tasks:
        lines.append(f"[ID: {t.id}]")
        lines.append(f"  계층: {t.l2} > {t.l3} > {t.l4}")
        lines.append(f"  Task명: {t.name}")
        if t.description:
            lines.append(f"  설명: {t.description[:250]}")
        if t.performer:
            lines.append(f"  수행주체(텍스트): {t.performer[:180]}")

        # A-1. 수행주체 체크박스
        performer_checked = [
            label for label, val in [
                ("임원", t.performer_executive),
                ("HR", t.performer_hr),
                ("현업 팀장", t.performer_manager),
                ("현업 구성원", t.performer_member),
            ] if _checked(val)
        ]
        if performer_checked:
            lines.append(f"  수행주체(체크): {', '.join(performer_checked)}")

        # D-1. Pain Point
        pain_checked = [
            label for label, val in [
                ("시간/속도", t.pain_time),
                ("정확성", t.pain_accuracy),
                ("반복/수작업", t.pain_repetition),
                ("정보/데이터", t.pain_data),
                ("시스템/도구", t.pain_system),
                ("의사소통/협업", t.pain_communication),
                ("기타", t.pain_other),
            ] if _checked(val)
        ]
        if pain_checked:
            lines.append(f"  Pain Point: {', '.join(pain_checked)}")

        # E-2. Output
        output_checked = [
            label for label, val in [
                ("시스템 반영", t.output_system),
                ("문서/보고서", t.output_document),
                ("커뮤니케이션", t.output_communication),
                ("의사결정", t.output_decision),
                ("기타", t.output_other),
            ] if _checked(val)
        ]
        if output_checked:
            lines.append(f"  Output 유형: {', '.join(output_checked)}")

        # F-1. 업무 판단 로직
        logic_checked = [
            label for label, val in [
                ("Rule-based(규칙 기반)", t.logic_rule_based),
                ("사람 판단", t.logic_human_judgment),
                ("혼합", t.logic_mixed),
            ] if _checked(val)
        ]
        if logic_checked:
            lines.append(f"  업무 판단 로직: {', '.join(logic_checked)}")

        if t.standard_or_specialized:
            lines.append(f"  표준/특화 구분: {t.standard_or_specialized}")
        if t.remark:
            lines.append(f"  비고: {t.remark[:120]}")

        lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# LLM 분류기
# ─────────────────────────────────────────────────────────────────────────────

class LLMClassifier(BaseClassifier):
    """3단계 파이프라인 기반 OpenAI 분류기."""

    async def classify_stream(
        self,
        tasks: list[Task],
        settings: ClassifierSettings,
    ) -> AsyncIterator[ClassificationResult]:
        # API Key: .env > settings > 환경변수 순으로 탐색
        api_key = os.getenv("OPENAI_API_KEY", "") or settings.api_key
        if not api_key:
            raise ValueError(
                "OpenAI API 키가 없습니다. backend/.env 파일에 "
                "OPENAI_API_KEY=sk-... 를 설정해 주세요."
            )

        client = AsyncOpenAI(api_key=api_key)
        system_prompt = build_system_prompt(settings.criteria_prompt)

        # Task 1개씩 처리 → 실시간 진행률, 안정적 분석
        for task in tasks:
            result = await self._call_single(client, task, system_prompt)
            yield result

    async def _call_single(
        self,
        client: AsyncOpenAI,
        task: Task,
        system_prompt: str,
    ) -> ClassificationResult:
        """태스크 1개를 분류하고 3단계 분석 결과를 반환합니다."""
        from models import StageAnalysis
        user_prompt = build_user_prompt([task])

        try:
            response = await client.chat.completions.create(
                model="gpt-5.2",
                temperature=0.0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            data = json.loads(raw)
            # 단일 태스크 응답: tasks 배열의 첫 번째 원소 사용
            classified = data.get("tasks", [data])
            r = classified[0] if classified else {}

        except Exception as e:
            return ClassificationResult(
                task_id=task.id,
                label="미분류",
                reason=f"API 오류: {e}",
                confidence=0.0,
            )

        raw_label = r.get("label", "미분류")
        label = raw_label if raw_label in _LABELS else "미분류"

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
            input_types=r.get("input_types", ""),
            output_types=r.get("output_types", ""),
            reason=r.get("reason", ""),
            confidence=float(r.get("confidence", 0.5)),
        )
