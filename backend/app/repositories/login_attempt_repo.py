"""登录失败尝试仓储层：仅封装查询与写入（ARCHITECTURE §3）

本层只 flush 不 commit，事务边界由 Service 层控制。
"""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.login_attempt import LoginAttempt


def count_recent(db: Session, *, username: str, ip: str, since: datetime) -> tuple[int, int]:
    """统计窗口内按用户名 / IP 的失败次数。"""
    by_username = (
        db.query(func.count(LoginAttempt.id))
        .filter(LoginAttempt.username == username, LoginAttempt.failed_at >= since)
        .scalar()
    )
    by_ip = (
        db.query(func.count(LoginAttempt.id))
        .filter(LoginAttempt.ip == ip, LoginAttempt.failed_at >= since)
        .scalar()
    )
    return int(by_username or 0), int(by_ip or 0)


def create(db: Session, *, username: str, ip: str, failed_at: datetime) -> LoginAttempt:
    item = LoginAttempt(username=username, ip=ip, failed_at=failed_at)
    db.add(item)
    db.flush()
    return item


def delete_by_username(db: Session, username: str) -> int:
    """登录成功后清理该用户名的失败记录（IP 维度保留到自然过期）。"""
    return (
        db.query(LoginAttempt)
        .filter(LoginAttempt.username == username)
        .delete(synchronize_session=False)
    )


def delete_older_than(db: Session, before: datetime) -> int:
    return (
        db.query(LoginAttempt)
        .filter(LoginAttempt.failed_at < before)
        .delete(synchronize_session=False)
    )
