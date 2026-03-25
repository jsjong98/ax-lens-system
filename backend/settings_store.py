"""
settings_store.py — 분류 설정 및 분류 결과를 JSON 파일로 영속화합니다.

파일 위치: backend/results/ 폴더 내
  - settings.json                     : ClassifierSettings
  - results/{파일명}_openai.json      : OpenAI 분류 결과
  - results/{파일명}_anthropic.json   : Anthropic 분류 결과

파일별로 결과를 분리 저장하여, 다른 엑셀을 업로드해도 이전 결과가 누적되지 않습니다.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

from models import ClassificationResult, ClassifierSettings

_BASE = Path(__file__).parent
_PERSIST_ROOT = Path("/app/persist") if Path("/app/persist").exists() else _BASE
_SETTINGS_FILE = _PERSIST_ROOT / "settings.json"
_RESULTS_DIR = _PERSIST_ROOT / "results"
_RESULTS_DIR.mkdir(exist_ok=True)

# 현재 활성 엑셀 파일명 (확장자 제외)
_current_file_key: str = "default"


def set_current_file(filename: str) -> None:
    """현재 작업 중인 엑셀 파일명을 설정합니다."""
    global _current_file_key
    # 파일명에서 확장자 제거 + 특수문자를 _로 치환
    name = Path(filename).stem
    _current_file_key = re.sub(r'[^\w가-힣\-]', '_', name)


def get_current_file_key() -> str:
    return _current_file_key


def _results_file(provider: str) -> Path:
    return _RESULTS_DIR / f"{_current_file_key}_{provider}.json"


def _migrate_legacy() -> None:
    """기존 results_openai.json → results/ 폴더로 1회 마이그레이션."""
    for provider in ("openai", "anthropic"):
        legacy = _BASE / f"results_{provider}.json"
        if legacy.exists():
            target = _RESULTS_DIR / f"default_{provider}.json"
            if not target.exists():
                import shutil
                shutil.copy(legacy, target)
                print(f"[settings_store] {legacy.name} → results/{target.name} 마이그레이션 완료")
    # 구버전 results.json
    legacy_old = _BASE / "results.json"
    if legacy_old.exists():
        target = _RESULTS_DIR / "default_openai.json"
        if not target.exists():
            import shutil
            shutil.copy(legacy_old, target)


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
