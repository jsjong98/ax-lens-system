"""
auth_store.py — 간단한 JSON 기반 사용자 인증 저장소

사용자 정보를 users.json에 저장하며, bcrypt 없이 hashlib(sha256)을 사용합니다.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path
from datetime import datetime

_USERS_FILE = Path(__file__).parent / "users.json"

# 인메모리 세션 저장소: {token: {"email": ..., "expires": ...}}
_sessions: dict[str, dict] = {}


def _hash_password(password: str) -> str:
    """SHA-256으로 비밀번호 해시"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _load_users() -> dict[str, dict]:
    """users.json 로드. 없으면 빈 dict."""
    if _USERS_FILE.exists():
        return json.loads(_USERS_FILE.read_text("utf-8"))
    return {}


def _save_users(users: dict[str, dict]) -> None:
    """users.json 저장"""
    _USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), "utf-8")


def init_default_users() -> None:
    """기본 계정이 없으면 생성"""
    users = _load_users()
    defaults = [
        {"email": "jong-hwan.oh@pwc.com", "name": "Oh Jonghwan", "password": "strategy&"},
        {"email": "jidong.kim@pwc.com", "name": "Kim Jidong", "password": "strategy&"},
    ]
    changed = False
    for d in defaults:
        if d["email"] not in users:
            users[d["email"]] = {
                "name": d["name"],
                "password_hash": _hash_password(d["password"]),
                "must_change_password": True,
                "created_at": datetime.now().isoformat(),
            }
            changed = True
    if changed:
        _save_users(users)


def authenticate(email: str, password: str) -> str | None:
    """
    이메일/비밀번호 검증. 성공 시 세션 토큰 반환, 실패 시 None.
    """
    users = _load_users()
    user = users.get(email)
    if not user:
        return None
    if user["password_hash"] != _hash_password(password):
        return None
    # 세션 토큰 생성
    token = secrets.token_urlsafe(32)
    _sessions[token] = {"email": email}
    return token


def get_session_user(token: str) -> dict | None:
    """토큰으로 세션 조회. 유효하면 사용자 정보 반환."""
    session = _sessions.get(token)
    if not session:
        return None
    email = session["email"]
    users = _load_users()
    user = users.get(email)
    if not user:
        return None
    return {
        "email": email,
        "name": user["name"],
        "must_change_password": user.get("must_change_password", False),
    }


def change_password(email: str, old_password: str, new_password: str) -> bool:
    """비밀번호 변경. 성공 시 True."""
    users = _load_users()
    user = users.get(email)
    if not user:
        return False
    if user["password_hash"] != _hash_password(old_password):
        return False
    user["password_hash"] = _hash_password(new_password)
    user["must_change_password"] = False
    _save_users(users)
    return True


def logout(token: str) -> None:
    """세션 삭제"""
    _sessions.pop(token, None)
