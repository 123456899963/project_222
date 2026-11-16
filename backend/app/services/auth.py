"""认证业务层：注册、登录、用户查询

安全控制落点（SECURITY）：
- S-01：密码 bcrypt 哈希（在 core/security.py）
- S-04：登录失败统一 40110，对不存在用户执行哑哈希比对（等时）
- S-05：用户名唯一性，并发注册以唯一索引兜底（IntegrityError → 40910）
- S-20：不整包映射 ORM，字段显式构造
- S-33：登录失败锁定（用户名 + IP 双维度，窗口内达到阈值返回 42900）
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.response import (
    BadCredentials,
    TooManyLoginAttempts,
    UsernameExists,
    ValidationError,
)
from app.core.security import DUMMY_HASH, hash_password, verify_password
from app.models.user import User
from app.repositories import login_attempt_repo, user_repo


def register(db: Session, username: str, password: str) -> User:
    """注册新用户。

    先查重给出友好提示；并发注册撞唯一索引时捕获 IntegrityError 转 40910，
    不得返回 500（SECURITY S-05 / S-26）。
    """
    if user_repo.get_by_username(db, username):
        raise UsernameExists

    try:
        return user_repo.create_user(db, username, hash_password(password))
    except IntegrityError:
        # 并发场景：查重与创建之间另一个请求抢先插入
        db.rollback()
        raise UsernameExists


def _is_locked(db: Session, username: str, ip: str, now: datetime) -> bool:
    """窗口内同一用户名或同一 IP 的失败次数是否达到阈值（S-33）。"""
    since = now - timedelta(minutes=settings.LOGIN_WINDOW_MINUTES)
    by_username, by_ip = login_attempt_repo.count_recent(db, username=username, ip=ip, since=since)
    return by_username >= settings.LOGIN_MAX_FAILURES or by_ip >= settings.LOGIN_MAX_FAILURES


def _record_failure(db: Session, username: str, ip: str, now: datetime) -> None:
    """记录失败事件，并顺带清理超过保留期的历史记录。"""
    login_attempt_repo.delete_older_than(
        db, now - timedelta(hours=settings.LOGIN_ATTEMPT_RETENTION_HOURS)
    )
    login_attempt_repo.create(db, username=username, ip=ip, failed_at=now)
    db.commit()


def login(db: Session, username: str, password: str, *, ip: str) -> User:
    """校验用户名 + 密码。

    - 锁定判定先于账号存在性校验，避免通过 429/401 差异探测账号（S-33 / S-04）
    - 用户名不存在与密码错误统一返回 40110（不区分）；对不存在的用户也执行一次
      bcrypt 哑哈希比对，避免响应时间差暴露账号是否存在（SECURITY S-04）
    """
    now = datetime.now(timezone.utc)

    if _is_locked(db, username, ip, now):
        # 锁定期间即使密码正确也拒绝；不泄露账号是否存在
        raise TooManyLoginAttempts

    user = user_repo.get_by_username(db, username)
    if not user:
        # 等时比对：对哑哈希做一次校验，消耗与正常登录相近的时间
        verify_password(password, DUMMY_HASH)
        _record_failure(db, username, ip, now)
        raise BadCredentials

    if not verify_password(password, user.password_hash):
        _record_failure(db, username, ip, now)
        raise BadCredentials

    # 成功登录清空该用户名的失败记录（IP 维度保留至自然过期，防止借有效账号洗白 IP）
    login_attempt_repo.delete_by_username(db, username)
    db.commit()
    return user


def get_by_id(db: Session, user_id: int) -> User | None:
    return user_repo.get_by_id(db, user_id)


def change_password(db: Session, user: User, old_password: str, new_password: str) -> None:
    """修改密码：校验旧密码 → 更新哈希 → 递增会话版本（旧 Cookie 立即失效）。

    - 旧密码错误复用凭证错误码 40110（不区分具体原因）
    - 新旧密码相同返回 40000；长度/字符规则由 Schema 与注册保持一致
    """
    if not verify_password(old_password, user.password_hash):
        raise BadCredentials
    if old_password == new_password:
        raise ValidationError
    user_repo.update_password(db, user, hash_password(new_password))


def logout(db: Session, user: User | None) -> None:
    """登出吊销：有效会话时递增会话版本，使旧 Cookie 立即失效（SECURITY S-10）。

    未登录或 Cookie 无效时不做任何数据库操作，保持接口幂等。
    由于没有 sessions 表，吊销粒度是用户级——该用户所有设备会话同时失效。
    """
    if user is not None:
        user_repo.revoke_sessions(db, user)
