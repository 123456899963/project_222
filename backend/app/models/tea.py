from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utcnow
from app.core.database import Base


class Tea(Base):
    """茶品图鉴卡片（PRD §4.1）"""

    __tablename__ = "teas"

    id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(
        Enum(
            "green",
            "white",
            "yellow",
            "red",
            "oolong",
            "dark",
            "reprocessed",
            name="tea_category",
        ),
        nullable=False,
    )
    origin: Mapped[str] = mapped_column(String(200), nullable=False)
    season: Mapped[str | None] = mapped_column(
        Enum("明前", "雨前", "春茶", "夏茶", "秋茶", "冬茶", name="tea_season"),
        nullable=True,
    )
    fermentation: Mapped[str | None] = mapped_column(
        Enum("不发酵", "微发酵", "半发酵", "全发酵", "后发酵", name="tea_fermentation"),
        nullable=True,
    )
    # 价格档位文案未在 PRD 定稿，保留 VARCHAR，由 Pydantic 校验
    price_range: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # 价格区间数值（S2 五档筛选）：单位元/斤，由后台录入或按 price_range 回填
    price_min: Mapped[int | None] = mapped_column(MySQLInteger(unsigned=True), nullable=True)
    price_max: Mapped[int | None] = mapped_column(MySQLInteger(unsigned=True), nullable=True)
    representative_variety: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 四大感官（TEXT 在 MySQL 5.7 不能有 DB 默认值，空串由应用层写入）
    shape_desc: Mapped[str] = mapped_column(Text, nullable=False, default="")
    soup_desc: Mapped[str] = mapped_column(Text, nullable=False, default="")
    aroma_desc: Mapped[str] = mapped_column(Text, nullable=False, default="")
    taste_desc: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # 冲泡参考（DECIMAL 避免浮点近似导致的展示误差）
    water_temp: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)  # 摄氏度
    tea_amount: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)  # 克
    brew_time: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)  # 秒

    # 主图
    main_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 视频介绍（S5，ADR-0003；NULL 表示无视频，前端整块隐藏）
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_duration: Mapped[int | None] = mapped_column(
        MySQLInteger(unsigned=True), nullable=True
    )  # 秒，≤180 由应用层校验

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    favorite_count: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), nullable=False, default=0
    )

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
        Index("idx_teas_active_category", "is_active", "category"),
        Index("idx_teas_active_created", "is_active", "created_at"),
        Index("idx_teas_active_favorite", "is_active", "favorite_count"),
    )

    # 关联
    tips: Mapped["TeaTips | None"] = relationship(back_populates="tea", uselist=False)
    brewing_guide: Mapped["TeaBrewingGuide | None"] = relationship(
        back_populates="tea", uselist=False
    )
    media_images: Mapped[list["TeaMedia"]] = relationship(
        back_populates="tea",
        order_by="TeaMedia.sort_order",
        cascade="all, delete-orphan",
    )


class TeaMedia(Base):
    """茶品图片集（PRD S4，ADR-0003；物理删除，上限 9 张由应用层校验）"""

    __tablename__ = "tea_media"

    id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), primary_key=True, autoincrement=True
    )
    tea_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True),
        ForeignKey("teas.id", ondelete="CASCADE"),
        nullable=False,
    )
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (Index("idx_tea_media_tea", "tea_id", "sort_order"),)

    tea: Mapped[Tea] = relationship(back_populates="media_images")


class TeaTips(Base):
    """官方小贴士（PRD §4.1 小贴士区）"""

    __tablename__ = "tea_tips"

    id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), primary_key=True, autoincrement=True
    )
    tea_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True),
        ForeignKey("teas.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    history: Mapped[str | None] = mapped_column(Text, nullable=True)  # 历史典故
    suitable: Mapped[str | None] = mapped_column(Text, nullable=True)  # 适合人群
    misconception: Mapped[str | None] = mapped_column(Text, nullable=True)  # 冲泡误区
    official_note: Mapped[str | None] = mapped_column(Text, nullable=True)  # 品鉴笔记（官方）

    # 时间戳（S7 首页最新小贴士按 updated_at 倒序）
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

    tea: Mapped[Tea] = relationship(back_populates="tips")


class TeaBrewingGuide(Base):
    """茶品分步冲泡教程（ADR-0005，与茶品 1:1）

    steps 为 JSON 数组：[{"title": str, "detail": str, "tip": str | null}]
    步数与字段长度由 Pydantic + Service 校验（MySQL 5.7 JSON 无内部约束）。
    """

    __tablename__ = "tea_brewing_guides"

    id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), primary_key=True, autoincrement=True
    )
    tea_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True),
        ForeignKey("teas.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    intro: Mapped[str | None] = mapped_column(String(200), nullable=True)
    steps: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    caution: Mapped[str | None] = mapped_column(Text, nullable=True)

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

    tea: Mapped[Tea] = relationship(back_populates="brewing_guide")
