"""
settings_store.py — 분류 설정 및 분류 결과를 JSON 파일로 영속화합니다.

파일 위치: backend/ 폴더 내
  - settings.json   : ClassifierSettings
  - results.json    : {task_id: ClassificationResult}
"""
from __future__ import annotations
import json
from pathlib import Path

from models import ClassificationResult, ClassifierSettings

_BASE = Path(__file__).parent
_SETTINGS_FILE = _BASE / "settings.json"
_RESULTS_FILE  = _BASE / "results.json"


# ── 설정 ─────────────────────────────────────────────────────────────────────

def load_settings() -> ClassifierSettings:
    if _SETTINGS_FILE.exists():
        try:
            return ClassifierSettings(**json.loads(_SETTINGS_FILE.read_text("utf-8")))
        except Exception:
            pass
    return ClassifierSettings()


def save_settings(settings: ClassifierSettings) -> None:
    _SETTINGS_FILE.write_text(
        settings.model_dump_json(indent=2), encoding="utf-8"
    )


# ── 결과 ─────────────────────────────────────────────────────────────────────

def load_results() -> dict[str, ClassificationResult]:
    if _RESULTS_FILE.exists():
        try:
            raw: dict = json.loads(_RESULTS_FILE.read_text("utf-8"))
            return {
                task_id: ClassificationResult(**data)
                for task_id, data in raw.items()
            }
        except Exception:
            pass
    return {}


def save_results(results: dict[str, ClassificationResult]) -> None:
    data = {
        task_id: result.model_dump()
        for task_id, result in results.items()
    }
    _RESULTS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_result(result: ClassificationResult) -> None:
    results = load_results()
    results[result.task_id] = result
    save_results(results)


def clear_results() -> None:
    if _RESULTS_FILE.exists():
        _RESULTS_FILE.unlink()
