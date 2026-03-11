"""
settings_store.py — 분류 설정 및 분류 결과를 JSON 파일로 영속화합니다.

파일 위치: backend/ 폴더 내
  - settings.json          : ClassifierSettings
  - results_openai.json    : OpenAI 분류 결과 {task_id: ClassificationResult}
  - results_anthropic.json : Anthropic 분류 결과 {task_id: ClassificationResult}
"""
from __future__ import annotations
import json
from pathlib import Path

from models import ClassificationResult, ClassifierSettings

_BASE = Path(__file__).parent
_SETTINGS_FILE         = _BASE / "settings.json"
_RESULTS_OPENAI_FILE   = _BASE / "results_openai.json"
_RESULTS_ANTHROPIC_FILE = _BASE / "results_anthropic.json"


def _results_file(provider: str) -> Path:
    return _RESULTS_ANTHROPIC_FILE if provider == "anthropic" else _RESULTS_OPENAI_FILE


def _migrate_legacy() -> None:
    """기존 results.json → results_openai.json 1회 마이그레이션."""
    legacy = _BASE / "results.json"
    if legacy.exists() and not _RESULTS_OPENAI_FILE.exists():
        import shutil
        shutil.copy(legacy, _RESULTS_OPENAI_FILE)
        print("[settings_store] results.json → results_openai.json 마이그레이션 완료")


_migrate_legacy()


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

def load_results(provider: str = "openai") -> dict[str, ClassificationResult]:
    file = _results_file(provider)
    if file.exists():
        try:
            raw: dict = json.loads(file.read_text("utf-8"))
            return {
                task_id: ClassificationResult(**data)
                for task_id, data in raw.items()
            }
        except Exception:
            pass
    return {}


def save_results(results: dict[str, ClassificationResult], provider: str = "openai") -> None:
    data = {
        task_id: result.model_dump()
        for task_id, result in results.items()
    }
    _results_file(provider).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def upsert_result(result: ClassificationResult, provider: str = "openai") -> None:
    results = load_results(provider)
    results[result.task_id] = result
    save_results(results, provider)


def clear_results(provider: str = "openai") -> None:
    file = _results_file(provider)
    if file.exists():
        file.unlink()
