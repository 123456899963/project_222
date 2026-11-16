"""安全工具：密码哈希、会话签名、管理员权限校验"""

import bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import settings

# bcrypt cost 对齐 SECURITY S-01 / DATA_MODEL §9 种子数据注释（cost=10）
_BCRYPT_ROUNDS = 10

# 登录等时比对用的固定哑哈希（SECURITY S-04）：对不存在的用户也执行一次 bcrypt 校验，
# 避免响应时间差暴露账号是否存在。
DUMMY_HASH = bcrypt.hashpw(
    b"dummy-password-for-constant-time", bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
).decode("utf-8")


# --- 密码哈希 ---


def hash_password(password: str) -> str:
    """明文密码 → bcrypt 哈希（cost=10，对齐 SECURITY S-01）"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode(
        "utf-8"
    )


def verify_password(password: str, hashed: str) -> bool:
    """校验明文密码与 bcrypt 哈希是否匹配"""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# --- 会话签名 ---

_serializer = URLSafeTimedSerializer(settings.SECRET_KEY)


def create_session_token(user_id: int, session_version: int = 0) -> str:
    """把 user_id 与会话版本签名为 Cookie 令牌（itsdangerous 签名 Cookie，无状态）"""
    return _serializer.dumps({"uid": user_id, "sv": session_version})


def parse_session_token(token: str, max_age_days: int | None = None) -> tuple[int, int] | None:
    """解析 Cookie 令牌，返回 (user_id, session_version)；过期或无效返回 None。

    旧格式令牌没有 ``sv`` 字段，按 0 处理以保持向后兼容。
    """
    # 0/负数是 TEST_PLAN §2 约定的“立即过期”模拟值：
    # itsdangerous 只比较 age > max_age，同秒签发的令牌 age=0 不会过期，
    # 因此在使用库之前显式判定（配置值与显式传参同等处理）。
    days = settings.SESSION_EXPIRE_DAYS if max_age_days is None else max_age_days
    if days <= 0:
        return None
    try:
        max_age = days * 86400
        data = _serializer.loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None

    user_id = data.get("uid")
    session_version = data.get("sv", 0)
    if not isinstance(user_id, int) or not isinstance(session_version, int):
        return None
    return user_id, session_version


def verify_session_token(token: str, max_age_days: int | None = None) -> int | None:
    """解析 Cookie 令牌，返回 user_id；过期或无效返回 None"""
    parsed = parse_session_token(token, max_age_days)
    return parsed[0] if parsed is not None else None
