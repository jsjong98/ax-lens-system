"""
auth_store.py — JSON 기반 사용자 인증 저장소

- PBKDF2-SHA256 비밀번호 해싱
- IP 기반 최대 2기기 동시 로그인 제한
- 비밀번호 재설정 (Resend API 이메일)
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path
from datetime import datetime, timedelta

_PERSIST_ROOT = Path("/app/persist") if Path("/app/persist").exists() else Path(__file__).parent
_USERS_FILE = _PERSIST_ROOT / "users.json"
_SESSIONS_FILE = _PERSIST_ROOT / "sessions.json"

# 최대 동시 세션 수 (기기 수)
MAX_SESSIONS_PER_USER = 2

# Admin 이메일
ADMIN_EMAIL = "jong-hwan.oh@pwc.com"

# 세션 저장소 (파일 영속)
_sessions: dict[str, dict] = {}

# 인메모리 인증번호 저장소
_reset_codes: dict[str, dict] = {}


def _load_sessions() -> None:
    """서버 시작 시 세션 파일에서 복원."""
    global _sessions
    if _SESSIONS_FILE.exists():
        try:
            _sessions = json.loads(_SESSIONS_FILE.read_text("utf-8"))
        except Exception:
            _sessions = {}


def _save_sessions() -> None:
    """세션을 파일로 저장."""
    try:
        _SESSIONS_FILE.write_text(json.dumps(_sessions, ensure_ascii=False), "utf-8")
    except Exception as e:
        print(f"[auth] 세션 저장 실패: {e}")


_load_sessions()


def _hash_password(password: str) -> str:
    """PBKDF2-SHA256 기반 비밀번호 해시 (솔트 포함)."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode(), 100_000)
    return f"{salt}${dk.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    """저장된 해시와 비밀번호를 비교. 레거시(SHA-256) 호환."""
    if "$" in stored_hash:
        salt, dk_hex = stored_hash.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode(), 100_000)
        return secrets.compare_digest(dk.hex(), dk_hex)
    return secrets.compare_digest(
        hashlib.sha256(password.encode("utf-8")).hexdigest(), stored_hash
    )


def _load_users() -> dict[str, dict]:
    if _USERS_FILE.exists():
        return json.loads(_USERS_FILE.read_text("utf-8"))
    return {}


def _save_users(users: dict[str, dict]) -> None:
    _USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), "utf-8")


def _get_user_sessions(email: str) -> list[tuple[str, dict]]:
    """특정 사용자의 모든 세션을 (token, session_data) 리스트로 반환."""
    return [(tok, sess) for tok, sess in _sessions.items() if sess.get("email") == email]


def _enforce_session_limit(email: str) -> list[str]:
    """
    최대 동시 세션 수 초과 시 가장 오래된 세션을 제거.
    제거된 토큰 목록을 반환.
    """
    user_sessions = _get_user_sessions(email)
    if len(user_sessions) < MAX_SESSIONS_PER_USER:
        return []

    # login_at 기준 오래된 순 정렬
    user_sessions.sort(key=lambda x: x[1].get("login_at", ""))

    # 가장 오래된 세션부터 제거 (새 세션 자리 확보)
    to_remove = len(user_sessions) - MAX_SESSIONS_PER_USER + 1
    removed = []
    for tok, _ in user_sessions[:to_remove]:
        _sessions.pop(tok, None)
        removed.append(tok)

    return removed


def init_default_users() -> None:
    users = _load_users()
    defaults_json = os.getenv("DEFAULT_USERS", "")
    if not defaults_json:
        return
    try:
        defaults = json.loads(defaults_json)
    except json.JSONDecodeError:
        print("[auth] DEFAULT_USERS 환경변수 파싱 실패")
        return
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


def authenticate(email: str, password: str, ip: str = "", user_agent: str = "") -> str | None:
    """
    이메일/비밀번호 검증. 성공 시 세션 토큰 반환, 실패 시 None.
    최대 2기기 동시 로그인 제한 적용.
    """
    from audit_log import log_event

    users = _load_users()
    user = users.get(email)
    if not user:
        log_event("login_failed", email=email, ip=ip, detail="존재하지 않는 이메일")
        return None
    if not _verify_password(password, user["password_hash"]):
        log_event("login_failed", email=email, ip=ip, detail="비밀번호 불일치")
        return None

    # 레거시 SHA-256 해시 → PBKDF2 자동 마이그레이션
    if "$" not in user["password_hash"]:
        user["password_hash"] = _hash_password(password)
        _save_users(users)

    # 동시 세션 제한 — 오래된 세션 강제 종료
    removed = _enforce_session_limit(email)
    if removed:
        log_event("session_evicted", email=email, ip=ip,
                  detail=f"최대 {MAX_SESSIONS_PER_USER}기기 제한으로 {len(removed)}개 세션 종료")

    # 새 세션 토큰 생성
    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        "email": email,
        "ip": ip,
        "user_agent": user_agent,
        "login_at": datetime.now().isoformat(),
    }
    _save_sessions()

    log_event("login_success", email=email, ip=ip,
              detail=f"활성 세션 {len(_get_user_sessions(email))}개")
    return token


def update_session_info(token: str, ip: str = "", user_agent: str = "") -> None:
    """세션에 IP/UA 정보를 갱신 (기존 세션 호환용)."""
    session = _sessions.get(token)
    if not session:
        return
    changed = False
    if ip and not session.get("ip"):
        session["ip"] = ip
        changed = True
    if user_agent and not session.get("user_agent"):
        session["user_agent"] = user_agent
        changed = True
    if changed:
        _save_sessions()


def get_session_user(token: str) -> dict | None:
    """토큰으로 세션 조회."""
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
        "is_admin": email == ADMIN_EMAIL,
    }


def change_password(email: str, old_password: str, new_password: str) -> bool:
    """비밀번호 변경. 성공 시 True."""
    from audit_log import log_event
    users = _load_users()
    user = users.get(email)
    if not user:
        return False
    if not _verify_password(old_password, user["password_hash"]):
        return False
    user["password_hash"] = _hash_password(new_password)
    user["must_change_password"] = False
    _save_users(users)
    log_event("password_changed", email=email)
    return True


def logout(token: str) -> None:
    session = _sessions.pop(token, None)
    _save_sessions()
    if session:
        from audit_log import log_event
        log_event("logout", email=session.get("email", ""))


def get_all_sessions() -> list[dict]:
    """Admin용: 모든 활성 세션 목록."""
    result = []
    for tok, sess in _sessions.items():
        result.append({
            "token_prefix": tok[:8] + "...",
            "email": sess.get("email", ""),
            "ip": sess.get("ip", ""),
            "user_agent": sess.get("user_agent", ""),
            "login_at": sess.get("login_at", ""),
        })
    result.sort(key=lambda x: x.get("login_at", ""), reverse=True)
    return result


def get_all_users_info() -> list[dict]:
    """Admin용: 모든 사용자 정보 (비밀번호 제외)."""
    users = _load_users()
    result = []
    for email, user in users.items():
        sessions = _get_user_sessions(email)
        result.append({
            "email": email,
            "name": user.get("name", ""),
            "created_at": user.get("created_at", ""),
            "must_change_password": user.get("must_change_password", False),
            "active_sessions": len(sessions),
            "session_ips": list({s.get("ip", "") for _, s in sessions}),
        })
    return result


def force_logout_user(email: str) -> int:
    """Admin용: 특정 사용자의 모든 세션 강제 종료. 종료된 세션 수 반환."""
    from audit_log import log_event
    sessions = _get_user_sessions(email)
    for tok, _ in sessions:
        _sessions.pop(tok, None)
    _save_sessions()
    log_event("admin_force_logout", email=email, detail=f"{len(sessions)}개 세션 강제 종료")
    return len(sessions)


# ── 비밀번호 재설정 ──────────────────────────────────────────────────────────

def generate_reset_code(email: str) -> str | None:
    users = _load_users()
    if email not in users:
        return None
    code = f"{secrets.randbelow(1_000_000):06d}"
    _reset_codes[email] = {
        "code": code,
        "expires_at": (datetime.now() + timedelta(minutes=10)).isoformat(),
    }
    return code


def verify_reset_code(email: str, code: str) -> bool:
    entry = _reset_codes.get(email)
    if not entry:
        return False
    if datetime.now() > datetime.fromisoformat(entry["expires_at"]):
        _reset_codes.pop(email, None)
        return False
    return entry["code"] == code


def reset_password(email: str, code: str, new_password: str) -> bool:
    if not verify_reset_code(email, code):
        return False
    users = _load_users()
    user = users.get(email)
    if not user:
        return False
    user["password_hash"] = _hash_password(new_password)
    user["must_change_password"] = False
    _save_users(users)
    _reset_codes.pop(email, None)
    from audit_log import log_event
    log_event("password_reset", email=email)
    return True


async def send_reset_email(email: str, code: str) -> bool:
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        print(f"[AUTH] RESEND_API_KEY 미설정. 개발 모드")
        return True

    import urllib.request
    import urllib.error

    payload = json.dumps({
        "from": "PwC AX Lens <noreply@pwc-ax-lens.com>",
        "to": [email],
        "subject": "[PwC AX Lens] 비밀번호 재설정 인증번호",
        "html": f"""
        <div style="font-family: 'Noto Sans KR', Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 24px;">
            <div style="text-align: center; margin-bottom: 32px;">
                <h2 style="color: #A62121; margin: 0;">PwC AX Lens System</h2>
            </div>
            <div style="background: #f9fafb; border-radius: 12px; padding: 32px; text-align: center;">
                <p style="color: #374151; margin: 0 0 8px; font-size: 14px;">비밀번호 재설정 인증번호</p>
                <div style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #A62121; margin: 16px 0;">
                    {code}
                </div>
                <p style="color: #6b7280; margin: 16px 0 0; font-size: 13px;">
                    이 인증번호는 <strong>10분간</strong> 유효합니다.
                </p>
            </div>
            <p style="color: #9ca3af; font-size: 12px; text-align: center; margin-top: 24px;">
                본인이 요청하지 않았다면 이 이메일을 무시하세요.
            </p>
        </div>
        """,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print("[AUTH] 인증번호 이메일 발송 성공")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[AUTH] 이메일 발송 실패 (HTTP {e.code})")
        return True
    except Exception as e:
        print("[AUTH] 이메일 발송 오류")
        return True
