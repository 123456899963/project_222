"""batch1_filters：S2 价格数值列 + S7 小贴士时间戳 + S17 收藏时间索引

Revision ID: 0003_batch1_filters
Revises: 0002_content_expansion
Create Date: 2026-11-09

依据：PLAN_剩余功能 批次一（2026-11-09 已确认）
- S2 五档筛选：teas 增 price_min / price_max（元/斤），并从 price_range 文本回填
- S7 首页最新小贴士：tea_tips 增 created_at / updated_at，按 updated_at 倒序
- S17 热门 7 天权重：favorite_items 增 (created_at, tea_id) 索引支撑窗口聚合
"""

import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger

# revision identifiers, used by Alembic.
revision: str = "0003_batch1_filters"
down_revision: str | None = "0002_content_expansion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _parse_price_range(raw: str | None) -> tuple[int | None, int | None]:
    """从「500-3000元/斤」等文案解析价格区间；解析失败返回 (None, None)。"""
    if not raw:
        return None, None
    nums = re.findall(r"\d+", raw)
    if not nums:
        return None, None
    if len(nums) == 1:
        value = int(nums[0])
        return value, value
    low, high = int(nums[0]), int(nums[1])
    return (low, high) if low <= high else (high, low)


def upgrade() -> None:
    # --- S2：价格区间数值列 ---
    op.add_column(
        "teas",
        sa.Column(
            "price_min",
            MySQLInteger(unsigned=True),
            nullable=True,
            comment="价格下限（元/斤，S2 五档筛选）",
        ),
    )
    op.add_column(
        "teas",
        sa.Column(
            "price_max",
            MySQLInteger(unsigned=True),
            nullable=True,
            comment="价格上限（元/斤，S2 五档筛选）",
        ),
    )

    # --- S7：小贴士时间戳 ---
    op.add_column(
        "tea_tips",
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.add_column(
        "tea_tips",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # --- S17：收藏时间窗口聚合索引 ---
    op.create_index(
        "idx_favorite_created_tea",
        "favorite_items",
        ["created_at", "tea_id"],
    )

    # --- 回填历史价格区间（幂等：仅回填两侧均为空的记录） ---
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, price_range FROM teas")).fetchall()
    for tea_id, price_range in rows:
        low, high = _parse_price_range(price_range)
        if low is None:
            continue
        bind.execute(
            sa.text(
                "UPDATE teas SET price_min = :low, price_max = :high "
                "WHERE id = :tea_id AND price_min IS NULL AND price_max IS NULL"
            ),
            {"low": low, "high": high, "tea_id": tea_id},
        )


def downgrade() -> None:
    op.drop_index("idx_favorite_created_tea", table_name="favorite_items")
    op.drop_column("tea_tips", "updated_at")
    op.drop_column("tea_tips", "created_at")
    op.drop_column("teas", "price_max")
    op.drop_column("teas", "price_min")
