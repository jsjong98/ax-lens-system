"""
tobe_excel_exporter.py — To-Be 설계 결과를 As-Is 템플릿 포맷 Excel로 반출

생성 규칙:
  - 사용자 업로드 As-Is 템플릿 xlsx를 베이스로 복사
  - 데이터 행(row 10+)은 기존 내용 제거 후 To-Be L5 Task로 재작성
  - 각 행 = 하나의 To-Be L5 Task:
      · Junior AI task (AI 파트) — performer = agent 이름, cls_final_label = 원본 분류 유지
      · HR 검토 노드 (AI+Human의 Human 파트) — performer = HR 담당자
      · 보존된 As-Is Human L5 — 그대로
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from copy import copy as _copy
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Border, Side

# 데이터 시작 행 (헤더 4~9, 데이터는 10부터)
_DATA_START_ROW = 10

# As-Is 템플릿의 열 레이아웃 (1-based)
_COL = {
    "l2_id":    2,   # B
    "l2_name":  3,   # C
    "l3_id":    4,   # D
    "l3_name":  5,   # E
    "l4_id":    6,   # F
    "l4_name":  7,   # G
    "l4_desc":  8,   # H
    "l5_id":    9,   # I
    "l5_name":  10,  # J
    "l5_desc":  11,  # K
    "performer":              12,  # L (자유 텍스트)
    "performer_executive":    13,  # M ●
    "performer_hr":           14,  # N ●
    "performer_manager":      15,  # O ●
    "performer_member":       16,  # P ●
    "cls_1st_label":  34,  # AH
    "cls_1st_knockout": 35,  # AI
    "cls_1st_reason": 36,  # AJ
    "cls_1st_ai_prereq": 37, # AK
    "cls_doosan_label": 38,  # AL
    "cls_doosan_feedback": 39, # AM
    "cls_final_label": 40,  # AN
    "cls_final_feedback": 41,  # AO
}


def _find_data_sheet(wb) -> Any | None:
    """As-Is 데이터가 들어있는 메인 시트를 찾아 반환."""
    for sn in wb.sheetnames:
        # 우선 '3. As-Is 분석' 같은 정규 시트 우선
        if "As-Is" in sn or "as-is" in sn.lower() or "분석" in sn:
            return wb[sn]
    # fallback: 가이드 제외 첫 시트
    for sn in wb.sheetnames:
        if "가이드" in sn or "guide" in sn.lower() or "count" in sn.lower():
            continue
        return wb[sn]
    return None


def _clear_data_rows(ws) -> None:
    """데이터 시작 행부터 마지막까지 비움 (스타일 유지)."""
    max_row = ws.max_row
    if max_row < _DATA_START_ROW:
        return
    for r in range(_DATA_START_ROW, max_row + 1):
        for c in range(1, min(ws.max_column + 1, 100)):
            cell = ws.cell(r, c)
            if cell.value is not None and not isinstance(cell, openpyxl.cell.cell.MergedCell):
                cell.value = None


def _get_task_row(task: dict) -> dict[str, str]:
    """To-Be task 한 개(dict)를 엑셀 행 dict로 매핑."""
    tid = str(task.get("task_id") or "").strip()
    tparts = tid.split(".") if tid else []

    l2_id = ".".join(tparts[:1]) if len(tparts) >= 1 else task.get("l2_id", "")
    l3_id = ".".join(tparts[:2]) if len(tparts) >= 2 else task.get("l3_id", "")
    l4_id = ".".join(tparts[:3]) if len(tparts) >= 3 else task.get("l4_id", "")
    l5_id = tid

    return {
        "l2_id": l2_id,
        "l2_name": task.get("l2", ""),
        "l3_id": l3_id,
        "l3_name": task.get("l3", ""),
        "l4_id": l4_id,
        "l4_name": task.get("l4", ""),
        "l5_id": l5_id,
        "l5_name": task.get("task_name", ""),
        "l5_desc": task.get("ai_role", "") or task.get("human_role", ""),
    }


def _write_row(ws, row: int, values: dict[str, str | None]) -> None:
    """dict의 (key, value) → 정의된 열에 value를 씀."""
    for key, val in values.items():
        col = _COL.get(key)
        if col is None:
            continue
        try:
            ws.cell(row, col).value = val if val is not None else ""
        except Exception:
            # merged cell일 수 있음 — 무시
            pass


def export_tobe_excel(
    template_path: str | Path,
    output_path: str | Path,
    step2_cache: dict,
    classification: dict,
    excel_tasks: list,
    wf_tobe_flow_cache: dict | None = None,
) -> None:
    """
    To-Be Excel 반출 메인 엔트리.

    Args:
        template_path: 사용자가 업로드한 As-Is 템플릿 xlsx 경로
        output_path: 반출할 xlsx 경로
        step2_cache: _wf_step2_cache (agents + assigned_tasks)
        classification: _wf_classification (엑셀 분류 + hybrid_note)
        excel_tasks: _wf_excel_tasks (원본 Task 리스트)
        wf_tobe_flow_cache: 선택적 — 이미 생성된 To-Be Flow dict
    """
    template_path = Path(template_path)
    output_path = Path(output_path)
    if not template_path.exists():
        raise FileNotFoundError(f"템플릿 파일을 찾을 수 없습니다: {template_path}")

    wb = openpyxl.load_workbook(template_path)
    ws = _find_data_sheet(wb)
    if ws is None:
        raise RuntimeError("As-Is 데이터 시트를 템플릿에서 찾지 못했습니다.")

    # 데이터 행 초기화
    _clear_data_rows(ws)

    # 엑셀 task를 id 기준 인덱스
    task_by_id: dict[str, Any] = {t.id: t for t in (excel_tasks or [])}

    row = _DATA_START_ROW

    # ── 1. Junior AI task (AI 파트) 쓰기 ──
    for agent in step2_cache.get("agents", []):
        atype = agent.get("agent_type", "")
        if atype not in ("Senior AI", "Junior AI"):
            continue
        agent_name = agent.get("agent_name", "") or ""
        for t in agent.get("assigned_tasks", []):
            tid = str(t.get("task_id") or "").strip()
            cls = classification.get(tid, {}) if classification else {}
            orig_label = cls.get("label", "")
            orig_task = task_by_id.get(tid)

            # 계층 정보 보강 — 원본 task에서 가져오기
            base = {
                "l2_id": (orig_task.l2_id if orig_task else "") or "",
                "l2_name": (orig_task.l2 if orig_task else "") or t.get("l2", ""),
                "l3_id": (orig_task.l3_id if orig_task else "") or "",
                "l3_name": (orig_task.l3 if orig_task else "") or t.get("l3", ""),
                "l4_id": (orig_task.l4_id if orig_task else "") or "",
                "l4_name": (orig_task.l4 if orig_task else "") or t.get("l4", ""),
            }

            # AI 파트 행
            ai_part_desc = t.get("ai_role", "") or t.get("task_name", "")
            values = {
                **base,
                "l5_id": tid,
                "l5_name": f"[AI] {t.get('task_name', '')}",
                "l5_desc": ai_part_desc,
                "performer": f"{atype} — {agent_name}",
                "performer_executive": "",
                "performer_hr": "",
                "performer_manager": "",
                "performer_member": "",
                "cls_1st_label":    cls.get("label", "AI"),
                "cls_1st_knockout": cls.get("criterion", ""),
                "cls_1st_reason":   cls.get("reason", ""),
                "cls_1st_ai_prereq": cls.get("ai_prerequisites", ""),
                "cls_doosan_label": cls.get("label", ""),
                "cls_doosan_feedback": cls.get("feedback", ""),
                "cls_final_label":  orig_label or "AI",
                "cls_final_feedback": cls.get("feedback", ""),
            }
            _write_row(ws, row, values)
            row += 1

            # AI+Human 인 경우: Human 파트 별도 행 추가
            is_hybrid = (orig_label == "AI + Human") or bool(t.get("human_role"))
            if is_hybrid:
                human_part = t.get("human_role", "").strip()
                if not human_part and cls.get("hybrid_note"):
                    # hybrid_note에서 Human 파트 추출
                    hn = cls["hybrid_note"]
                    if "Human 파트:" in hn:
                        human_part = hn.split("Human 파트:", 1)[1].strip()

                if human_part:
                    values_h = {
                        **base,
                        "l5_id": tid,
                        "l5_name": f"[Human] {t.get('task_name', '')} 검토",
                        "l5_desc": human_part,
                        "performer": "HR 담당자",
                        "performer_hr": "●",
                        "cls_1st_label": cls.get("label", "AI + Human"),
                        "cls_1st_knockout": cls.get("criterion", ""),
                        "cls_1st_reason": cls.get("reason", ""),
                        "cls_1st_ai_prereq": cls.get("ai_prerequisites", ""),
                        "cls_doosan_label": cls.get("label", ""),
                        "cls_doosan_feedback": cls.get("feedback", ""),
                        "cls_final_label": "Human",
                        "cls_final_feedback": cls.get("feedback", ""),
                    }
                    _write_row(ws, row, values_h)
                    row += 1

    # ── 2. Human으로 분류된 As-Is L5 (AI Agent에 미포함) — 그대로 보존 ──
    agent_task_ids: set[str] = set()
    for agent in step2_cache.get("agents", []):
        for t in agent.get("assigned_tasks", []):
            agent_task_ids.add(str(t.get("task_id") or ""))

    for t in (excel_tasks or []):
        cls = classification.get(t.id, {}) if classification else {}
        label = cls.get("label", "")
        if label != "Human":
            continue
        if t.id in agent_task_ids:
            continue
        values = {
            "l2_id": t.l2_id or "", "l2_name": t.l2,
            "l3_id": t.l3_id or "", "l3_name": t.l3,
            "l4_id": t.l4_id or "", "l4_name": t.l4,
            "l5_id": t.id,
            "l5_name": f"[Human] {t.name}",
            "l5_desc": t.description or "",
            "performer": t.performer or "HR 담당자",
            "performer_executive": t.performer_executive or "",
            "performer_hr": t.performer_hr or "",
            "performer_manager": t.performer_manager or "",
            "performer_member": t.performer_member or "",
            "cls_1st_label": label,
            "cls_1st_knockout": cls.get("criterion", ""),
            "cls_1st_reason": cls.get("reason", ""),
            "cls_final_label": label,
            "cls_final_feedback": cls.get("feedback", ""),
        }
        _write_row(ws, row, values)
        row += 1

    wb.save(output_path)
