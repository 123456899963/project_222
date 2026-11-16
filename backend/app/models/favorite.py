from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.database import Base


class FavoriteItem(Base):
    """收藏清单条目（PRD §4.2，S9 多清单）

    - 清单归属以 list_id 为准，user_id 冗余保留用于「跨清单去重」与统计
    - 同一清单内同一茶品唯一：UNIQUE(list_id, tea_id)
    - 同一茶品可存在于多个清单，但 teas.favorite_count 只在用户首次收藏时 +1
    """

    __tablename__ = "favorite_items"

    id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), primary_key=True, autoincrement=True
    )
    list_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True),
        ForeignKey("collection_lists.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tea_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), ForeignKey("teas.id", ondelete="CASCADE"), nullable=False
    )
    tasting_note: Mapped[str | None] = mapped_column(Text, nullable=True)  # 私有品鉴笔记
    created_at: Mapped[datetime] = mapped_column(  # 收藏时间
        DateTime, nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        UniqueConstraint("list_id", "tea_id", name="uk_favorite_list_tea"),
        Index("idx_favorite_list_created", "list_id", "created_at"),
        Index("idx_favorite_user_created", "user_id", "created_at"),
        Index("idx_favorite_tea", "tea_id"),
    )


class ShareToken(Base):
    """清单分享令牌（PRD FR-5.4 / FR-5.5）

    - 分享对象是清单，故挂 list_id（不再直接挂 user_id）
    - token 使用 utf8mb4_bin（大小写敏感），避免 k7X9m2 / K7X9M2 被视为同一令牌
    - 撤销为软失效，行永久保留；撤销后不可复活，再次分享必须新建 token
    """

    __tablename__ = "share_tokens"

    id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), primary_key=True, autoincrement=True
    )
    list_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True),
        ForeignKey("collection_lists.id", ondelete="CASCADE"),
        nullable=False,
    )
    token: Mapped[str] = mapped_column(
        String(16, collation="utf8mb4_bin"), unique=True, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        # 判断清单是否已有生效分享（复用/撤销/审计），兼作 list_id 外键索引
        Index("idx_share_list_active", "list_id", "is_active"),
    )
