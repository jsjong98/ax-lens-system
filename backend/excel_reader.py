"""
excel_reader.py — 엑셀 파일에서 L5 Task 목록을 추출합니다.

시트 자동 감지 전략:
  1. 이름에 가이드/guide/작성 등이 포함된 시트는 제외
  2. 나머지 시트 중 열 I에서 L5 ID 패턴(숫자.숫자.숫자)이 가장 많이 발견되는 시트 선택
  3. 데이터 시작 행도 열 I의 첫 번째 유효한 ID 행을 스캔해 자동 결정
"""
from __future__ import annotations
import re
from pathlib import Path

import openpyxl

from models import Task

# ── 엑셀 열 인덱스 (1-based, openpyxl 기준) ────────────────────────────────
_COL = {
    # 프로세스 계층
    "l2_id":     2,   # B
    "l2_name":   3,   # C
    "l3_id":     4,   # D
    "l3_name":   5,   # E
    "l4_id":     6,   # F
    "l4_name":   7,   # G
    "l4_desc":   8,   # H  (없는 경우 빈 문자열)
    # L5 Task
    "l5_id":     9,   # I
    "l5_name":   10,  # J
    "l5_desc":   11,  # K
    "performer": 12,  # L  수행주체 (자유 텍스트)
    # A-1. 수행주체 체크박스
    "performer_executive": 13,  # M  임원
    "performer_hr":        14,  # N  HR
    "performer_manager":   15,  # O  현업 팀장
    "performer_member":    16,  # P  현업 구성원
    # D-1. Pain Point
    "pain_time":         17,  # Q  시간/속도
    "pain_accuracy":     18,  # R  정확성
    "pain_repetition":   19,  # S  반복/수작업
    "pain_data":         20,  # T  정보/데이터
    "pain_system":       21,  # U  시스템/도구
    "pain_communication":22,  # V  의사소통/협업
    "pain_other":        23,  # W  기타
    # E-2. Output 유형
    "output_system":        24,  # X  시스템 반영
    "output_document":      25,  # Y  문서/보고서
    "output_communication": 26,  # Z  커뮤니케이션
    "output_decision":      27,  # AA 의사결정
    "output_other":         28,  # AB 기타
    # F-1. 업무 판단 로직
    "logic_rule_based":     29,  # AC Rule-based
    "logic_human_judgment": 30,  # AD 사람 판단
    "logic_mixed":          31,  # AE 혼합
    # F-2~F-3
    "remark":                  32,  # AF 비고
    "standard_or_specialized": 33,  # AG 표준 vs 특화
}

# ── 시트 자동 감지 ────────────────────────────────────────────────────────────

# 데이터가 없는 가이드/설명 시트 식별 키워드
_GUIDE_KEYWORDS = {"가이드", "guide", "작성", "설명", "manual", "instruction", "readme", "index"}

# L5 ID 패턴: "1.1.1", "1.1.1.1", "2.3.4.5" 등 숫자.숫자.숫자로 시작
_L5_ID_RE = re.compile(r"^\d+\.\d+\.\d+")

# L5 ID가 위치하는 열 (I = 9번째, 0-indexed = 8)
_L5_ID_COL_IDX = 8   # 0-based (openpyxl values_only row 기준)
_L5_ID_COL_1B  = 9   # 1-based  (openpyxl cell 직접 접근 기준)

# 시트 스캔 시 확인할 최대 행 수 (헤더 영역 포함)
_SCAN_ROWS = 50


def _is_guide_sheet(name: str) -> bool:
    lower = name.lower()
    return any(kw in lower for kw in _GUIDE_KEYWORDS)


def _score_sheet(ws) -> int:
    """시트에서 L5 ID 패턴이 몇 개 발견되는지 반환 (스캔은 최대 _SCAN_ROWS행)."""
    count = 0
    for row in ws.iter_rows(
        min_row=1, max_row=_SCAN_ROWS,
        min_col=_L5_ID_COL_1B, max_col=_L5_ID_COL_1B,
        values_only=True,
    ):
        val = str(row[0]).strip() if row[0] is not None else ""
        if _L5_ID_RE.match(val):
            count += 1
    return count


def _find_data_sheet(wb):
    """
    가이드 시트를 제외하고 L5 Task 데이터가 가장 많은 시트를 반환합니다.
    동점이면 시트 목록 순서가 앞선 것을 선택합니다.
    """
    best_ws = None
    best_score = -1

    for name in wb.sheetnames:
        if _is_guide_sheet(name):
            print(f"[sheet] '{name}' — 가이드 시트 제외")
            continue
        ws = wb[name]
        score = _score_sheet(ws)
        print(f"[sheet] '{name}' — L5 ID {score}개 감지")
        if score > best_score:
            best_score = score
            best_ws = ws

    if best_ws is None:
        # 모두 가이드로 판단된 경우 첫 시트로 폴백
        print("[sheet] 적합한 시트 없음 — 첫 번째 시트로 폴백")
        return wb.worksheets[0]

    print(f"[sheet] 선택됨: '{best_ws.title}' (L5 ID {best_score}개)")
    return best_ws


def _find_data_start_row(ws) -> int:
    """
    열 I(L5 ID)에서 첫 번째 유효한 L5 ID가 있는 행 번호를 반환합니다.
    발견하지 못하면 기본값 10을 반환합니다.
    """
    for row in ws.iter_rows(
        min_row=1, max_row=100,
        min_col=_L5_ID_COL_1B, max_col=_L5_ID_COL_1B,
        values_only=True,
    ):
        # iter_rows는 (value,) 튜플을 반환하므로 row[0]
        pass  # iter_rows는 행 번호를 직접 주지 않으므로 enumerate 사용

    start = 10
    for r_idx, row in enumerate(
        ws.iter_rows(
            min_row=1, max_row=100,
            min_col=_L5_ID_COL_1B, max_col=_L5_ID_COL_1B,
            values_only=True,
        ),
        start=1,
    ):
        val = str(row[0]).strip() if row[0] is not None else ""
        if _L5_ID_RE.match(val):
            start = r_idx
            break

    print(f"[sheet] 데이터 시작 행: {start}")
    return start


def _find_excel(base_dir: Path) -> Path:
    """base_dir 또는 상위 디렉토리에서 엑셀 파일을 자동 탐색."""
    # 상위 디렉토리 포함해서 탐색
    for search_dir in [base_dir, base_dir.parent]:
        xlsx_files = list(search_dir.glob("*.xlsx"))
        if xlsx_files:
            # As-Is 파일 우선 선택
            for f in xlsx_files:
                if "As-is" in f.name or "as-is" in f.name.lower():
                    return f
            return xlsx_files[0]
    raise FileNotFoundError(
        f"엑셀 파일을 찾을 수 없습니다. 경로: {base_dir}"
    )


def _cell(row: tuple, col: int) -> str:
    """1-based 열 번호로 행에서 값 추출 후 문자열 변환."""
    val = row[col - 1]
    if val is None:
        return ""
    return str(val).strip()


def list_sheets(excel_path: str | Path) -> list[dict]:
    """
    엑셀 파일의 시트 목록과 각 시트의 L5 Task 개수를 반환합니다.

    Returns:
        [{"name": "시트1", "task_count": 42, "is_guide": False, "recommended": True}, ...]
    """
    excel_path = Path(excel_path)
    if not excel_path.exists():
        raise FileNotFoundError(f"파일 없음: {excel_path}")

    wb = openpyxl.load_workbook(str(excel_path), data_only=True, read_only=True)

    best_score = -1
    best_name = ""
    sheets = []

    for name in wb.sheetnames:
        is_guide = _is_guide_sheet(name)
        ws = wb[name]
        score = _score_sheet(ws) if not is_guide else 0
        if score > best_score:
            best_score = score
            best_name = name
        sheets.append({
            "name": name,
            "task_count": score,
            "is_guide": is_guide,
            "recommended": False,
        })

    # 추천 시트 마킹
    for s in sheets:
        if s["name"] == best_name and best_score > 0:
            s["recommended"] = True

    wb.close()
    return sheets


def load_tasks(
    excel_path: str | Path | None = None,
    sheet_name: str | None = None,
) -> list[Task]:
    """
    엑셀 파일을 읽어 Task 목록을 반환합니다.

    Args:
        excel_path: 엑셀 파일 경로. None이면 현재 파일 기준으로 자동 탐색.
        sheet_name: 시트 이름. None이면 자동 감지.
    """
    if excel_path is None:
        base_dir = Path(__file__).parent
        excel_path = _find_excel(base_dir)

    excel_path = Path(excel_path)
    if not excel_path.exists():
        raise FileNotFoundError(f"파일 없음: {excel_path}")

    wb = openpyxl.load_workbook(str(excel_path), data_only=True, read_only=True)

    if sheet_name and sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        print(f"[sheet] 사용자 지정 시트: '{sheet_name}'")
    else:
        ws = _find_data_sheet(wb)
    data_start_row = _find_data_start_row(ws)

    # read_only 모드에서는 ws를 재사용할 수 없으므로 다시 열기
    wb.close()
    wb = openpyxl.load_workbook(str(excel_path), data_only=True, read_only=True)
    ws = wb[ws.title]

    tasks: list[Task] = []
    seen_ids: dict[str, int] = {}   # ID 중복 카운터

    for row in ws.iter_rows(
        min_row=data_start_row,
        max_row=ws.max_row,
        values_only=True,
    ):
        l5_id = _cell(row, _COL["l5_id"])
        if not l5_id:
            continue

        # 중복 ID 처리: 두 번째부터 접미사 붙이기 (예: 1.8.1.2_2)
        if l5_id in seen_ids:
            seen_ids[l5_id] += 1
            unique_id = f"{l5_id}_{seen_ids[l5_id]}"
            print(f"[excel] 중복 ID 발견: '{l5_id}' → '{unique_id}'로 변경")
        else:
            seen_ids[l5_id] = 1
            unique_id = l5_id

        tasks.append(
            Task(
                id=unique_id,
                l2_id=_cell(row, _COL["l2_id"]),
                l2=_cell(row, _COL["l2_name"]),
                l3_id=_cell(row, _COL["l3_id"]),
                l3=_cell(row, _COL["l3_name"]),
                l4_id=_cell(row, _COL["l4_id"]),
                l4=_cell(row, _COL["l4_name"]),
                l4_description=_cell(row, _COL["l4_desc"]),
                name=_cell(row, _COL["l5_name"]),
                description=_cell(row, _COL["l5_desc"]),
                performer=_cell(row, _COL["performer"]),
                # A-1. 수행주체 체크박스
                performer_executive=_cell(row, _COL["performer_executive"]),
                performer_hr=_cell(row, _COL["performer_hr"]),
                performer_manager=_cell(row, _COL["performer_manager"]),
                performer_member=_cell(row, _COL["performer_member"]),
                # D-1. Pain Point
                pain_time=_cell(row, _COL["pain_time"]),
                pain_accuracy=_cell(row, _COL["pain_accuracy"]),
                pain_repetition=_cell(row, _COL["pain_repetition"]),
                pain_data=_cell(row, _COL["pain_data"]),
                pain_system=_cell(row, _COL["pain_system"]),
                pain_communication=_cell(row, _COL["pain_communication"]),
                pain_other=_cell(row, _COL["pain_other"]),
                # E-2. Output
                output_system=_cell(row, _COL["output_system"]),
                output_document=_cell(row, _COL["output_document"]),
                output_communication=_cell(row, _COL["output_communication"]),
                output_decision=_cell(row, _COL["output_decision"]),
                output_other=_cell(row, _COL["output_other"]),
                # F-1. 업무 판단 로직
                logic_rule_based=_cell(row, _COL["logic_rule_based"]),
                logic_human_judgment=_cell(row, _COL["logic_human_judgment"]),
                logic_mixed=_cell(row, _COL["logic_mixed"]),
                # F-2~F-3
                remark=_cell(row, _COL["remark"]),
                standard_or_specialized=_cell(row, _COL["standard_or_specialized"]),
            )
        )

    wb.close()
    return tasks
