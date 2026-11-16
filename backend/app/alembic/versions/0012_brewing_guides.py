"""brewing_guides：新增 tea_brewing_guides 分步冲泡教程表（ADR-0005）

Revision ID: 0012_brewing_guides
Revises: 0011_user_session_version
Create Date: 2026-11-12

- 与 teas 1:1（tea_id 唯一），随茶品级联删除
- steps 为 JSON 数组：[{"title","detail","tip"}]，3–8 步由应用层校验
- 内容逐茶独立维护，管理员整篇 upsert；null 时前台退回三格速查卡
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger

# revision identifiers, used by Alembic.
revision: str = "0012_brewing_guides"
down_revision: str | None = "0011_user_session_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tea_brewing_guides",
        sa.Column("id", MySQLInteger(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("tea_id", MySQLInteger(unsigned=True), nullable=False),
        sa.Column("intro", sa.String(length=200), nullable=True),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("caution", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["tea_id"],
            ["teas.id"],
            name="fk_tea_brewing_guides_tea",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tea_id", name="uk_tea_brewing_guides_tea_id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        comment="茶品分步冲泡教程，与茶品 1:1（ADR-0005）",
    )


def downgrade() -> None:
    op.drop_table("tea_brewing_guides")
