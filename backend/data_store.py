"""
data_store.py — 파일별 E2E 데이터 영속 저장소

업로드된 파일마다 별도 폴더를 생성하여 모든 결과를 보존합니다.
이전에 처리한 파일의 결과를 다시 로드할 수 있습니다.

구조:
  backend/data/
    {파일명}/
      results_openai.json
      results_anthropic.json
      new_workflow_result.json
      project_definition.json
      project_design.json
      meta.json  (업로드 시각, task 수 등)

  backend/
    current_project.json  (현재 활성 프로젝트)
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

_BASE_DIR = Path(__file__).parent / "data"
_BASE_DIR.mkdir(exist_ok=True)

_CURRENT_FILE = Path(__file__).parent / "current_project.json"

# 데이터 키 목록
DATA_KEYS = [
    "results_openai",
    "results_anthropic",
    "workflow_result",
    "new_workflow_result",
    "project_definition",
    "project_design",
]


def _safe_dirname(filename: str) -> str:
    """파일명을 안전한 디렉토리명으로 변환."""
    name = Path(filename).stem
    return re.sub(r'[^\w가-힣\-.]', '_', name)


def _project_dir(filename: str) -> Path:
    """파일별 프로젝트 디렉토리 경로."""
    d = _BASE_DIR / _safe_dirname(filename)
    d.mkdir(exist_ok=True)
    return d


# ── 현재 프로젝트 관리 ────────────────────────────────────────────────────────

def get_current_project() -> str | None:
    """현재 활성 프로젝트(파일명) 반환."""
    if _CURRENT_FILE.exists():
        try:
            data = json.loads(_CURRENT_FILE.read_text("utf-8"))
            return data.get("filename")
        except Exception:
            pass
    return None


def set_current_project(filename: str) -> None:
    """현재 활성 프로젝트 설정."""
    _CURRENT_FILE.write_text(
        json.dumps({"filename": filename, "set_at": datetime.now().isoformat()},
                   ensure_ascii=False),
        "utf-8",
    )
    # meta.json 업데이트
    meta_path = _project_dir(filename) / "meta.json"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text("utf-8"))
        except Exception:
            pass
    meta["filename"] = filename
    meta["last_accessed"] = datetime.now().isoformat()
    if "created_at" not in meta:
        meta["created_at"] = datetime.now().isoformat()
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), "utf-8")


# ── 파일별 데이터 저장/로드 ───────────────────────────────────────────────────

def save_data(key: str, data: dict | list, filename: str | None = None) -> None:
    """데이터를 현재 프로젝트 폴더에 JSON으로 저장."""
    fn = filename or get_current_project()
    if not fn:
        # fallback: 기존 방식 (루트에 저장)
        fallback = Path(__file__).parent / f"{key}.json"
        fallback.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        return
    path = _project_dir(fn) / f"{key}.json"
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    except Exception as e:
        print(f"[data_store] 저장 실패 ({key}, {fn}): {e}")


def load_data(key: str, filename: str | None = None) -> dict | list | None:
    """현재 프로젝트 폴더에서 데이터 로드. 없으면 None."""
    fn = filename or get_current_project()
    if not fn:
        # fallback
        fallback = Path(__file__).parent / f"{key}.json"
        if fallback.exists():
            try:
                return json.loads(fallback.read_text("utf-8"))
            except Exception:
                pass
        return None
    path = _project_dir(fn) / f"{key}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception as e:
        print(f"[data_store] 로드 실패 ({key}, {fn}): {e}")
        return None


def clear_data(key: str, filename: str | None = None) -> None:
    """저장된 데이터 삭제."""
    fn = filename or get_current_project()
    if not fn:
        return
    path = _project_dir(fn) / f"{key}.json"
    if path.exists():
        path.unlink(missing_ok=True)


# ── 프로젝트 목록 / 히스토리 ──────────────────────────────────────────────────

def list_projects() -> list[dict]:
    """저장된 모든 프로젝트 목록 반환."""
    projects = []
    if not _BASE_DIR.exists():
        return projects

    for d in sorted(_BASE_DIR.iterdir()):
        if not d.is_dir():
            continue
        meta_path = d / "meta.json"
        meta = {"dirname": d.name}
        if meta_path.exists():
            try:
                meta.update(json.loads(meta_path.read_text("utf-8")))
            except Exception:
                pass

        # 어떤 결과가 저장되어 있는지 확인
        saved = {}
        for key in DATA_KEYS:
            saved[key] = (d / f"{key}.json").exists()
        meta["saved_data"] = saved
        meta["has_any_result"] = any(saved.values())

        projects.append(meta)

    # 최근 접근순 정렬
    projects.sort(key=lambda p: p.get("last_accessed", ""), reverse=True)
    return projects


def get_saved_status(filename: str | None = None) -> dict[str, bool]:
    """각 데이터의 저장 여부."""
    fn = filename or get_current_project()
    if not fn:
        return {k: False for k in DATA_KEYS}
    d = _project_dir(fn)
    return {key: (d / f"{key}.json").exists() for key in DATA_KEYS}


def save_meta(filename: str, **kwargs: Any) -> None:
    """프로젝트 메타데이터 업데이트."""
    meta_path = _project_dir(filename) / "meta.json"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text("utf-8"))
        except Exception:
            pass
    meta.update(kwargs)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), "utf-8")
