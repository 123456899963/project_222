from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.database import Base


class CollectionList(Base):
    """用户收藏清单（PRD §4.2 / FR-5.1 / FR-5.2，S9 多清单）

    - 每用户有且仅有一个默认清单：默认行 is_default=1，其余行 is_default=NULL；
      `UNIQUE(user_id, is_default)` 依赖 MySQL「唯一索引允许多个 NULL」特性，
      因此同一用户可建多个非默认清单，但默认清单只能有一个。
    - 可见性不落列，由 share_tokens.is_active 派生。
    """

    __tablename__ = "collection_lists"

    id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(50), nullable=False, default="我的收藏")
    is_default: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    __table_args__ = (
        UniqueConstraint("user_id", "is_default", name="uk_list_user_default"),
        Index("idx_list_user", "user_id"),
    )
