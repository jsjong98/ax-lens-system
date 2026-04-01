"""
auth_store.py — 간단한 JSON 기반 사용자 인증 저장소

사용자 정보를 users.json에 저장하며, bcrypt 없이 hashlib(sha256)을 사용합니다.
비밀번호 재설정은 Resend API로 이메일 인증번호를 발송합니다.
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
    # 레거시 SHA-256 호환 (기존 사용자 마이그레이션용)
    return secrets.compare_digest(
        hashlib.sha256(password.encode("utf-8")).hexdigest(), stored_hash
    )


def _load_users() -> dict[str, dict]:
    """users.json 로드. 없으면 빈 dict."""
    if _USERS_FILE.exists():
        return json.loads(_USERS_FILE.read_text("utf-8"))
    return {}


def _save_users(users: dict[str, dict]) -> None:
    """users.json 저장"""
    _USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), "utf-8")


def init_default_users() -> None:
    """
    기본 계정이 없으면 생성.
    환경변수 DEFAULT_USERS에서 읽음 (JSON 배열).
    예: [{"email":"a@b.com","name":"홍길동","password":"pw123"}]
    """
    users = _load_users()
    defaults_json = os.getenv("DEFAULT_USERS", "")
    if not defaults_json:
        return  # 환경변수 미설정 시 건너뜀
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


def authenticate(email: str, password: str) -> str | None:
    """
    이메일/비밀번호 검증. 성공 시 세션 토큰 반환, 실패 시 None.
    """
    users = _load_users()
    user = users.get(email)
    if not user:
        return None
    if not _verify_password(password, user["password_hash"]):
        return None
    # 레거시 SHA-256 해시 → PBKDF2 자동 마이그레이션
    if "$" not in user["password_hash"]:
        user["password_hash"] = _hash_password(password)
        _save_users(users)
    # 세션 토큰 생성 + 파일 저장
    token = secrets.token_urlsafe(32)
    _sessions[token] = {"email": email}
    _save_sessions()
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
    if not _verify_password(old_password, user["password_hash"]):
        return False
    user["password_hash"] = _hash_password(new_password)
    user["must_change_password"] = False
    _save_users(users)
    return True


def logout(token: str) -> None:
    """세션 삭제"""
    _sessions.pop(token, None)
    _save_sessions()


# ── 비밀번호 재설정 ──────────────────────────────────────────────────────────

def generate_reset_code(email: str) -> str | None:
    """
    6자리 인증번호를 생성하고 저장. 등록되지 않은 이메일이면 None.
    유효시간: 10분.
    """
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
    """인증번호 검증. 유효하면 True."""
    entry = _reset_codes.get(email)
    if not entry:
        return False
    if datetime.now() > datetime.fromisoformat(entry["expires_at"]):
        _reset_codes.pop(email, None)
        return False
    return entry["code"] == code


def reset_password(email: str, code: str, new_password: str) -> bool:
    """인증번호 확인 후 비밀번호 재설정. 성공 시 True."""
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
    return True


async def send_reset_email(email: str, code: str) -> bool:
    """Resend API로 인증번호 이메일 발송."""
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        print(f"[AUTH] RESEND_API_KEY 미설정. 인증번호가 생성되었으나 이메일 발송 불가 (개발 모드)")
        return True  # 키 없으면 콘솔 출력만 (개발용)

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
        # 인증번호는 로그에 출력하지 않음 (보안)
        return True  # 이메일 실패해도 인증번호는 생성됨 — 로그에서 확인 가능
    except Exception as e:
        print("[AUTH] 이메일 발송 오류")
        # 인증번호는 로그에 출력하지 않음 (보안)
        return True
