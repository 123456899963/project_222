"""content_expansion：teas 视频列 + tea_media 图片集表

Revision ID: 0002_content_expansion
Revises: 0001_baseline
Create Date: 2026-11-09

依据：ADR-0003（已采纳 2026-11-09）
- S5 详情页视频：teas 增 video_url / video_duration（与 main_image_url 同级，不建独立表）
- S4 详情页图片集：新建 tea_media 关联表（1:N，物理删除，随茶品级联）
约束：视频 ≤180 秒、≤50MB、MP4/MOV（应用层校验，MySQL 5.7 无有效 CHECK）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger

# revision identifiers, used by Alembic.
revision: str = "0002_content_expansion"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- S5：teas 增视频字段（选填，NULL 表示无视频，前端整块隐藏） ---
    op.add_column(
        "teas",
        sa.Column(
            "video_url",
            sa.String(500),
            nullable=True,
            comment="视频介绍 mp4 同源 URL（≤3 分钟，≤50MB，ADR-0003）",
        ),
    )
    op.add_column(
        "teas",
        sa.Column(
            "video_duration",
            MySQLInteger(unsigned=True),
            nullable=True,
            comment="视频时长（秒，≤180，应用层校验）",
        ),
    )

    # --- S4：tea_media 茶品图片集（1:N，物理删除） ---
    op.create_table(
        "tea_media",
        sa.Column("id", MySQLInteger(unsigned=True), autoincrement=True, primary_key=True),
        sa.Column("tea_id", MySQLInteger(unsigned=True), nullable=False),
        sa.Column(
            "image_url",
            sa.String(500),
            nullable=False,
            comment="图片 URL（同源 /uploads/...）",
        ),
        sa.Column(
            "sort_order",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="展示顺序，ASC",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["tea_id"], ["teas.id"], ondelete="CASCADE", name="fk_tea_media_tea"
        ),
        sa.Index("idx_tea_media_tea", "tea_id", "sort_order"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_comment="茶品图片集（PRD S4，ADR-0003；物理删除，上限 9 张由应用层校验）",
    )


def downgrade() -> None:
    op.drop_table("tea_media")
    op.drop_column("teas", "video_duration")
    op.drop_column("teas", "video_url")
