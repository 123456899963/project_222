from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, text
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.clock import utcnow
from app.core.database import Base

CONTRIBUTION_TYPE = Enum("new_tea", "article", name="contribution_type")
CONTRIBUTION_STATUS = Enum("pending", "approved", "rejected", name="contribution_status")
TEA_CATEGORY = Enum(
    "green", "white", "yellow", "red", "oolong", "dark", "reprocessed", name="tea_category"
)


class Contribution(Base):
    """用户贡献提交（S10 / S11 / S12 / S13）

    - payload 为结构化 JSON：new_tea 存茶品字段，article 存 {title, content}
    - 状态仅 pending → approved / rejected 单向流转；已处理记录保留审计
    - target_tea_id 仅 article 使用，茶品删除后置 NULL（贡献记录不随茶品消失）
    """

    __tablename__ = "contributions"

    id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(CONTRIBUTION_TYPE, nullable=False)
    target_tea_id: Mapped[int | None] = mapped_column(
        MySQLInteger(unsigned=True), ForeignKey("teas.id", ondelete="SET NULL"), nullable=True
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        CONTRIBUTION_STATUS, nullable=False, default="pending", server_default=text("'pending'")
    )
    reject_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reviewer_id: Mapped[int | None] = mapped_column(
        MySQLInteger(unsigned=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        Index("idx_contrib_user_status", "user_id", "status"),
        Index("idx_contrib_status_created", "status", "created_at"),
    )


class TeaNameCategoryMap(Base):
    """名品-茶类映射（S10 第一层校验）

    - 命中名称时强校验用户选择的茶类；未命中则由管理员人工审核
    - 名称唯一，避免同一名品出现矛盾映射
    """

    __tablename__ = "tea_name_category_map"

    id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(TEA_CATEGORY, nullable=False)
