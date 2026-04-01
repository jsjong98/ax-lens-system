"""
audit_log.py — 감사 로그 시스템

모든 사용자 활동을 JSON 파일로 기록합니다.
- 로그인/로그아웃
- 데이터 업로드
- 분류 실행
- Workflow 생성
- 비밀번호 변경
- Admin 활동
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

_PERSIST_ROOT = Path("/app/persist") if Path("/app/persist").exists() else Path(__file__).parent
_LOG_FILE = _PERSIST_ROOT / "audit_log.json"

# 인메모리 캐시 (최근 로그)
_log_cache: list[dict] = []
_MAX_CACHE = 5000


def _load_log() -> None:
    """서버 시작 시 로그 복원."""
    global _log_cache
    if _LOG_FILE.exists():
        try:
            _log_cache = json.loads(_LOG_FILE.read_text("utf-8"))
        except Exception:
            _log_cache = []


def _save_log() -> None:
    """로그 파일 저장."""
    try:
        # 최대 크기 제한
        data = _log_cache[-_MAX_CACHE:]
        _LOG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    except Exception as e:
        print(f"[audit] 로그 저장 실패: {e}")


_load_log()


def log_event(
    event_type: str,
    email: str = "",
    ip: str = "",
    detail: str = "",
    data: dict | None = None,
) -> None:
    """
    감사 이벤트를 기록합니다.

    event_type 예시:
    - login_success, login_failed, logout, session_evicted
    - password_changed, password_reset
    - excel_upload, classify_run, classify_complete
    - workflow_upload, workflow_generate, benchmark_run
    - new_workflow_generate, project_definition, project_design
    - admin_force_logout, admin_view
    - data_download, data_export
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        "email": email,
        "ip": ip,
        "detail": detail,
    }
    if data:
        entry["data"] = data

    _log_cache.append(entry)

    # 주기적 저장 (매 10건)
    if len(_log_cache) % 10 == 0:
        _save_log()
    else:
        # 중요 이벤트는 즉시 저장
        if event_type in ("login_failed", "admin_force_logout", "password_changed", "password_reset"):
            _save_log()


def get_logs(
    limit: int = 100,
    offset: int = 0,
    email_filter: str = "",
    event_filter: str = "",
    ip_filter: str = "",
) -> tuple[list[dict], int]:
    """
    로그 조회. (결과 목록, 전체 건수) 반환.
    최신순 정렬.
    """
    filtered = _log_cache

    if email_filter:
        filtered = [e for e in filtered if email_filter.lower() in e.get("email", "").lower()]
    if event_filter:
        filtered = [e for e in filtered if event_filter.lower() in e.get("event", "").lower()]
    if ip_filter:
        filtered = [e for e in filtered if ip_filter in e.get("ip", "")]

    total = len(filtered)
    # 최신순
    filtered = list(reversed(filtered))
    return filtered[offset:offset + limit], total


def get_login_history(email: str = "", limit: int = 50) -> list[dict]:
    """로그인 관련 이벤트만 조회."""
    login_events = {"login_success", "login_failed", "logout", "session_evicted"}
    filtered = [e for e in _log_cache if e.get("event") in login_events]
    if email:
        filtered = [e for e in filtered if e.get("email") == email]
    return list(reversed(filtered))[:limit]


def get_data_activity(limit: int = 50) -> list[dict]:
    """데이터 관련 이벤트 조회 (업로드, 분류, 생성 등)."""
    data_events = {
        "excel_upload", "classify_run", "classify_complete",
        "workflow_upload", "workflow_generate", "benchmark_run",
        "new_workflow_generate", "project_definition", "project_design",
        "data_download", "data_export",
    }
    filtered = [e for e in _log_cache if e.get("event") in data_events]
    return list(reversed(filtered))[:limit]


def flush() -> None:
    """강제 저장."""
    _save_log()
