"""安全：pbkdf2 密码摘要 + HMAC 签名 Token（均只用标准库，无额外依赖）。"""
import base64
import hashlib
import hmac
import json
import os
import time

import settings


# ---------- 密码 ----------

def hash_password(password: str, salt: str | None = None) -> str:
    """生成 pbkdf2_sha256 摘要，格式：pbkdf2$迭代$盐$摘要。"""
    salt = salt or base64.urlsafe_b64encode(os.urandom(16)).decode()
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), settings.PASSWORD_ITERATIONS)
    return f"pbkdf2${settings.PASSWORD_ITERATIONS}${salt}${base64.urlsafe_b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _algo, iters, salt, digest = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iters))
        return hmac.compare_digest(base64.urlsafe_b64encode(dk).decode(), digest)
    except Exception:
        return False


# ---------- Token ----------

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def create_token(user_id: int, username: str, role: int = 1) -> str:
    """HMAC 签名 Token：payload 签名后 base64，形如 body.sig。role: 1=用户 9=管理员。"""
    payload = {
        "uid": user_id,
        "un": username,
        "role": role,
        "exp": int(time.time()) + settings.TOKEN_TTL_DAYS * 86400,
    }
    body = _b64(json.dumps(payload).encode())
    sig = hmac.new(settings.APP_SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify_token(token: str) -> dict | None:
    """校验 Token，返回 payload；失败返回 None。"""
    try:
        body, sig = token.split(".")
        expect = hmac.new(settings.APP_SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expect, sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None
