"""content_platform：批次五 R1–R5 五大内容板块

Revision ID: 0007_content_platform
Revises: 0006_contributions
Create Date: 2026-11-10

依据：PLAN_剩余功能 批次五（2026-11-10 已确认）
- content_types：5 个板块分类（茶具/产地/文化/品牌/知识）
- content_items：统一内容条目表，meta JSON 承载各板块特有字段
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger

# revision identifiers, used by Alembic.
revision: str = "0007_content_platform"
down_revision: str | None = "0006_contributions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TYPE_SEED = [
    {
        "code": "teaware",
        "name": "茶具茶器",
        "icon": "🫖",
        "description": "盖碗、茶壶、品茗杯、公道杯等茶器文化与选择指南",
        "sort_order": 1,
    },
    {
        "code": "origin",
        "name": "茶叶产地",
        "icon": "🗺️",
        "description": "中国主要产茶区地理环境、风土特色与名茶产地溯源",
        "sort_order": 2,
    },
    {
        "code": "culture",
        "name": "茶叶文化",
        "icon": "📜",
        "description": "茶的历史演变、文人茶事、茶道精神与传统礼仪",
        "sort_order": 3,
    },
    {
        "code": "brand",
        "name": "茶叶品牌",
        "icon": "🏷️",
        "description": "中华老字号茶企与现代茶品牌故事",
        "sort_order": 4,
    },
    {
        "code": "knowledge",
        "name": "茶叶知识",
        "icon": "📚",
        "description": "茶叶标准、分类原理、冲泡技巧与品鉴知识",
        "sort_order": 5,
    },
]


def upgrade() -> None:
    type_table = op.create_table(
        "content_types",
        sa.Column("id", MySQLInteger(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("icon", sa.String(length=32), nullable=True),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uk_content_types_code"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        comment="内容板块分类（批次五 R1–R5）",
    )
    op.bulk_insert(type_table, TYPE_SEED)

    op.create_table(
        "content_items",
        sa.Column("id", MySQLInteger(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("type_id", MySQLInteger(unsigned=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("cover_image", sa.String(length=500), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.SmallInteger(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["type_id"], ["content_types.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        comment="统一内容条目（批次五 R1–R5；meta 为各板块特有 JSON 字段）",
    )
    op.create_index(
        "idx_content_items_type_active_sort",
        "content_items",
        ["type_id", "is_active", "sort_order"],
    )
    op.create_index(
        "idx_content_items_created",
        "content_items",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_content_items_created", table_name="content_items")
    op.drop_index("idx_content_items_type_active_sort", table_name="content_items")
    op.drop_table("content_items")
    op.drop_table("content_types")
