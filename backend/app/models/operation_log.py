from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.database import Base


class OperationLog(Base):
    """管理员写操作留痕（MVP 最小字段集）

    - user_id 采用 SET NULL：审计记录不随账号删除而消失
    - target_id 为弱引用（不建外键）：删茶不应抹掉历史日志
    - action 用 VARCHAR 而非 ENUM：日志可扩展动作，历史不受新枚举约束
    """

    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), primary_key=True, autoincrement=True
    )
    user_id: Mapped[int | None] = mapped_column(
        MySQLInteger(unsigned=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False, default="tea")
    target_id: Mapped[int | None] = mapped_column(MySQLInteger(unsigned=True), nullable=True)
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        Index("idx_oplog_created", "created_at"),
        Index("idx_oplog_user", "user_id"),
    )
