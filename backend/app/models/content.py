from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, SmallInteger, String, text
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.clock import utcnow
from app.core.database import Base


class ContentType(Base):
    """内容板块分类（批次五 R1–R5）

    - 固定 5 类：茶具/产地/文化/品牌/知识
    - code 唯一，用于前端路由和 API 查询参数
    """

    __tablename__ = "content_types"

    id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), primary_key=True, autoincrement=True
    )
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=0, server_default=text("0")
    )


class ContentItem(Base):
    """统一内容条目（批次五 R1–R5）

    - type_id → ContentType 外键，决定条目所属板块
    - meta JSON 承载各板块特有字段：
      - teaware: {"material", "volume", "category"}
      - origin: {"province", "region"}
      - culture: {"era", "tags"}
      - brand: {"founded", "origin", "website"}
      - knowledge: {"subtype", "difficulty"}
    - is_active 软失效；下架后前台不可见
    """

    __tablename__ = "content_items"

    id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), primary_key=True, autoincrement=True
    )
    type_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True),
        ForeignKey("content_types.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str | None] = mapped_column(String(20000), nullable=True)
    cover_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sort_order: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=0, server_default=text("0")
    )
    is_active: Mapped[int] = mapped_column(
        SmallInteger(), nullable=False, default=1, server_default=text("1")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utcnow,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    __table_args__ = (
        Index("idx_content_items_type_active_sort", "type_id", "is_active", "sort_order"),
        Index("idx_content_items_created", "created_at"),
    )
