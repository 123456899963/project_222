"""multi_lists：S9 多收藏清单

Revision ID: 0005_multi_lists
Revises: 0004_login_attempts
Create Date: 2026-11-09

依据：PLAN_剩余功能 批次三（2026-11-09 已确认）
- collection_lists：去 UNIQUE(user_id)，增 is_default + UNIQUE(user_id, is_default)
  （默认清单 is_default=1，非默认为 NULL，利用 MySQL 唯一索引允许多个 NULL）
- favorite_items：增 list_id 并按用户默认清单回填；唯一键改为 (list_id, tea_id)
- 为「有收藏但无清单」的历史用户补建默认清单，保证回填无空值
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger

# revision identifiers, used by Alembic.
revision: str = "0005_multi_lists"
down_revision: str | None = "0004_login_attempts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    # --- collection_lists：单清单 → 多清单 ---
    op.add_column(
        "collection_lists",
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=True,
            comment="默认清单标记：1=默认，NULL=普通清单（每用户仅一个默认）",
        ),
    )
    # 历史清单一律视为默认清单
    bind.execute(sa.text("UPDATE collection_lists SET is_default = 1"))

    # 先建 user_id 单列索引（承接外键依赖），再移除旧的 user_id 唯一约束
    op.create_index("idx_list_user", "collection_lists", ["user_id"])
    op.drop_constraint("uk_list_user", "collection_lists", type_="unique")
    op.create_unique_constraint(
        "uk_list_user_default", "collection_lists", ["user_id", "is_default"]
    )

    # --- favorite_items：补 list_id 并回填 ---
    op.add_column(
        "favorite_items",
        sa.Column(
            "list_id",
            MySQLInteger(unsigned=True),
            nullable=True,
            comment="所属清单 ID（S9 多清单）",
        ),
    )

    # 有收藏但从未创建清单的用户，先补默认清单
    bind.execute(
        sa.text(
            "INSERT INTO collection_lists (user_id, title, is_default) "
            "SELECT DISTINCT fi.user_id, '我的收藏', 1 FROM favorite_items fi "
            "LEFT JOIN collection_lists cl ON cl.user_id = fi.user_id "
            "WHERE cl.id IS NULL"
        )
    )
    # 历史收藏归属到各自用户的默认清单
    bind.execute(
        sa.text(
            "UPDATE favorite_items fi "
            "JOIN collection_lists cl ON cl.user_id = fi.user_id AND cl.is_default = 1 "
            "SET fi.list_id = cl.id"
        )
    )

    op.alter_column(
        "favorite_items",
        "list_id",
        existing_type=MySQLInteger(unsigned=True),
        nullable=False,
    )

    op.drop_constraint("uk_favorite_user_tea", "favorite_items", type_="unique")
    op.create_unique_constraint("uk_favorite_list_tea", "favorite_items", ["list_id", "tea_id"])
    op.create_index("idx_favorite_list_created", "favorite_items", ["list_id", "created_at"])
    op.create_foreign_key(
        "fk_favorite_list",
        "favorite_items",
        "collection_lists",
        ["list_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    bind = op.get_bind()

    # 降级回单清单：丢弃非默认清单中的条目与清单本身
    bind.execute(
        sa.text(
            "DELETE fi FROM favorite_items fi "
            "JOIN collection_lists cl ON cl.id = fi.list_id "
            "WHERE cl.is_default IS NULL"
        )
    )
    bind.execute(sa.text("DELETE FROM collection_lists WHERE is_default IS NULL"))

    op.drop_constraint("fk_favorite_list", "favorite_items", type_="foreignkey")
    op.drop_index("idx_favorite_list_created", table_name="favorite_items")
    op.drop_constraint("uk_favorite_list_tea", "favorite_items", type_="unique")
    op.create_unique_constraint("uk_favorite_user_tea", "favorite_items", ["user_id", "tea_id"])
    op.drop_column("favorite_items", "list_id")

    op.drop_constraint("uk_list_user_default", "collection_lists", type_="unique")
    # 先补回 user_id 单列唯一索引，再移除临时单列索引
    op.create_unique_constraint("uk_list_user", "collection_lists", ["user_id"])
    op.drop_index("idx_list_user", table_name="collection_lists")
    op.drop_column("collection_lists", "is_default")
