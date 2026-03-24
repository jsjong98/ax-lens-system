"""
data_store.py — E2E 데이터 영속 저장소

모든 단계의 결과를 JSON 파일로 저장하여:
1. 서버 재시작 시 자동 복원
2. LLM 재호출 없이 이전 결과 재사용
3. 단계 간 데이터 흐름 보존

저장 파일:
- workflow_result.json       : Workflow (As-Is → To-Be) 결과
- new_workflow_result.json   : New Workflow 결과
- project_definition.json   : 과제 정의서
- project_design.json       : 과제 설계서
- nw_tasks.json              : New Workflow 전용 Task 캐시
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).parent
_FILES = {
    "workflow":             _DATA_DIR / "workflow_result.json",
    "new_workflow":         _DATA_DIR / "new_workflow_result.json",
    "project_definition":   _DATA_DIR / "project_definition.json",
    "project_design":       _DATA_DIR / "project_design.json",
    "nw_tasks":             _DATA_DIR / "nw_tasks.json",
}


def save_data(key: str, data: dict | list) -> None:
    """데이터를 JSON 파일로 저장합니다."""
    path = _FILES.get(key)
    if not path:
        return
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    except Exception as e:
        print(f"[data_store] 저장 실패 ({key}): {e}")


def load_data(key: str) -> dict | list | None:
    """JSON 파일에서 데이터를 로드합니다. 없으면 None."""
    path = _FILES.get(key)
    if not path or not path.exists():
        return None
    try:
        text = path.read_text("utf-8")
        return json.loads(text)
    except Exception as e:
        print(f"[data_store] 로드 실패 ({key}): {e}")
        return None


def clear_data(key: str) -> None:
    """저장된 데이터를 삭제합니다."""
    path = _FILES.get(key)
    if path and path.exists():
        path.unlink(missing_ok=True)


def get_all_keys() -> list[str]:
    """사용 가능한 데이터 키 목록."""
    return list(_FILES.keys())


def get_saved_status() -> dict[str, bool]:
    """각 데이터의 저장 여부를 반환합니다."""
    return {key: path.exists() for key, path in _FILES.items()}
