"""登录失败尝试（S14 / SECURITY S-33）

只记录失败事件，不记录密码明文；记录 24 小时后由登录流程顺带清理。
维度：用户名 + IP，双维度任一达到阈值即锁定。
"""

from datetime import datetime

from sqlalchemy import DateTime, Index, String, text
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.database import Base


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), primary_key=True, autoincrement=True
    )
    username: Mapped[str] = mapped_column(String(32), nullable=False)
    ip: Mapped[str] = mapped_column(String(45), nullable=False)
    failed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        Index("idx_login_attempt_username", "username", "failed_at"),
        Index("idx_login_attempt_ip", "ip", "failed_at"),
    )
