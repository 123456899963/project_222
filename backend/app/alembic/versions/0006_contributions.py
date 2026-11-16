"""contributions：S10–S13 用户贡献 + 管理员审核

Revision ID: 0006_contributions
Revises: 0005_multi_lists
Create Date: 2026-11-09

依据：PLAN_剩余功能 批次四（2026-11-09 已确认）
- contributions：用户提交的新茶 / 科普投稿与审核状态
- tea_name_category_map：名品-茶类映射，做第一层茶类矛盾校验
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger

# revision identifiers, used by Alembic.
revision: str = "0006_contributions"
down_revision: str | None = "0005_multi_lists"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CATEGORY_ENUM = sa.Enum("green", "white", "yellow", "red", "oolong", "dark", name="tea_category")

MAPPING_SEED = [
    ("西湖龙井", "green"),
    ("碧螺春", "green"),
    ("黄山毛峰", "green"),
    ("六安瓜片", "green"),
    ("信阳毛尖", "green"),
    ("白毫银针", "white"),
    ("白牡丹", "white"),
    ("寿眉", "white"),
    ("君山银针", "yellow"),
    ("蒙顶黄芽", "yellow"),
    ("正山小种", "red"),
    ("金骏眉", "red"),
    ("祁门红茶", "red"),
    ("滇红", "red"),
    ("大红袍", "oolong"),
    ("铁观音", "oolong"),
    ("武夷岩茶", "oolong"),
    ("凤凰单丛", "oolong"),
    ("普洱熟茶", "dark"),
    ("普洱生茶", "dark"),
    ("安化黑茶", "dark"),
    ("六堡茶", "dark"),
]


def upgrade() -> None:
    mapping_table = op.create_table(
        "tea_name_category_map",
        sa.Column("id", MySQLInteger(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category", CATEGORY_ENUM, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uk_name_category_name"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        comment="名品-茶类映射（S10 第一层校验）",
    )
    op.bulk_insert(
        mapping_table,
        [{"name": name, "category": category} for name, category in MAPPING_SEED],
    )

    op.create_table(
        "contributions",
        sa.Column("id", MySQLInteger(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("user_id", MySQLInteger(unsigned=True), nullable=False),
        sa.Column(
            "type",
            sa.Enum("new_tea", "article", name="contribution_type"),
            nullable=False,
        ),
        sa.Column("target_tea_id", MySQLInteger(unsigned=True), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "approved", "rejected", name="contribution_status"),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("reject_reason", sa.String(length=200), nullable=True),
        sa.Column("reviewer_id", MySQLInteger(unsigned=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_tea_id"], ["teas.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        comment="用户贡献提交与审核状态（S10–S13）",
    )
    op.create_index("idx_contrib_user_status", "contributions", ["user_id", "status"])
    op.create_index("idx_contrib_status_created", "contributions", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_contrib_status_created", table_name="contributions")
    op.drop_index("idx_contrib_user_status", table_name="contributions")
    op.drop_table("contributions")
    op.drop_table("tea_name_category_map")
